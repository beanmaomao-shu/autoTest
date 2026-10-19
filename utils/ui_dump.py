# -*- coding: utf-8 -*-
"""
UI 控件树快照工具（ui_dump.py）
------------------------------------------------
作用：开发/调试阶段抓定位器的辅助工具，App 改版或探索新页面时
不再需要编写临时探测脚本。提供三个子命令：
    1. snap ：创建临时 Appium 会话，对当前界面拍控件树快照（page_source）
              保存到 log/ui_dump/，并打印可定位控件表（class/id/text/hint）；
    2. show ：离线解析已保存的快照 XML，打印控件表（可反复查看）；
    3. diff ：对比两份快照的 resource-id 集合差异，快速判断
              「操作后界面是否跳转、新增/消失了哪些控件」；
    4. walk ：复用一个会话连续走查多屏（每按回车快照 + 自动 diff 上一屏），
              避免探索多个界面时重复支付建会话 + 登录前置（降本）。

用法（在项目根目录下执行）：
    python utils/ui_dump.py snap                       # 快照存为 page_<时间戳>.xml
    python utils/ui_dump.py snap -n login_page         # 指定文件名 login_page.xml
    python utils/ui_dump.py snap -k puc                # 只打印 id/text/hint 含 puc 的控件
    python utils/ui_dump.py show log/ui_dump/login_page.xml
    python utils/ui_dump.py diff log/ui_dump/a.xml log/ui_dump/b.xml
    python utils/ui_dump.py walk -p bind               # 一次登录，逐屏导航快照 bind_01.xml ...

实现说明：
    - 快照走 Appium page_source（GET /session/<id>/source），与
      find_element 的 XPath 匹配同源，表里能看到的属性运行时一定能定位到；
    - 部分设备/模拟器上 adb uiautomator dump 会被系统杀掉，故不依赖它；
      若必须用 adb，可用 exec-out 重定向：adb exec-out uiautomator dump /dev/tty > 本地.xml
    - 解析时遍历所有标签而不是 iter('node')：部分 App（如 com.hd.smartVillage）
      的 page_source 节点标签名是 class 全名（<android.widget.EditText>），没有 <node> 标签；
    - snap 会按 config capabilities 启动 App（noReset，不清数据），
      拍的是会话建立那一刻的前台界面。
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# 以 python utils/ui_dump.py 方式直接运行时，把项目根目录加入模块搜索路径，
# 保证 config / utils 等项目内模块可以被正常导入（-m 方式运行则天然可用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.setting import DUMP_DIR, ensure_dirs


# ------------------------------------------------------------------
# 一、解析与展示
# ------------------------------------------------------------------
def _short_class(tag):
    """class 全名 -> 短类名：android.widget.EditText -> EditText"""
    return tag.rsplit(".", 1)[-1] if tag else tag


def _short_id(rid):
    """resource-id 全称 -> id 后缀：com.hd.smartVillage:id/puc_btn_login -> puc_btn_login"""
    return rid.rsplit("/", 1)[-1] if rid else rid


def _clean(value, width):
    """把属性值压成单行并截断，避免长文本/换行把表格打散"""
    value = re.sub(r"\s+", " ", value or "").strip()
    return value[:width] + ("..." if len(value) > width else "")


def parse_nodes(xml_text, keyword=None):
    """
    解析快照 XML，返回值得抓定位器的控件信息列表。
    注意：遍历所有标签而非 iter('node')，兼容节点标签名为 class 全名的 App。
    过滤条件：至少带 resource-id / text / hint 之一的控件；
    指定 keyword 时，要求三者之一包含该关键字（用于快速定位目标控件）。
    """
    root = ET.fromstring(xml_text)
    rows = []
    for el in root.iter():
        rid = el.get("resource-id") or ""
        text = el.get("text") or ""
        hint = el.get("hint") or ""
        if not (rid or text or hint):
            continue  # 纯布局容器，对抓定位器没有意义
        if keyword and keyword not in f"{rid}{text}{hint}":
            continue
        rows.append({
            "class": _short_class(el.tag),
            "id": _short_id(rid),
            "text": text,
            "hint": hint,
            # checked 只在 true 时展示（false 占绝大多数，全打出来是噪音）
            "checked": "true" if el.get("checked") == "true" else "",
        })
    return rows


def print_table(rows):
    """按表格打印控件表：class / resource-id / text / hint / checked"""
    print(f"{'class':<20} | {'resource-id':<32} | {'text':<24} | {'hint':<20} | checked")
    print("-" * 110)
    for r in rows:
        print(f"{r['class']:<20} | {r['id']:<32} | {_clean(r['text'], 24):<24} | "
              f"{_clean(r['hint'], 20):<20} | {r['checked']}")
    print(f"共 {len(rows)} 个可定位控件")


def collect_ids(xml_text):
    """提取快照中所有非空 resource-id（保留包名前缀全称，用于 diff 精确对比）"""
    return {rid for rid in re.findall(r'resource-id="([^"]*)"', xml_text) if rid}


# ------------------------------------------------------------------
# 二、三个子命令
# ------------------------------------------------------------------
def cmd_snap(args):
    """
    snap：创建临时 Appium 会话 -> 拍 page_source 快照 -> 保存并打印控件表。
    快照对象是会话建立那一刻的前台界面（App 会按 capabilities 被拉起）。
    """
    # 懒加载 appium 相关依赖：show / diff 属于纯离线操作，不应要求安装/连接
    from utils.appium_driver import create_driver, quit_driver

    ensure_dirs()
    name = args.name or f"page_{datetime.now():%Y%m%d_%H%M%S}"
    file_path = os.path.join(DUMP_DIR, f"{name}.xml")

    driver = create_driver()
    try:
        xml_text = driver.page_source
    finally:
        quit_driver(driver)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(xml_text)
    print(f"快照已保存：{file_path}")
    print_table(parse_nodes(xml_text, args.keyword))
    return 0


def cmd_show(args):
    """show：离线解析指定快照文件并打印控件表"""
    with open(args.file, encoding="utf-8") as f:
        xml_text = f.read()
    print(f"快照文件：{args.file}")
    print_table(parse_nodes(xml_text, args.keyword))
    return 0


def cmd_diff(args):
    """
    diff：对比两份快照的 resource-id 集合。
    典型用法：操作前 snap 一份、操作后再 snap 一份，diff 两者：
    集合完全相同 => 界面没跳转（点击可能被吞/被弹窗拦截）；
    有差异 => 差异列表就是新界面「新增/消失」的控件，直接拿来抓定位器。
    """
    with open(args.file_a, encoding="utf-8") as f:
        ids_a = collect_ids(f.read())
    with open(args.file_b, encoding="utf-8") as f:
        ids_b = collect_ids(f.read())

    only_a = sorted(ids_a - ids_b)
    only_b = sorted(ids_b - ids_a)
    print(f"A = {args.file_a}（{len(ids_a)} 个控件 id）")
    print(f"B = {args.file_b}（{len(ids_b)} 个控件 id）")
    print(f"共同控件：{len(ids_a & ids_b)} 个")

    if not only_a and not only_b:
        print("结论：两屏 resource-id 集合完全相同 —— 界面未跳转，"
              "或跳转前后两屏控件都没有 resource-id（需结合 text/hint 再判断）")
        return 0
    if only_a:
        print("\n仅 A 有（B 中已消失的控件）：")
        for rid in only_a:
            print(f"  - {rid}")
    if only_b:
        print("\n仅 B 有（B 中新增的控件）：")
        for rid in only_b:
            print(f"  + {rid}")
    return 0


def cmd_walk(args):
    """
    walk：复用一个会话连续走查多个界面并逐屏快照（针对探索降本）。
    踩坑回顾：snap 每次都新建会话 + 重跑登录前置（建会话~10s + clearApp
    + 弹窗链 + 登录），探索多个界面时前置被重复支付（坑 4）；且每轮只验
    一层、轮次切分太细（坑 5）。walk 只建一次会话，人工在手机上逐层导航，
    每按一次回车就快照当前屏 + 自动与上一屏 diff，一次登录即可连续探索多个假设。
    工作流：建 driver 一次 -> （人在手机上导航）-> 回车快照当前屏
    -> 依次存 prefix_01.xml / prefix_02.xml ... 并打印控件表 + 与上一屏差异；
    输入 q 回车退出并关闭会话。
    """
    from utils.appium_driver import create_driver, quit_driver

    ensure_dirs()
    prefix = args.prefix or f"walk_{datetime.now():%Y%m%d_%H%M%S}"
    driver = create_driver()
    print("会话已建立。请在手机上导航到目标界面，回到此处按回车快照；输入 q 回车退出。")
    prev_xml = None
    index = 0
    try:
        while True:
            try:
                cmd = input(f"[{prefix}] 回车=快照 / q=退出 > ").strip().lower()
            except EOFError:
                break
            if cmd in ("q", "quit", "exit"):
                break
            index += 1
            file_path = os.path.join(DUMP_DIR, f"{prefix}_{index:02d}.xml")
            xml_text = driver.page_source
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml_text)
            print(f"快照已保存：{file_path}")
            print_table(parse_nodes(xml_text, args.keyword))
            # 自动与上一屏 diff resource-id 集合，帮助判断“这一步操作是否真的跳页”
            if prev_xml is not None:
                ids_prev, ids_cur = collect_ids(prev_xml), collect_ids(xml_text)
                if ids_prev == ids_cur:
                    print(">> 与上一屏 resource-id 集合相同：界面未跳转（点击可能被吞/被弹窗拦截）")
                else:
                    added = sorted(ids_cur - ids_prev)
                    removed = sorted(ids_prev - ids_cur)
                    if added:
                        print(">> 较上一屏新增控件：" + ", ".join(_short_id(r) for r in added))
                    if removed:
                        print(">> 较上一屏消失控件：" + ", ".join(_short_id(r) for r in removed))
            prev_xml = xml_text
    finally:
        quit_driver(driver)
    print(f"走查结束，共 {index} 份快照（前缀：{prefix}）。")
    return 0


# ------------------------------------------------------------------
# 三、命令行入口
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="ui_dump",
        description="Appium UI 控件树快照工具：snap 拍快照 / show 看控件表 / diff 对比两屏",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snap", help="创建临时会话，对当前界面拍快照并打印控件表")
    p_snap.add_argument("-n", "--name", help="快照文件名（不带扩展名），默认 page_<时间戳>")
    p_snap.add_argument("-k", "--keyword", help="只打印 resource-id/text/hint 含该关键字的控件")
    p_snap.set_defaults(func=cmd_snap)

    p_show = sub.add_parser("show", help="解析已保存的快照文件并打印控件表")
    p_show.add_argument("file", help="快照 XML 文件路径")
    p_show.add_argument("-k", "--keyword", help="只打印 resource-id/text/hint 含该关键字的控件")
    p_show.set_defaults(func=cmd_show)

    p_diff = sub.add_parser("diff", help="对比两份快照的 resource-id 集合差异")
    p_diff.add_argument("file_a", help="快照 A（前一屏 / 操作前）")
    p_diff.add_argument("file_b", help="快照 B（后一屏 / 操作后）")
    p_diff.set_defaults(func=cmd_diff)

    p_walk = sub.add_parser(
        "walk", help="复用一个会话连续走查多屏快照（自动 diff 上一屏），避免重复登录前置")
    p_walk.add_argument("-p", "--prefix", help="快照文件名前缀，依次存为 prefix_01.xml ...")
    p_walk.add_argument("-k", "--keyword", help="只打印 resource-id/text/hint 含该关键字的控件")
    p_walk.set_defaults(func=cmd_walk)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

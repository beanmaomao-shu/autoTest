# -*- coding: utf-8 -*-
"""
框架统一运行入口（run.py）
------------------------------------------------
作用：一条命令完成「执行测试用例 + 生成 allure 可视化报告」的全流程，
方便本地运行，也方便 Jenkins 等 CI 工具直接调用。

使用方式（在项目根目录执行）：
    python run.py                 # 运行全部用例并生成报告
    python run.py -m smoke        # 只运行冒烟用例（参数会透传给 pytest）

前置条件：
    1. 已启动 Appium Server（appium 命令）；
    2. 已连接设备/模拟器（adb devices 能看到设备）；
    3. 已安装 allure 命令行工具（生成 html 报告需要，未安装则只产出原始结果）。
"""
import os
import shutil
import subprocess
import sys

import pytest

# 将项目根目录加入导入路径，保证以脚本方式运行时能 import 各层包
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config.setting import ALLURE_RESULT_DIR, ALLURE_REPORT_DIR, ensure_dirs  # noqa: E402


def run_tests(extra_args=None):
    """
    执行 pytest 测试用例。

    :param extra_args: 透传给 pytest 的额外命令行参数（列表），如 ["-m", "smoke"]
    :return: pytest 退出码（0 表示全部通过）
    """
    # pytest 基础参数：指定结果输出目录并清空旧结果
    args = [
        "scripts",
        f"--alluredir={ALLURE_RESULT_DIR}",
        "--clean-alluredir",
    ]
    # 合并用户传入的额外参数
    if extra_args:
        args.extend(extra_args)

    print(f">>> 开始执行测试用例，参数：{args}")
    # 调用 pytest 主入口执行用例
    exit_code = pytest.main(args)
    return exit_code


def preserve_allure_history():
    """
    打通 allure 历史趋势：把上一次报告的 history 目录接续到本次结果目录。

    原理：
        allure 的历史趋势数据（通过率、耗时曲线等）保存在报告目录的
        allure-report/history 中；而下一步的 `allure generate --clean`
        会清空整个 allure-report。所以在生成前，先把旧的 history 复制到
        allure-result/history，allure 生成时会读取它并与本次结果合并，
        从而在新的 allure-report/history 中累积出趋势数据。

    注意：必须在 run_tests 之后调用（此时 allure-result 已被清空并写入本次结果），
         且在 generate_allure_report 之前调用（否则 history 会随 --clean 被删掉）。
    """
    # 上一次报告中的历史目录
    history_src = os.path.join(ALLURE_REPORT_DIR, "history")
    # 本次结果目录中用于承接历史的位置
    history_dst = os.path.join(ALLURE_RESULT_DIR, "history")

    if not os.path.exists(history_src):
        # 首次执行没有历史，属正常情况，直接跳过
        print(">>> 未检测到历史报告（首次执行），跳过历史趋势接续")
        return

    # 若结果目录已有残留 history，先删除，保证复制干净
    if os.path.exists(history_dst):
        shutil.rmtree(history_dst)

    # 将上一次报告的历史复制到本次结果目录，供 allure generate 合并
    shutil.copytree(history_src, history_dst)
    print(f">>> 已接续历史趋势数据：{history_src} -> {history_dst}")


def generate_allure_report():
    """
    调用 allure 命令行工具，把原始结果（json）生成 html 可视化报告。
    若本机未安装 allure 命令行工具，则给出提示并跳过（不影响用例执行结果）。
    """
    print(f">>> 开始生成 allure 报告：{ALLURE_REPORT_DIR}")
    # allure generate：-o 指定输出目录，--clean 表示清空旧报告
    command = [
        "allure",
        "generate",
        ALLURE_RESULT_DIR,
        "-o",
        ALLURE_REPORT_DIR,
        "--clean",
    ]
    try:
        # Windows 下 allure 是 .bat 脚本，需要 shell=True 才能被识别
        subprocess.run(command, shell=True, check=True)
        print(f">>> allure 报告生成成功，路径：{ALLURE_REPORT_DIR}")
        print(f">>> 查看报告命令：allure open {ALLURE_REPORT_DIR}")
    except subprocess.CalledProcessError:
        print(">>> allure 报告生成失败，请检查 allure 命令行工具是否已正确安装并配置环境变量")
    except Exception as e:
        print(f">>> 生成 allure 报告时出现异常：{e}")


def main():
    """入口函数：准备目录 -> 执行用例 -> 生成报告"""
    # 1. 确保日志、报告等目录存在
    ensure_dirs()
    # 2. 执行测试用例（sys.argv[1:] 把命令行额外参数透传给 pytest）
    run_tests(sys.argv[1:])
    # 3. 接续上一次的历史趋势数据（必须在生成报告、清空旧报告之前）
    preserve_allure_history()
    # 4. 生成 allure 可视化报告
    generate_allure_report()


if __name__ == "__main__":
    main()

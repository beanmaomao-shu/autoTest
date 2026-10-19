# -*- coding: utf-8 -*-
"""
全局弹窗注册表与统一处理（dialogs.py）
------------------------------------------------
作用：把被测 App 所有已知「弹窗 / 系统提示」的关闭按钮集中登记为单一事实来源，
供各页面对象、conftest fixture 以及探索脚本统一调用，一处维护、全局生效。

踩坑总结（为什么要集中 + 为什么要临时关隐式等待）：
    1. 【弹窗分散】弹窗定位原先分散在 LoginPage.dismiss_startup_dialogs 与
       BindHousePage.handle_location_dialog 两处，新场景出现的新弹窗（如进绑定页
       触发的定位权限「系统提示」）容易漏登记、重复维护。集中到本模块后，
       发现新弹窗只需在 KNOWN_DIALOGS 加一行，所有调用方自动生效。
    2. 【隐式等待拖慢扫描】全局 IMPLICIT_WAIT=10，若扫描时沿用隐式等待，每个
       「不在屏」的定位器都会阻塞满 10 秒，一轮 5 个弹窗最坏要 50 秒，首启弹窗链
       曾因此耗约 100 秒。本模块在扫描期间把隐式等待临时降为 0，做到「在就点、
       不在就秒过」，处理完再还原，把首启链降到真实加载耗时（数十秒→数秒）。

用法：
    from base.dialogs import dismiss_known_dialogs, DIALOG_SYSTEM_PROMPT
    # 首启弹窗链：轮询直到首页就绪或超时（给足冗余）
    dismiss_known_dialogs(driver, timeout=90, ready_locator=HomePage.COURT_ENTRY)
    # 业务弹窗：短超时轮询，只关心某个弹窗（如进绑定页可能弹的定位权限提示）
    dismiss_known_dialogs(driver, timeout=3, only=(DIALOG_SYSTEM_PROMPT,))
"""
import time

from appium.webdriver.common.appiumby import AppiumBy

from config.setting import IMPLICIT_WAIT
from utils.logger import logger

# 被测 App 的 resource-id 前缀，用于拼接弹窗按钮定位
_PKG = "com.hd.smartVillage:id"

# ----------------------------------------------------------------------
# 已知弹窗注册表（单一事实来源）
# 每项为 (弹窗名, 关闭按钮定位器)；扫描时逐项探测，在屏即点掉，顺序无关。
# 新增弹窗只需在此登记一处，所有调用方自动生效。
# ----------------------------------------------------------------------
KNOWN_DIALOGS = (
    # ---- 首启弹窗链（清空数据重启后依次出现，顺序不固定）----
    ("通知权限-不允许", (AppiumBy.XPATH, '//*[@text="不允许"]')),
    ("隐私协议-同意", (AppiumBy.XPATH, '//*[@text="同意"]')),
    ("温馨提示-我知道了", (AppiumBy.XPATH, '//*[@text="我知道了"]')),
    ("推送引导-关闭", (AppiumBy.XPATH,
                     f'//android.view.View[@resource-id="{_PKG}/notificationSettingCloseBtn"]')),
    # ---- 系统权限提示：存储权限、定位权限「系统提示」共用同一「取消」按钮 id ----
    ("系统提示-取消", (AppiumBy.XPATH,
                     f'//android.widget.TextView[@resource-id="{_PKG}/bt_cancel"]')),
)

# 常用弹窗名常量：供调用方通过 only 参数精确指定，避免散落易错的字符串字面量。
# 进绑定页点击 court_name 后，未授予定位权限时会弹此「系统提示」，点「取消」跳过。
DIALOG_SYSTEM_PROMPT = "系统提示-取消"


def dismiss_known_dialogs(driver, timeout=60, ready_locator=None, only=None, poll=0.5):
    """
    在 timeout 秒内轮询扫描注册表，关闭当前屏幕上的已知弹窗。

    扫描期间把隐式等待临时降为 0（快查快返，避免每个不在屏的定位器阻塞
    IMPLICIT_WAIT 秒），无论正常结束还是异常，finally 都还原为全局 IMPLICIT_WAIT。

    :param driver: Appium driver
    :param timeout: 最长处理时间（秒）。首启弹窗链给足冗余（如 90）；
                    单个业务弹窗给短值（如 3）即可
    :param ready_locator: 可选，「页面已就绪」的目标定位器（如首页 court_name）。
                          一旦在屏即提前结束，用于首启弹窗处理完后尽快进入下一步；
                          为 None 时轮询满 timeout（适合“可能弹也可能不弹”的业务弹窗）
    :param only: 可选，弹窗名元组，仅扫描这些弹窗（精确处理、避免误点）；
                 为 None 时扫描注册表全部弹窗
    :param poll: 每轮扫描后的轮询间隔（秒）
    :return: 本次实际关闭的弹窗名列表（按点击顺序）
    """
    targets = KNOWN_DIALOGS if only is None else tuple(d for d in KNOWN_DIALOGS if d[0] in only)
    dismissed = []
    deadline = time.monotonic() + timeout
    # 临时关闭隐式等待：弹窗扫描要的是“在就点、不在就秒过”，
    # 隐式等待会让每个 miss 的定位器白等 IMPLICIT_WAIT 秒，严重拖慢首启处理
    driver.implicitly_wait(0)
    try:
        while time.monotonic() < deadline:
            # 目标页已就绪则无需再扫弹窗
            if ready_locator is not None and driver.find_elements(*ready_locator):
                break
            for name, locator in targets:
                elems = driver.find_elements(*locator)
                if elems:
                    elems[0].click()
                    dismissed.append(name)
                    logger.info(f"关闭弹窗：{name}")
                    time.sleep(1)  # 等当前弹窗动画消失、下一个弹窗出现
            time.sleep(poll)
        return dismissed
    finally:
        # 还原隐式等待，避免影响后续元素定位 / 显式等待行为
        driver.implicitly_wait(IMPLICIT_WAIT)

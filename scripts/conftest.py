# -*- coding: utf-8 -*-
"""
pytest 全局配置文件（conftest.py）
------------------------------------------------
作用：pytest 的共享配置与 fixture 文件，放在此处的 fixture / 钩子函数
对同目录及子目录下的所有测试脚本自动生效，无需 import。
本文件主要负责：
    1. 提供全局 driver fixture（会话级别，全程复用一个 driver）；
    2. 框架启动前准备必要目录；
    3. 用例失败时自动截图，并把截图、日志附加到 allure 报告。
"""
import os
import time

import allure
import pytest

from config.setting import DATA_DIR, ensure_dirs, SCREENSHOT_DIR
from pages.login_page import LoginPage
from utils.appium_driver import create_driver, quit_driver, get_capabilities
from utils.logger import logger
from utils.yaml_util import read_yaml


def pytest_sessionstart(session):
    """
    pytest 会话开始时的钩子函数（整个测试进程只执行一次）。
    作用：确保日志、报告、截图等目录存在，避免运行时因目录缺失报错。
    """
    ensure_dirs()
    logger.info("========== pytest 测试会话开始 ==========")


def pytest_sessionfinish(session, exitstatus):
    """pytest 会话结束时的钩子函数，用于打印收尾日志"""
    logger.info(f"========== pytest 测试会话结束，退出码：{exitstatus} ==========")


@pytest.fixture(scope="session", autouse=True)
def driver():
    """
    全局 driver fixture（会话级别）。
    - scope="session"：整个测试会话只创建一个 driver，所有用例复用，节省启动 App 的时间；
    - autouse=True：所有用例自动注入该 fixture，无需在每个用例显式声明；
    - yield 之前是「准备（setup）」，之后是「清理（teardown）」。
    :yield: 返回初始化好的 Appium driver
    """
    logger.info("【setup】初始化 Appium driver")
    _driver = create_driver()
    # 最大化/唤醒屏幕，保证用例执行时屏幕处于可用状态
    yield _driver
    logger.info("【teardown】关闭 Appium driver")
    quit_driver(_driver)


def reset_app(driver, clear_data):
    """
    重启被测 App 的公共实现。
    :param driver: 会话级 Appium driver
    :param clear_data: True=清空 App 数据（退出登录回首启态）；False=仅重启保留登录态
    """
    app_package = get_capabilities().get("appPackage")
    if not app_package:
        return
    driver.terminate_app(app_package)
    if clear_data:
        # 清空 App 数据（等价于退出登录/恢复初始状态）
        driver.execute_script("mobile: clearApp", {"appId": app_package})
    driver.activate_app(app_package)
    # 清数据后首启必有一串顺序不固定的弹窗链；未清数据时偶发弹窗也一并扫描，
    # 无弹窗时该方法约 1 秒即返回，代价可忽略
    LoginPage(driver).dismiss_startup_dialogs()
    logger.info(f"已重启被测 App：{app_package}（清空数据：{clear_data}）")


@pytest.fixture
def clean_app(driver):
    """
    强隔离（函数级，需在用例参数中显式声明）：清数据 + 重启，
    回到未登录首启状态。适用于测试登录流程本身、或用例会改变账号状态的模块。
    代价：每条用例需重过首启弹窗链（弹窗链提速后约 15 秒），不要给无副作用的用例滥用。
    """
    reset_app(driver, clear_data=True)
    yield driver


@pytest.fixture
def relaunch_app(driver):
    """
    弱隔离（函数级，需在用例参数中显式声明）：仅重启不清数据，
    保留登录态回到首页（约 6 秒）。适用于共享登录态、无副作用的用例，
    通常与模块级 logged_in_app 搭配使用。
    """
    reset_app(driver, clear_data=False)
    yield driver


@pytest.fixture(scope="module")
def logged_in_app(driver):
    """
    模块级共享登录态：模块第一条用例前清数据 + 过弹窗链 + 用
    login_data.yaml 的 valid_account 登录一次，同模块后续用例直接复用登录态
    （搭配 relaunch_app 每条用例前仅重启回首页）。
    适用条件：模块内用例均无副作用（不改变账号状态，如表单校验被拦截类）；
    有真实写入副作用的用例（如真实绑定/支付）请改用 clean_app 强隔离。
    """
    reset_app(driver, clear_data=True)
    valid_account = read_yaml(os.path.join(DATA_DIR, "login_data.yaml"))["valid_account"]
    login_page = LoginPage(driver)
    login_page.enter_login_page()
    login_page.choose_password_login()
    login_page.login(valid_account["account"], valid_account["password"])
    assert login_page.wait_login_success(), "共享登录态前置失败：登录未成功"
    logger.info("模块级共享登录态已就绪")
    yield driver


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    pytest 生成测试报告的钩子（hookwrapper 包裹，可拿到最终报告对象）。
    作用：监听每条用例的执行结果，一旦用例「执行阶段失败」，
    自动截图并把截图附加到 allure 报告中，方便定位失败现场。
    """
    outcome = yield
    # 获取本次测试的报告对象
    report = outcome.get_result()

    # 只在「用例主体执行阶段（call）」且「失败」时截图
    if report.when == "call" and report.failed:
        # 从测试项中取出 driver fixture 实例
        _driver = item.funcargs.get("driver")
        if _driver is not None:
            try:
                # 以「用例名 + 时间戳」命名截图，避免相互覆盖
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                png_name = f"{item.name}_{timestamp}.png"
                png_path = os.path.join(SCREENSHOT_DIR, png_name)
                # 获取截图的二进制内容
                screenshot_bytes = _driver.get_screenshot_as_png()
                # 保存到本地截图目录
                with open(png_path, "wb") as f:
                    f.write(screenshot_bytes)
                # 附加到 allure 报告，类型为 PNG 图片
                allure.attach(
                    screenshot_bytes,
                    name=f"失败截图_{item.name}",
                    attachment_type=allure.attachment_type.PNG,
                )
                logger.error(f"用例失败并已截图：{png_path}")
            except Exception as e:
                logger.warning(f"失败截图过程出现异常：{e}")

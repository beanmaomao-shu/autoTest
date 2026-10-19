# -*- coding: utf-8 -*-
"""
登录功能测试脚本（test_login.py）
------------------------------------------------
作用：scripts 层的测试用例，遵循「准备数据 -> 调用页面方法 -> 断言结果」的结构。
被测 App 为 com.hd.smartVillage，登录流程：
    首页小区入口（court_name）-> 登录页 -> 切换密码登录 ->
    输入账号/密码 -> 勾选用户协议 -> 点击登录。
演示了：
    1. 使用 allure 装饰器标注用例的模块、故事、标题、严重级别，生成美观报告；
    2. 使用 pytest.mark.parametrize + yaml 数据文件实现数据驱动测试；
    3. 调用 pages 层页面对象完成业务操作，脚本层不直接操作元素（PO 原则）。
隔离策略：本模块测的是登录流程本身，每条用例都必须是未登录初始态，
    故显式声明 clean_app 强隔离 fixture（清数据+重启，见 scripts/conftest.py）。
"""
import os

import allure
import pytest

from config.setting import DATA_DIR
from pages.login_page import LoginPage
from utils.logger import logger
from utils.yaml_util import read_yaml


def load_login_data():
    """
    从 data/login_data.yaml 读取登录测试数据。
    :return: (有效账号字典, 参数化数据列表)
    """
    data_path = os.path.join(DATA_DIR, "login_data.yaml")
    data = read_yaml(data_path)
    return data["valid_account"], data["login_data"]


# 读取一次登录测试数据，供下方参数化使用（避免多次读文件）
VALID_ACCOUNT, LOGIN_DATA = load_login_data()


@allure.epic("移动端 App 自动化测试")
@allure.feature("登录模块")
class TestLogin:
    """登录功能测试用例集"""

    @allure.story("登录成功场景")
    @allure.title("正确账号密码登录，进入首页")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_success(self, driver, clean_app):
        """
        正向用例：输入正确账号密码并登录，验证离开登录页进入首页。
        :param driver: 由 conftest 提供的会话级 Appium driver
        :param clean_app: 强隔离 fixture，用例前清数据重启回未登录态
        """
        logger.info("开始执行用例：正确账号密码登录进入首页")

        # 1. 创建登录页面对象
        login_page = LoginPage(driver)

        # 2. 调用页面业务方法：进入登录页 -> 切换密码登录 -> 输入账号密码并登录
        login_page.enter_login_page()
        login_page.choose_password_login()
        login_page.login(VALID_ACCOUNT["account"], VALID_ACCOUNT["password"])

        # 3. 断言：登录成功后离开登录页（含未跳转时的补点重试，避免冷启动吞点击导致误报）
        with allure.step("校验是否离开登录页（等待登录按钮消失）"):
            assert login_page.wait_login_success(), "点击登录后未离开登录页进入首页"

        logger.info("用例执行通过：登录成功进入首页")

    @allure.story("登录数据驱动场景")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        # 参数化：用 pytest.param 将每条数据包装为单个参数（避免 dict 被自动拆解），
        # 并用 case_name 作为用例 id 显示在报告中
        argnames=["case"],
        argvalues=[pytest.param(item, id=item["case_name"]) for item in LOGIN_DATA],
    )
    def test_login_with_data(self, driver, clean_app, case):
        """
        数据驱动用例：遍历 yaml 中的多组账号密码数据，登录后验证去向。
        :param driver: Appium driver
        :param clean_app: 强隔离 fixture，用例前清数据重启回未登录态
        :param case: 单条测试数据字典（account/password/expected/case_name）
        """
        # 动态设置 allure 报告中显示的用例标题
        allure.dynamic.title(case["case_name"])

        logger.info(f"开始执行数据驱动用例：{case['case_name']}")

        login_page = LoginPage(driver)

        with allure.step(f"输入账号[{case['account']}]和密码，点击登录"):
            login_page.enter_login_page()
            login_page.choose_password_login()
            login_page.login(case["account"], case["password"])

        with allure.step("校验是否按预期离开/停留登录页"):
            if case["expected"] == "离开登录页":
                # 登录成功：等待登录按钮消失，确认已进入首页
                assert login_page.wait_login_success(), "预期离开登录页进入首页，实际仍停留"
            else:
                # 登录被拦截：登录按钮应仍在当前屏幕
                assert login_page.is_login_page_displayed(), "预期停留登录页，实际已离开"

        logger.info(f"用例执行通过：{case['case_name']}")

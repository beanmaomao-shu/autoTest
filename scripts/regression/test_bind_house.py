# -*- coding: utf-8 -*-
"""
绑定房屋功能测试脚本（test_bind_house.py）
------------------------------------------------
作用：覆盖登录后「首页绑定房屋」业务，结构与 test_login.py 一致：
    准备数据 -> 调用页面方法 -> 断言结果。
业务流程（真机实测）：
    登录后首页 court_name 显示「请绑定房屋」-> 点击进入绑定房屋表单页
    -> 表单级联校验：城市 -> 小区 -> 房号，身份信息（姓名/手机号/类型/身份）。
用例设计：
    1. 正向：从首页进入绑定页，校验表单默认值（手机号预填/类型/身份/未选状态）；
    2. 数据驱动：按 data/bind_house_data.yaml 校验表单拦截规则
       （未选城市点小区 Toast 提示、未选小区点房号拦截、不完整提交拦截）。
说明：本模块用例全部是表单校验被拦截类（不改变账号状态），符合共享登录态
    条件：模块级 logged_in_app 只登录一次，每条用例前 relaunch_app 仅重启
    回登录态首页（不清数据，约 15 秒/条，相比 clean_app 强隔离提速约 5 倍）。
    若未来新增真实绑定成功等有副作用的用例，该用例应单独放模块并改用 clean_app。
"""
import os

import allure
import pytest

from config.setting import DATA_DIR
from pages.bind_house_page import BindHousePage
from utils.logger import logger
from utils.yaml_util import read_yaml


def load_bind_house_data():
    """
    读取登录账号（复用 login_data.yaml 的 valid_account）与绑定房屋测试数据。
    :return: (有效账号字典, 绑定房屋参数化数据列表)
    """
    valid_account = read_yaml(os.path.join(DATA_DIR, "login_data.yaml"))["valid_account"]
    bind_data = read_yaml(os.path.join(DATA_DIR, "bind_house_data.yaml"))["bind_house_data"]
    return valid_account, bind_data


# 读取一次测试数据，供下方参数化使用（避免多次读文件）
VALID_ACCOUNT, BIND_HOUSE_DATA = load_bind_house_data()


@pytest.fixture(autouse=True)
def bind_case_env(logged_in_app, relaunch_app):
    """
    本模块用例公共前置：复用模块级共享登录态（logged_in_app 首条用例前
    清数据+登录一次），每条用例前仅重启回登录态首页（relaunch_app，不清数据）。
    fixture 作用域保证顺序：模块级 logged_in_app 先于函数级 relaunch_app 执行。
    """


def enter_bind_page(driver):
    """
    公共前置：从已登录首页点「请绑定房屋」入口进入绑定房屋表单页。
    登录由模块级 logged_in_app fixture 完成，此处不再重复登录。
    :param driver: Appium driver
    :return: BindHousePage 页面对象
    """
    bind_page = BindHousePage(driver)
    bind_page.enter_bind_page()
    return bind_page


@allure.epic("移动端 App 自动化测试")
@allure.feature("绑定房屋模块")
class TestBindHouse:
    """首页绑定房屋业务测试用例集"""

    @allure.story("绑定入口与表单默认值")
    @allure.title("从首页进入绑定房屋页，表单默认值正确")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_enter_bind_page(self, driver):
        """
        正向用例：登录后点首页「请绑定房屋」，校验进入绑定表单页且默认值正确。
        :param driver: 由 conftest 提供的会话级 Appium driver
        """
        logger.info("开始执行用例：从首页进入绑定房屋页")

        with allure.step("点击已登录首页的「请绑定房屋」入口"):
            bind_page = enter_bind_page(driver)

        with allure.step("校验已进入绑定房屋表单页"):
            assert bind_page.is_bind_form_displayed(), "未进入绑定房屋表单页"
            assert bind_page.get_page_title() == "绑定房屋", "绑定页标题不正确"

        with allure.step("校验表单默认值：手机号预填、类型=个人客户、身份=业主、小区/房号未选"):
            assert bind_page.get_default_mobile() == VALID_ACCOUNT["account"], \
                "手机号未预填为登录账号"
            assert bind_page.get_default_type() == "个人客户", "默认客户类型不是个人客户"
            assert bind_page.get_default_identity() == "业主", "默认身份不是业主"
            assert bind_page.is_court_unselected(), "小区初始状态应为未选择"
            assert bind_page.is_house_unselected(), "房号初始状态应为未选择"

        logger.info("用例执行通过：绑定房屋表单页默认值校验完成")

    @allure.story("绑定表单校验场景")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        # 参数化：用 pytest.param 将每条数据包装为单个参数（避免 dict 被自动拆解），
        # 并用 case_name 作为用例 id 显示在报告中
        argnames=["case"],
        argvalues=[pytest.param(item, id=item["case_name"]) for item in BIND_HOUSE_DATA],
    )
    def test_bind_house_validation(self, driver, case):
        """
        数据驱动用例：进入绑定页后按 yaml 数据执行操作，校验 Toast 与去向。
        :param driver: Appium driver
        :param case: 单条测试数据字典（action/name/expected_toast/expected/case_name）
        """
        # 动态设置 allure 报告中显示的用例标题
        allure.dynamic.title(case["case_name"])

        logger.info(f"开始执行数据驱动用例：{case['case_name']}")

        with allure.step("从已登录首页进入绑定房屋表单页"):
            bind_page = enter_bind_page(driver)
            assert bind_page.is_bind_form_displayed(), "前置失败：未进入绑定房屋表单页"

        with allure.step(f"执行操作[{case['action']}]（姓名：{case['name'] or '不填'}）并立即捕获 Toast"):
            # perform_action 点击后立刻捕获 Toast（Toast 瞬态，延后就丢了）
            toast = bind_page.perform_action(case["action"], case["name"])

        with allure.step("校验 Toast 提示与页面去向"):
            if case["expected_toast"]:
                assert toast == case["expected_toast"], \
                    f"预期 Toast [{case['expected_toast']}]，实际 [{toast}]"
            if case["expected"] == "停留绑定页":
                assert bind_page.is_bind_form_displayed(), "预期停留绑定页，实际已离开"
                assert bind_page.is_court_unselected(), "操作应被拦截，小区应仍未选择"
            else:
                assert bind_page.wait_element_absent(bind_page.SUBMIT_BUTTON), \
                    "预期离开绑定页，实际仍停留"

        logger.info(f"用例执行通过：{case['case_name']}")

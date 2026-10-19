# -*- coding: utf-8 -*-
"""
登录页面对象（LoginPage）
------------------------------------------------
作用：PO 模式中的具体页面对象，封装被测 App（com.hd.smartVillage）的登录流程：
    首页小区入口 -> 登录页（默认短信登录）-> 切换密码登录 ->
    输入账号/密码 -> 勾选用户协议 -> 点击登录。
遵循 PO 设计原则：
    1. 页面元素定位（属性）与页面业务操作（方法）分离；
    2. 一个页面一个类，页面上的元素和操作都收敛在本类中；
    3. 业务方法返回页面对象或结果，方便脚本层链式调用与断言。
说明：元素定位基于真机控件树抓取的 resource-id / hint 属性。
若被测 App 控件有变化，可用 Appium Inspector 或 uiautomatorviewer 重新抓取。
"""
from appium.webdriver.common.appiumby import AppiumBy

from base.base_page import BasePage
from utils.logger import logger


class LoginPage(BasePage):
    """登录页面对象，继承 BasePage 复用所有基础元素操作"""

    # ------------------------------------------------------------------
    # 一、元素定位（属性）：集中管理本页所有控件的定位方式
    # ------------------------------------------------------------------
    # 首页小区入口（点击后进入登录页）
    COURT_ENTRY = (AppiumBy.XPATH, '//android.widget.TextView[@resource-id="com.hd.smartVillage:id/court_name"]')
    # 「切换密码登录」入口（登录页默认短信登录，点击后切换为账号密码表单）
    CHANGE_TO_PWD_LOGIN = (AppiumBy.XPATH, '//android.widget.TextView[@resource-id="com.hd.smartVillage:id/puc_btn_change"]')
    # 账号输入框：账号/密码两个输入框共用 resource-id，用 hint 区分
    # （hint 恒定不变，比按 text 区分更稳定，不受账号预填/输入状态影响）
    ACCOUNT_INPUT = (AppiumBy.XPATH,
                     '//android.widget.EditText[@resource-id="com.hd.smartVillage:id/puc_text_input" '
                     'and @hint="请输入手机号码"]')
    # 密码输入框
    PASSWORD_INPUT = (AppiumBy.XPATH,
                      '//android.widget.EditText[@resource-id="com.hd.smartVillage:id/puc_text_input" '
                      'and @hint="请输入密码"]')
    # 用户协议勾选框（不勾选时点击登录无响应，登录前必须勾选）
    AGREE_CHECKBOX = (AppiumBy.XPATH, '//android.widget.CheckBox[@resource-id="com.hd.smartVillage:id/puc_ckb_agree"]')
    # 「登录」按钮
    LOGIN_BUTTON = (AppiumBy.XPATH, '//android.widget.Button[@resource-id="com.hd.smartVillage:id/puc_btn_login"]')

    # ------------------------------------------------------------------
    # 二、单步操作（方法）：对单个控件的最基础操作封装
    # ------------------------------------------------------------------
    def dismiss_startup_dialogs(self, timeout=90):
        """
        关闭首启弹窗链，直到首页就绪（court_name 出现）或超时。
        清空 App 数据后重启会陆续弹出通知权限/隐私协议/温馨提示/推送引导/
        系统权限提示等弹窗，且每次出现顺序不完全一致；统一委托 base.dialogs
        的全局弹窗注册表处理（扫描期临时关隐式等待以加速，详见 base/dialogs.py）。
        :param timeout: 最长处理时间（秒），首启链给足冗余
        :return: 本次实际关闭的弹窗名列表
        """
        from base.dialogs import dismiss_known_dialogs
        dismissed = dismiss_known_dialogs(
            self.driver, timeout=timeout, ready_locator=self.COURT_ENTRY)
        if not self.is_element_present(self.COURT_ENTRY, timeout=1):
            logger.warning("首启弹窗处理结束仍未见首页入口，交由后续步骤显式等待报错")
        return dismissed

    def enter_login_page(self):
        """点击首页小区入口，进入登录页"""
        self.click(self.COURT_ENTRY)

    def choose_password_login(self):
        """切换为账号密码登录方式"""
        self.click(self.CHANGE_TO_PWD_LOGIN)

    def input_account(self, account):
        """输入账号（手机号）"""
        self.input_text(self.ACCOUNT_INPUT, account)

    def input_password(self, password):
        """输入密码"""
        self.input_text(self.PASSWORD_INPUT, password)

    def agree_protocol(self):
        """勾选用户协议勾选框（仅未勾选时才点击，避免把已勾选状态取消）"""
        if self.get_attribute(self.AGREE_CHECKBOX, "checked") != "true":
            self.click(self.AGREE_CHECKBOX)

    def click_login(self):
        """点击「登录」按钮"""
        self.click(self.LOGIN_BUTTON)

    def is_login_page_displayed(self, timeout=3):
        """
        判断是否仍停留在登录页（以登录按钮是否还在屏幕为依据）。
        :return: 仍停留在登录页返回 True，否则 False
        """
        return self.is_element_present(self.LOGIN_BUTTON, timeout)

    def wait_leave_login_page(self, timeout=15):
        """
        等待登录按钮消失，即确认登录成功、已进入首页。
        :return: 超时内离开登录页返回 True，否则 False
        """
        return self.wait_element_absent(self.LOGIN_BUTTON, timeout)

    def wait_login_success(self, retry=1, first_timeout=5, timeout=15):
        """
        等待登录成功（离开登录页）；冷启动后首次登录点击可能被 App 内部
        初始化（推送/统计 SDK 等）吞掉而不跳转，此时仍停留在登录页，
        补点一次登录按钮再等待，最多补点 retry 次。
        吞点击是秒级现象，首轮只等 first_timeout 秒即快速补点，
        避免白等满超时（实测每次登录可节省约 10 秒）。
        :param retry: 未跳转时登录按钮的补点次数
        :param first_timeout: 首轮等待秒数（快速判断点击是否被吞）
        :param timeout: 补点后每轮的等待秒数
        :return: 登录成功返回 True，否则 False
        """
        for attempt in range(retry + 1):
            wait_seconds = first_timeout if attempt == 0 else timeout
            if self.wait_leave_login_page(wait_seconds):
                return True
            if attempt < retry and self.is_login_page_displayed():
                logger.warning("登录点击后未跳转，补点一次登录按钮")
                self.click_login()
        return False

    # ------------------------------------------------------------------
    # 三、业务操作（方法）：由多个单步操作组合成一个完整业务动作
    # ------------------------------------------------------------------
    def login(self, account, password):
        """
        密码登录业务：输入账号/密码 -> 勾选用户协议 -> 点击登录。
        说明：进入登录页、切换密码登录两步由脚本层按流程单独调用本类对应方法。
        """
        self.input_account(account)
        self.input_password(password)
        self.agree_protocol()
        self.click_login()

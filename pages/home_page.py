# -*- coding: utf-8 -*-
"""
首页页面对象（HomePage）
------------------------------------------------
作用：封装登录成功后的「首页」元素与业务操作，作为 PO 示例，
演示页面对象之间如何跳转与协作。
说明：元素定位为【示例】，请替换为被测 App 的真实控件属性。
"""
from appium.webdriver.common.appiumby import AppiumBy

from base.base_page import BasePage


class HomePage(BasePage):
    """首页页面对象"""

    # ------------------------------------------------------------------
    # 一、元素定位（属性）
    # ------------------------------------------------------------------
    # 首页标题/欢迎语，用于校验是否成功进入首页
    HOME_TITLE = (AppiumBy.ID, "com.example.app:id/tv_home_title")
    # 退出登录按钮
    LOGOUT_BUTTON = (AppiumBy.ID, "com.example.app:id/btn_logout")

    # ------------------------------------------------------------------
    # 二、页面业务操作（方法）
    # ------------------------------------------------------------------
    def get_home_title(self):
        """获取首页标题文本，常用于登录成功后的结果断言"""
        return self.get_text(self.HOME_TITLE)

    def is_home_page_displayed(self):
        """判断首页是否已展示（首页标题是否出现）"""
        return self.is_element_present(self.HOME_TITLE)

    def logout(self):
        """
        点击退出登录。
        :return: 退出后回到登录页，返回 LoginPage 对象
        """
        self.click(self.LOGOUT_BUTTON)
        from pages.login_page import LoginPage
        return LoginPage(self.driver)

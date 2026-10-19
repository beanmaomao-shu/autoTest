# -*- coding: utf-8 -*-
"""
绑定房屋页面对象（BindHousePage）
------------------------------------------------
作用：封装登录后「首页绑定房屋」业务的元素定位与操作。
业务流程（真机快照探索得出）：
    登录后首页 court_name 显示「请绑定房屋」-> 点击进入绑定房屋表单页
    （未授予定位权限时会先弹「系统提示」弹窗，点「取消」跳过，城市显示定位失败）。
表单校验规则（实测）：
    1. 级联校验：未选城市点「小区」-> Toast「请先选择城市」，停留在表单页；
       未选小区点「房号」-> 被静默拦截，停留在表单页；
    2. 提交拦截：表单不完整（如只填姓名）点「绑定」-> Toast「小区未填写」，
       不跳转，停留在表单页；
    3. 表单默认值：手机号预填登录账号、类型=个人客户、身份=业主。
说明：真实绑定成功需要物业服务中心登记过的姓名/身份信息，且属于有业务
副作用的操作，故测试数据聚焦上述可稳定重复的校验规则。
"""
from appium.webdriver.common.appiumby import AppiumBy

from base.base_page import BasePage
from utils.logger import logger


class BindHousePage(BasePage):
    """绑定房屋页面对象"""

    # 被测 App 的 resource-id 前缀
    RID = "com.hd.smartVillage:id"

    # ------------------------------------------------------------------
    # 一、元素定位（属性）
    # ------------------------------------------------------------------
    # 首页绑定入口：未登录时该控件进登录页，登录后 text=「请绑定房屋」
    HOME_BIND_ENTRY = (AppiumBy.XPATH,
                       f'//android.widget.TextView[@resource-id="{RID}/court_name"]')
    # 位置权限「系统提示」弹窗的「取消」按钮（点它跳过定位授权）
    LOCATION_DIALOG_CANCEL = (AppiumBy.XPATH,
                              f'//android.widget.TextView[@resource-id="{RID}/bt_cancel"]')
    # 绑定页标题（text=「绑定房屋」）
    PAGE_TITLE = (AppiumBy.XPATH,
                  f'//android.widget.TextView[@resource-id="{RID}/tv_title"]')
    # 「绑定」提交按钮：表单页独有控件，作为"是否停留在绑定页"的状态锚点
    SUBMIT_BUTTON = (AppiumBy.XPATH,
                     f'//android.widget.TextView[@resource-id="{RID}/submit"]')
    # 城市/小区/房号三级选择器入口（FrameLayout 容器可点击）
    CITY_SELECTOR = (AppiumBy.XPATH, f'//android.widget.FrameLayout[@resource-id="{RID}/lt_city"]')
    COURT_SELECTOR = (AppiumBy.XPATH, f'//android.widget.FrameLayout[@resource-id="{RID}/lt_court"]')
    HOUSE_SELECTOR = (AppiumBy.XPATH, f'//android.widget.FrameLayout[@resource-id="{RID}/lt_house"]')
    # 未选择时的占位文本（这些 TextView 无 resource-id，用恒定 hint 定位；选中后占位消失）
    COURT_PLACEHOLDER = (AppiumBy.XPATH, '//android.widget.TextView[@hint="请选择小区"]')
    HOUSE_PLACEHOLDER = (AppiumBy.XPATH, '//android.widget.TextView[@hint="请选择房号"]')
    # 姓名输入框（无 resource-id，用 hint 定位）
    NAME_INPUT = (AppiumBy.XPATH, '//android.widget.EditText[@hint="请输入姓名"]')
    # 手机号/类型/身份的当前值（TextView 预填，无 resource-id）：
    # 手机号用 hint 区分标签与值；类型/身份取各自容器内第 2 个 TextView（第 1 个是标签）
    MOBILE_VALUE = (AppiumBy.XPATH,
                    f'//android.widget.FrameLayout[@resource-id="{RID}/mobile_number"]'
                    '//android.widget.TextView[@hint="请输入手机号码"]')
    TYPE_VALUE = (AppiumBy.XPATH,
                  f'(//android.widget.FrameLayout[@resource-id="{RID}/guest_type"]'
                  '//android.widget.TextView)[2]')
    IDENTITY_VALUE = (AppiumBy.XPATH,
                      f'(//android.widget.FrameLayout[@resource-id="{RID}/resident_identity"]'
                      '//android.widget.TextView)[2]')

    # ------------------------------------------------------------------
    # 二、单步操作（方法）
    # ------------------------------------------------------------------
    def handle_location_dialog(self):
        """点绑定入口后若弹出定位权限「系统提示」，点「取消」跳过（不去设置定位）。
        委托全局弹窗注册表精确处理该弹窗：短超时轮询（可能弹也可能不弹，
        权限已授过则不弹），only 限定只扫定位权限提示，避免误点表单控件。"""
        from base.dialogs import DIALOG_SYSTEM_PROMPT, dismiss_known_dialogs
        dismissed = dismiss_known_dialogs(
            self.driver, timeout=3, only=(DIALOG_SYSTEM_PROMPT,))
        if dismissed:
            logger.info("已处理定位权限系统提示弹窗（点取消）")

    def click_bind_entry(self):
        """点击首页「请绑定房屋」入口"""
        self.click(self.HOME_BIND_ENTRY)

    def click_city_selector(self):
        """点击「城市」选择器"""
        self.click(self.CITY_SELECTOR)

    def click_court_selector(self):
        """点击「小区」选择器"""
        self.click(self.COURT_SELECTOR)

    def click_house_selector(self):
        """点击「房号」选择器"""
        self.click(self.HOUSE_SELECTOR)

    def input_name(self, name):
        """在「姓名」输入框输入内容"""
        self.input_text(self.NAME_INPUT, name)

    def click_submit(self):
        """点击「绑定」提交按钮"""
        self.click(self.SUBMIT_BUTTON)

    def capture_toast(self, timeout=3):
        """
        捕获当前 Toast 文本。Toast 是瞬态控件，消失后取文本会抛
        StaleElementReferenceException，这里兜底返回 None 而不是让用例报错。
        """
        try:
            return self.get_toast_text(timeout)
        except Exception as e:
            logger.warning(f"捕获 Toast 异常（视为未捕获）：{e}")
            return None

    # ------------------------------------------------------------------
    # 三、业务操作（方法）：由多个单步操作组合成一个完整业务动作
    # ------------------------------------------------------------------
    def enter_bind_page(self):
        """从首页进入绑定房屋表单页（自动处理位置权限弹窗）"""
        self.click_bind_entry()
        self.handle_location_dialog()

    def perform_action(self, action, name=""):
        """
        按数据驱动的 action 字段在绑定页执行对应操作，并立即捕获 Toast。
        :param action: city=点城市 / court=点小区 / house=点房号 / submit=点绑定
        :param name: 姓名输入内容，空字符串表示不输入
        :return: 操作后捕获到的 Toast 文本（无 Toast 返回 None）
        """
        if name:
            self.input_name(name)
        if action == "city":
            self.click_city_selector()
        elif action == "court":
            self.click_court_selector()
        elif action == "house":
            self.click_house_selector()
        elif action == "submit":
            self.click_submit()
        else:
            raise ValueError(f"未知的 action：{action}")
        # Toast 一闪而过，必须在点击后立即捕获
        return self.capture_toast()

    # ------------------------------------------------------------------
    # 四、判定方法：给脚本层断言用
    # ------------------------------------------------------------------
    def is_bind_form_displayed(self, timeout=5):
        """是否停留在绑定房屋表单页（以「绑定」按钮为状态锚点）"""
        return self.is_element_present(self.SUBMIT_BUTTON, timeout)

    def get_page_title(self):
        """获取页面标题文本（绑定页应为「绑定房屋」）"""
        return self.get_text(self.PAGE_TITLE)

    def is_court_unselected(self):
        """小区是否仍处于未选择状态（占位「请选择小区」还在）"""
        return self.is_element_present(self.COURT_PLACEHOLDER, timeout=3)

    def is_house_unselected(self):
        """房号是否仍处于未选择状态（占位「请选择房号」还在）"""
        return self.is_element_present(self.HOUSE_PLACEHOLDER, timeout=3)

    def get_default_mobile(self):
        """获取表单预填的手机号文本（应为登录账号）"""
        return self.get_attribute(self.MOBILE_VALUE, "text")

    def get_default_type(self):
        """获取默认客户类型文本（应为「个人客户」）"""
        return self.get_text(self.TYPE_VALUE)

    def get_default_identity(self):
        """获取默认身份文本（应为「业主」）"""
        return self.get_text(self.IDENTITY_VALUE)

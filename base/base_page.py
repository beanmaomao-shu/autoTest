# -*- coding: utf-8 -*-
"""
页面基类（BasePage）
------------------------------------------------
作用：PO（Page Object）设计模式的核心基类。
把所有页面对象都会用到的通用操作（查找元素、点击、输入、获取文本、
滑动、截图、显式等待等）统一封装在这里，
各具体页面（pages 层）继承本类，只需关注自己的元素定位和业务方法，
实现代码复用、降低维护成本。

元素定位约定：locator 统一使用元组形式，例如：
    (AppiumBy.ID, "com.xxx:id/username")
    (AppiumBy.XPATH, "//*[@text='登录']")
"""
import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# W3C 手势操作所需的类（Appium 2.x 使用 Selenium 的 Actions 实现滑动）
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder

from config.setting import EXPLICIT_WAIT
from utils.logger import logger


class BasePage:
    """页面对象基类，封装所有页面通用的元素操作方法"""

    def __init__(self, driver):
        """
        :param driver: Appium WebDriver 实例，所有操作都基于它执行
        """
        self.driver = driver

    # ------------------------------------------------------------------
    # 一、元素查找相关
    # ------------------------------------------------------------------
    def find_element(self, locator, timeout=EXPLICIT_WAIT):
        """
        显式等待元素出现在 DOM 中并返回该元素。

        :param locator: 元素定位器元组，如 (AppiumBy.ID, "xxx")
        :param timeout: 最长等待时间（秒）
        :return: 找到的元素对象；超时未找到则抛出异常
        """
        try:
            # presence_of_element_located：元素存在于页面即可返回
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            logger.info(f"成功找到元素：{locator}")
            return element
        except TimeoutException:
            logger.error(f"等待超时，未找到元素：{locator}")
            raise

    def find_elements(self, locator, timeout=EXPLICIT_WAIT):
        """
        查找一组匹配的元素（返回列表）。

        :param locator: 元素定位器元组
        :param timeout: 最长等待时间（秒）
        :return: 元素列表；未找到返回空列表
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.find_elements(*locator)) > 0
            )
            elements = self.driver.find_elements(*locator)
            logger.info(f"成功找到 {len(elements)} 个元素：{locator}")
            return elements
        except TimeoutException:
            logger.warning(f"未找到任何匹配元素：{locator}")
            return []

    def is_element_present(self, locator, timeout=3):
        """
        判断元素是否存在（不抛异常，返回布尔值），常用于流程判断。

        :param locator: 元素定位器元组
        :param timeout: 最长等待时间（秒）
        :return: 存在返回 True，否则 False
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def wait_element_absent(self, locator, timeout=EXPLICIT_WAIT):
        """
        等待元素从页面上消失（常用于确认页面已跳转），不抛异常，返回布尔值。

        :param locator: 元素定位器元组
        :param timeout: 最长等待时间（秒）
        :return: 超时内元素消失返回 True，否则 False
        """
        try:
            # invisibility_of_element_located：元素不可见或不存在时条件成立
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(locator)
            )
            logger.info(f"元素已消失：{locator}")
            return True
        except TimeoutException:
            logger.warning(f"等待超时，元素仍然存在：{locator}")
            return False

    # ------------------------------------------------------------------
    # 二、元素操作相关
    # ------------------------------------------------------------------
    def click(self, locator, timeout=EXPLICIT_WAIT):
        """
        等待元素可点击后执行点击操作。

        :param locator: 元素定位器元组
        :param timeout: 最长等待时间（秒）
        """
        try:
            # element_to_be_clickable：元素可见且可点击
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            element.click()
            logger.info(f"点击元素：{locator}")
        except TimeoutException:
            logger.error(f"元素不可点击或等待超时：{locator}")
            raise

    def input_text(self, locator, text, clear_first=True, timeout=EXPLICIT_WAIT):
        """
        向输入框输入文本。

        :param locator: 输入框元素定位器元组
        :param text: 要输入的内容
        :param clear_first: 输入前是否先清空输入框，默认清空
        :param timeout: 最长等待时间（秒）
        """
        element = self.find_element(locator, timeout)
        if clear_first:
            # clear() 清空输入框原有内容
            element.clear()
        element.send_keys(text)
        logger.info(f"在元素 {locator} 中输入内容：{text}")

    def clear(self, locator, timeout=EXPLICIT_WAIT):
        """清空输入框内容"""
        self.find_element(locator, timeout).clear()
        logger.info(f"清空输入框：{locator}")

    def get_text(self, locator, timeout=EXPLICIT_WAIT):
        """
        获取元素的可见文本内容。

        :param locator: 元素定位器元组
        :return: 元素的 text 文本
        """
        text = self.find_element(locator, timeout).text
        logger.info(f"获取元素 {locator} 的文本：{text}")
        return text

    def get_attribute(self, locator, attribute, timeout=EXPLICIT_WAIT):
        """
        获取元素的指定属性值（如 content-desc、text、enabled 等）。

        :param locator: 元素定位器元组
        :param attribute: 属性名
        :return: 属性值
        """
        value = self.find_element(locator, timeout).get_attribute(attribute)
        logger.info(f"获取元素 {locator} 的属性 {attribute} = {value}")
        return value

    # ------------------------------------------------------------------
    # 三、手势滑动相关（基于 W3C Actions，兼容 Appium 2.x）
    # ------------------------------------------------------------------
    def swipe(self, start_x, start_y, end_x, end_y, duration=800):
        """
        从起点坐标滑动到终点坐标。

        :param start_x: 起始 x 坐标
        :param start_y: 起始 y 坐标
        :param end_x: 结束 x 坐标
        :param end_y: 结束 y 坐标
        :param duration: 滑动耗时（毫秒），值越大滑动越慢
        """
        # 创建触摸类型的指针输入源
        actions = ActionBuilder(self.driver)
        pointer = actions.add_pointer(interaction.POINTER_TOUCH)
        # 按下起点 -> 移动到终点 -> 松开
        pointer.create_pointer_move(x=start_x, y=start_y)
        pointer.create_pointer_down(button=0)
        pointer.create_pause(duration / 1000)
        pointer.create_pointer_move(x=end_x, y=end_y)
        pointer.create_pointer_up(button=0)
        self.driver.perform(actions.get_interactions())
        logger.info(f"执行滑动：({start_x},{start_y}) -> ({end_x},{end_y})")

    def swipe_up(self, duration=800):
        """向上滑动屏幕（用于向下翻页/查看更多内容）"""
        size = self.driver.get_window_size()
        width = size["width"]
        height = size["height"]
        # 从屏幕中下部滑到中上部
        self.swipe(width // 2, int(height * 0.8), width // 2, int(height * 0.2), duration)

    def swipe_down(self, duration=800):
        """向下滑动屏幕（用于向上翻页/下拉刷新）"""
        size = self.driver.get_window_size()
        width = size["width"]
        height = size["height"]
        self.swipe(width // 2, int(height * 0.2), width // 2, int(height * 0.8), duration)

    def swipe_left(self, duration=800):
        """向左滑动屏幕（常用于轮播图切换）"""
        size = self.driver.get_window_size()
        width = size["width"]
        height = size["height"]
        self.swipe(int(width * 0.8), height // 2, int(width * 0.2), height // 2, duration)

    def swipe_right(self, duration=800):
        """向右滑动屏幕"""
        size = self.driver.get_window_size()
        width = size["width"]
        height = size["height"]
        self.swipe(int(width * 0.2), height // 2, int(width * 0.8), height // 2, duration)

    # ------------------------------------------------------------------
    # 四、辅助方法
    # ------------------------------------------------------------------
    def get_toast_text(self, timeout=EXPLICIT_WAIT):
        """
        获取 Android Toast 提示文本（Toast 一闪而过，需用 xpath 捕获）。

        瞬态控件防护（踩坑总结）：Toast 存活极短，定位到元素后再取 .text
        时控件可能已消失，抛 StaleElementReferenceException 使脚本崩溃。
        因此取值逐级降级：.text -> get_attribute("text")，均失败则按未捕获返回 None，
        绝不让 Toast 异常中断用例（由调用方按业务决定断言策略）。

        :return: Toast 的文本内容；获取不到返回 None
        """
        locator = (AppiumBy.XPATH, "//android.widget.Toast")
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            try:
                text = element.text
            except Exception:
                # .text 需再次请求控件属性，瞬态 Toast 可能已失效，改用属性快照兜底
                text = element.get_attribute("text")
            logger.info(f"捕获到 Toast 文本：{text}")
            return text
        except TimeoutException:
            logger.warning("未捕获到 Toast")
            return None
        except Exception as e:
            # Stale 等瞬态异常统一兜底：按未捕获处理，避免中断用例
            logger.warning(f"捕获 Toast 异常，按未捕获处理：{e}")
            return None

    def screenshot(self, file_path):
        """
        对当前屏幕截图并保存到指定路径。

        :param file_path: 截图保存的完整文件路径（.png）
        :return: 截图是否成功（布尔值）
        """
        try:
            self.driver.get_screenshot_as_file(file_path)
            logger.info(f"截图已保存：{file_path}")
            return True
        except Exception as e:
            logger.error(f"截图失败：{e}")
            return False

    def sleep(self, seconds):
        """强制等待（谨慎使用，优先用显式等待）"""
        time.sleep(seconds)

    def get_window_size(self):
        """获取屏幕尺寸，返回 {'width': x, 'height': y}"""
        return self.driver.get_window_size()

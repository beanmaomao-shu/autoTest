# -*- coding: utf-8 -*-
"""
Appium Driver 初始化工具模块
------------------------------------------------
作用：根据 config/config.yaml 中的 Appium Server 地址与设备能力配置，
创建并返回一个 Appium WebDriver（driver）实例。
driver 是操作手机、查找元素、执行手势的核心对象，
由 conftest.py 的 fixture 在会话开始时调用本模块创建，测试结束后关闭。
"""
from appium import webdriver
from appium.options.common import AppiumOptions
from selenium.webdriver.remote.remote_connection import RemoteConnection

from config.setting import COMMAND_TIMEOUT, IMPLICIT_WAIT
from utils.logger import logger
from utils.yaml_util import read_config


def get_remote_url():
    """
    根据配置文件拼接 Appium Server 的完整连接地址。

    :return: 形如 http://127.0.0.1:4723 的 URL 字符串（末尾不带斜杠）
    """
    config = read_config()
    appium_conf = config.get("appium", {})

    # 如果配置中直接写了完整 remote_url，则优先使用（去掉末尾斜杠，避免拼接出双斜杠路径）
    if appium_conf.get("remote_url"):
        return appium_conf["remote_url"].rstrip("/")

    host = appium_conf.get("host", "127.0.0.1")
    port = appium_conf.get("port", 4723)
    # Appium 2.x/3.x 的 path 为 "/"，1.x 为 "/wd/hub"
    path = appium_conf.get("path", "/").strip("/")
    # path 为 "/" 时 URL 末尾不能带斜杠：selenium 会在 URL 后直接拼接 /session 等命令路径，
    # 若末尾带斜杠会拼成 //session 双斜杠，Appium Server 路由匹配不到会报 404 unknown command
    url = f"http://{host}:{port}" + (f"/{path}" if path else "")
    return url


def get_capabilities():
    """
    从配置文件读取设备/App 能力配置（desired capabilities）。

    :return: 能力字典
    """
    config = read_config()
    return config.get("capabilities", {})


def create_driver():
    """
    创建 Appium WebDriver 实例（driver）。

    流程：
    1. 读取配置，拼接 Server 地址；
    2. 把 capabilities 逐项设置到 AppiumOptions；
    3. 建立与 Appium Server 的会话，返回 driver。

    :return: 已连接设备的 Appium driver 对象
    """
    remote_url = get_remote_url()
    capabilities = get_capabilities()

    logger.info(f"开始初始化 Appium driver，Server 地址：{remote_url}")

    # AppiumOptions 是 Appium-Python-Client 3.x 推荐的能力封装方式
    options = AppiumOptions()
    for key, value in capabilities.items():
        options.set_capability(key, value)

    try:
        # 客户端命令超时保护：设备端 uiautomator2 服务偶发假死（socket hang up）时，
        # selenium 默认会无限等待 HTTP 响应（实测挂起 14 分钟）；设置后超时快速报错。
        # 注意：RemoteConnection.set_timeout 是类级设置，且在建连接池时被读取，
        # 必须在 webdriver.Remote() 之前调用才生效。
        RemoteConnection.set_timeout(COMMAND_TIMEOUT)
        # 建立远程会话，成功后 driver 即可用于操作设备
        driver = webdriver.Remote(command_executor=remote_url, options=options)
        # 设置隐式等待：查找元素时最多等待 IMPLICIT_WAIT 秒
        driver.implicitly_wait(IMPLICIT_WAIT)
        logger.info("Appium driver 初始化成功")
        return driver
    except Exception as e:
        # 初始化失败时记录错误，方便排查（常见：Server 未启动、设备未连接、caps 错误）
        logger.error(f"Appium driver 初始化失败：{e}")
        raise


def quit_driver(driver):
    """
    安全关闭 driver 会话，释放设备资源。

    :param driver: 需要关闭的 Appium driver 对象
    """
    if driver:
        try:
            driver.quit()
            logger.info("Appium driver 已关闭")
        except Exception as e:
            logger.warning(f"关闭 driver 时出现异常：{e}")

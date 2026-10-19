# -*- coding: utf-8 -*-
"""
全局配置模块
------------------------------------------------
作用：统一管理整个框架中所有需要用到的绝对路径，以及全局常量。
其它模块通过导入本文件获取路径，避免在代码中到处硬编码路径字符串，
便于框架在不同机器 / Jenkins 环境下迁移。
"""
import os

# 获取当前文件所在目录（即 config 目录）的绝对路径
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# 通过 config 目录向上推导出整个项目的根目录
ROOT_DIR = os.path.dirname(CONFIG_DIR)

# ------------------------------------------------------------------
# 各层目录路径（使用 os.path.join 保证跨平台兼容性）
# ------------------------------------------------------------------
# APP 安装包目录：存放待测试的 .apk / .app 文件
APP_DIR = os.path.join(ROOT_DIR, "APP")

# 配置文件目录
CONFIG_FILE_DIR = os.path.join(ROOT_DIR, "config")

# 测试数据目录：存放 yaml / json / excel 等测试数据
DATA_DIR = os.path.join(ROOT_DIR, "data")

# 日志目录：存放框架运行日志
LOG_DIR = os.path.join(ROOT_DIR, "log")

# 测试报告目录：存放 allure 结果与报告
REPORT_DIR = os.path.join(ROOT_DIR, "report")

# allure 原始结果 json 目录（--alluredir 输出位置）
ALLURE_RESULT_DIR = os.path.join(REPORT_DIR, "allure-result")

# allure 可视化 html 报告目录
ALLURE_REPORT_DIR = os.path.join(REPORT_DIR, "allure-report")

# 失败截图目录：用例失败时自动截图保存位置
SCREENSHOT_DIR = os.path.join(REPORT_DIR, "screenshot")

# UI 控件树快照目录：utils/ui_dump.py 抓定位器时保存的 page_source XML
DUMP_DIR = os.path.join(LOG_DIR, "ui_dump")

# PO 页面对象目录
PAGES_DIR = os.path.join(ROOT_DIR, "pages")

# 测试脚本目录
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")


def ensure_dirs():
    """
    确保框架运行所需的目录都存在，不存在则自动创建。
    一般在框架启动时（run.py / conftest）调用一次。
    """
    for path in (LOG_DIR, REPORT_DIR, ALLURE_RESULT_DIR,
                 ALLURE_REPORT_DIR, SCREENSHOT_DIR, DUMP_DIR):
        os.makedirs(path, exist_ok=True)


# ------------------------------------------------------------------
# 全局常量配置
# ------------------------------------------------------------------
# 隐式等待时间（秒）：查找元素时的最大等待时长
IMPLICIT_WAIT = 10

# 显式等待时间（秒）：单个元素等待的超时时长
EXPLICIT_WAIT = 10

# 客户端命令超时（秒）：selenium 向 Appium Server 发每条 HTTP 命令的最长等待。
# 设备端 uiautomator2 服务偶发假死（socket hang up）时，若不设超时客户端会
# 无限等待（实测挂起 14 分钟）；设置后快速失败，便于重跑或重建会话。
# 取值需大于最慢的正常命令（建会话/冷启动约 40 秒，显式等待上限 15 秒）。
COMMAND_TIMEOUT = 120

# 日志文件名
LOG_FILE_NAME = "appium_test.log"

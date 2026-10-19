# -*- coding: utf-8 -*-
"""
日志工具模块
------------------------------------------------
作用：基于 Python 标准库 logging 封装统一的日志记录器。
框架中所有操作（元素点击、输入、断言、异常等）都通过该日志器输出，
同时打印到控制台并写入 log 目录下的日志文件，方便问题定位。
使用单例思想：全局复用同一个 logger，避免重复创建 handler 导致日志重复。
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from config.setting import LOG_DIR, LOG_FILE_NAME

# 日志输出格式：时间 - 文件名 - 行号 - 级别 - 具体内容
LOG_FORMAT = "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
# 时间格式
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class Logger:
    """日志记录器封装类（单例模式）"""

    # 类变量保存唯一的 logger 实例
    _logger = None

    def __new__(cls, *args, **kwargs):
        """重写 __new__ 保证全局只创建一个 logger 实例"""
        if cls._logger is None:
            cls._logger = super().__new__(cls)
            cls._logger._init_logger()
        return cls._logger

    def _init_logger(self):
        """初始化 logger：配置格式、级别、控制台与文件输出"""
        # 确保日志目录存在
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, LOG_FILE_NAME)

        # 创建日志器并设置最低级别
        self.logger = logging.getLogger("appium_test")
        self.logger.setLevel(logging.DEBUG)

        # 防止重复添加 handler（多次实例化时）
        if not self.logger.handlers:
            formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

            # 控制台输出：只显示 INFO 及以上，减少干扰
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # 文件输出：记录 DEBUG 及以上全部日志
            # RotatingFileHandler 支持日志按大小切割，单文件最大 10MB，保留 5 个备份
            file_handler = RotatingFileHandler(
                log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, msg):
        """记录调试级别日志"""
        self.logger.debug(msg)

    def info(self, msg):
        """记录普通信息级别日志"""
        self.logger.info(msg)

    def warning(self, msg):
        """记录警告级别日志"""
        self.logger.warning(msg)

    def error(self, msg):
        """记录错误级别日志"""
        self.logger.error(msg)

    def critical(self, msg):
        """记录严重错误级别日志"""
        self.logger.critical(msg)


# 对外暴露的全局日志对象，其它模块直接 from utils.logger import logger 使用
logger = Logger()

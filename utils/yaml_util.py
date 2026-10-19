# -*- coding: utf-8 -*-
"""
YAML 数据读取工具模块
------------------------------------------------
作用：封装对 yaml 文件的读取操作，供框架读取配置文件（config.yaml）
和测试数据文件（data 目录下的 yaml）使用。
统一封装后，业务代码无需关心文件打开、编码、异常处理等细节。
"""
import os

import yaml


def read_yaml(file_path):
    """
    读取指定 yaml 文件并返回其中的数据（字典或列表）。

    :param file_path: yaml 文件的绝对路径
    :return: 解析后的 Python 对象（dict / list）
    """
    # 校验文件是否存在，提前给出清晰报错，避免后续难以排查
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"yaml 文件不存在: {file_path}")

    # 以 utf-8 编码打开，保证中文内容正常读取
    with open(file_path, "r", encoding="utf-8") as f:
        # safe_load 安全解析 yaml，返回 Python 数据结构
        return yaml.safe_load(f)


def read_config():
    """
    读取框架核心配置文件 config/config.yaml。

    :return: 配置字典，包含 appium、capabilities 等节点
    """
    # 延迟导入，避免循环依赖问题
    from config.setting import CONFIG_FILE_DIR

    config_path = os.path.join(CONFIG_FILE_DIR, "config.yaml")
    return read_yaml(config_path)

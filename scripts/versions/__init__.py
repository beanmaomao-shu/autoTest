# -*- coding: utf-8 -*-
"""
versions 版本增量用例包
------------------------------------------------
按 App 版本分子目录存放新版本的增量/变更用例，例如：
    scripts/versions/v3_8_2/test_xxx.py
约定：
    1. 新版本的新业务用例先放对应版本目录，只在该版本验证期执行；
    2. 版本发布稳定后，把仍有效的用例迁入 scripts/regression/（固定回归集）；
    3. 单独执行某版本增量：pytest scripts/versions/v3_8_2
       只跑固定回归集：    pytest scripts/regression
"""

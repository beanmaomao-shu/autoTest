提供页面对象封装PO：pages层，页面对象封装，主要封装页面操作方法
-
- 封装每个页面对象：
    
    - 元素定位（属性）
    - 页面操作（方法） 【单步+业务+结果获取】

提供页面脚本层（pytest）：scripts层，主要封装测试的页面业务脚本
-
-封装测试脚本：测试用例（准备数据、调用测试方法、打印结果、断言）

目录组织（版本化管理）：
-
- scripts/regression/：固定回归集（版本无关的稳定用例，每轮 CI 必跑）
- scripts/versions/vX_Y_Z/：新版本增量用例（只在该版本验证期执行，稳定后迁入 regression/）
- 单独执行：pytest scripts/regression 或 pytest scripts/versions/v3_8_2；全量：python run.py

隔离 fixture（conftest.py 提供，用例按需显式声明）：
-
- clean_app：强隔离，清数据+重启+过弹窗链（约 100 秒/条），用于登录类/有副作用用例
- relaunch_app：弱隔离，仅重启保留登录态（约 15 秒/条）
- logged_in_app：模块级共享登录态（只登录一次），搭配 relaunch_app 用于无副作用用例提速
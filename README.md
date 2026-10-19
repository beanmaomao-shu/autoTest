# Python + Appium + PO + pytest + Allure + Jenkins 移动端自动化测试框架

一个分层清晰、开箱即用的 **Android/iOS App 自动化测试框架**。采用业界主流的
**PO（Page Object）设计模式**，整合 Appium、pytest、Allure、Jenkins，
实现「元素定位与业务分离、数据驱动、失败自动截图、可视化报告、持续集成」的完整闭环。

---

## 一、技术栈

| 组件 | 作用 |
| --- | --- |
| Python 3.10 | 开发语言 |
| Appium | 移动端自动化测试引擎（驱动 Android/iOS 设备） |
| PO 设计模式 | 页面对象模式，元素定位与操作分离，易维护 |
| pytest | 测试框架，负责用例组织、参数化、fixture、执行 |
| Allure | 生成美观的可视化测试报告 |
| PyYAML | 读取配置文件与测试数据（数据驱动） |
| Jenkins | 持续集成，定时/触发式自动执行测试并展示报告 |

---

## 二、目录结构

```
自动化框架/
├── APP/                    # 存放被测 App 安装包（.apk / .app）
├── base/                   # 基础封装层
│   └── base_page.py        # 页面基类：元素查找、点击、输入、滑动、截图等通用操作
├── config/                 # 配置层
│   ├── setting.py          # 全局路径与常量配置
│   └── config.yaml         # Appium Server 地址、设备/App 能力配置
├── data/                   # 测试数据层（数据驱动，与代码分离）
│   └── login_data.yaml     # 登录功能的测试数据
├── log/                    # 运行日志（自动生成）
├── pages/                  # PO 页面对象层
│   ├── login_page.py       # 登录页面对象（示例）
│   └── home_page.py        # 首页页面对象（示例）
├── report/                 # 测试报告（自动生成）
│   ├── allure-result/      # allure 原始结果 json
│   ├── allure-report/      # allure html 可视化报告
│   └── screenshot/         # 用例失败自动截图
├── scripts/                # 测试脚本层（pytest 用例）
│   ├── conftest.py         # 全局 fixture：driver 管理、失败截图、allure 集成
│   └── test_login.py       # 登录测试用例（示例）
├── utils/                  # 工具层
│   ├── logger.py           # 日志封装
│   ├── yaml_util.py        # yaml 读取封装
│   └── appium_driver.py    # Appium driver 初始化封装
├── venv/                   # Python 虚拟环境
├── Jenkinsfile             # Jenkins 持续集成流水线
├── pytest.ini              # pytest 运行配置
├── requirements.txt        # 项目依赖清单
├── run.py                  # 一键运行入口（执行用例 + 生成报告）
└── README.md               # 本说明文档
```

**分层设计思想**：`config/data`（配置与数据） → `utils/base`（工具与基类） →
`pages`（页面对象） → `scripts`（测试用例） → `run.py/Jenkinsfile`（运行与集成）。
上层依赖下层，职责单一，便于扩展与维护。

---

## 三、环境准备

### 1. 安装基础环境
- **Python 3.10+**（本项目使用 3.10.4）
- **Node.js** + **Appium Server 2.x**：
  ```bash
  npm install -g appium
  appium driver install uiautomator2      # Android 驱动
  appium -v                               # 验证安装
  ```
- **JDK**、**Android SDK**（含 adb，配置好环境变量）
- **Allure 命令行工具**：下载解压后将 `bin` 目录加入 PATH，`allure --version` 验证

### 2. 安装 Python 依赖
项目已在虚拟环境中安装好依赖，如需重装：
```bash
venv\Scripts\activate                     # Windows 激活虚拟环境
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 四、使用步骤

### 1. 修改配置
编辑 `config/config.yaml`，按实际情况填写：
- `appium.host / port`：Appium Server 地址
- `capabilities.deviceName / platformVersion`：设备信息（`adb devices` 查看）
- `capabilities.appPackage / appActivity`：被测 App 的包名与启动 Activity

### 2. 放入被测 App（可选）
将 `.apk` 放入 `APP/` 目录，并在 `config.yaml` 的 capabilities 中配置 `app` 路径。

### 3. 抓取元素、编写页面对象与用例
- 用 **Appium Inspector** 抓取元素属性，替换 `pages/*.py` 中的示例定位；
- 在 `pages/` 中按「一个页面一个类」新增页面对象；
- 在 `scripts/` 中新增 `test_*.py` 用例，通过页面对象完成业务操作；
- 测试数据写入 `data/*.yaml`，用 `@pytest.mark.parametrize` 实现数据驱动。

### 4. 启动 Appium Server
```bash
appium --address 127.0.0.1 --port 4723 --relaxed-security
```

### 5. 运行测试
```bash
# 方式一：一键运行（执行用例 + 生成 allure 报告）
python run.py

# 方式二：直接用 pytest 运行
pytest scripts

# 只运行冒烟用例（需给用例加上 @pytest.mark.smoke 标记）
python run.py -m smoke
```

### 6. 查看 Allure 报告
```bash
allure open report/allure-report
# 或者边跑边看
allure serve report/allure-result
```

---

## 五、Jenkins 持续集成

1. Jenkins 安装插件：**Allure Jenkins Plugin**、**Git Plugin**；
2. 「系统管理 → 全局工具配置」中配置 **Allure Commandline**（名称需与
   `Jenkinsfile` 中 `tools { allure 'allure' }` 一致）；
3. 新建 **Pipeline** 任务，选择「Pipeline script from SCM」，指向本仓库；
4. Jenkins 节点需提前装好 Python、Appium、Android SDK 并连接设备；
5. 构建时流水线会自动：拉取代码 → 装依赖 → 启动 Appium → 执行用例 → 生成并展示 Allure 报告。

---

## 六、核心机制说明

- **driver 复用**：`conftest.py` 中的 `driver` fixture 为 `session` 级别，
  整个测试会话只创建一个 driver，所有用例共享，减少 App 重启开销。
- **失败自动截图**：`pytest_runtest_makereport` 钩子在用例失败时自动截图，
  保存到 `report/screenshot/` 并附加到 Allure 报告。
- **统一日志**：所有操作通过 `utils/logger.py` 输出到控制台和 `log/appium_test.log`。
- **配置与数据分离**：设备配置、测试数据全部外置到 yaml，改配置无需动代码。

---

## 七、常见问题

| 问题 | 排查方向 |
| --- | --- |
| 连接 driver 超时 | Appium Server 是否启动、`config.yaml` 地址端口是否正确 |
| 找不到设备 | `adb devices` 是否能看到设备、`deviceName` 是否填写正确 |
| 元素定位失败 | 用 Appium Inspector 重新确认控件属性，检查等待时间 |
| allure 报告为空 | 是否安装 allure 命令行工具并配置到 PATH |
| 中文输入乱码 | capabilities 中开启 `unicodeKeyboard: true` |

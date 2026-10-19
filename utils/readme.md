这套方法的核心是：**把"人肉拿 Inspector 抓控件"变成"脚本拍快照 + 离线批量解析 + 假设验证"的循环**。临时脚本虽已清理，但实现细节如下，分四层讲。

## 一、dump 层：为什么走 `page_source` 而不是 adb

最初我试的是 `adb shell uiautomator dump /sdcard/ui.xml`，结果在这台模拟器上 uiautomator 进程直接被系统 **Killed**，文件根本写不出来（备选方案是 `adb exec-out uiautomator dump /dev/tty > 本地文件` 绕过设备文件系统）。于是我改走 Appium 通道：

```python
src = driver.page_source   # 本质是 GET /session/<id>/source，uiautomator2 server 返回当前窗口层级 XML
with open(f"log/page_{name}.xml", "w", encoding="utf-8") as f:
    f.write(src)
```

选它有三个关键理由：

1. **与断言同源**：`page_source` 和 `find_element(XPATH)` 用的是同一份控件树，dump 里能看到的属性，XPath 就一定能在运行时匹配到——验证定位器不会有"Inspector 里看得见、代码里找不到"的偏差；
2. **不受设备存储权限/进程被杀影响**；
3. **可嵌入操作步骤之间**：每操作一步拍一张快照，形成 `page_1_home → page_2_login_entry → page_3_pwd_form → page_4_after_login` 的**状态时间线**，事后可以逐帧对比。

## 二、探索脚本骨架：抗干扰的步骤编排

```python
def soft_click(driver, xpath, desc, wait=2):
    elems = driver.find_elements(AppiumBy.XPATH, xpath)   # 用 find_elements 而非 find_element：找不到返回 [] 不抛异常
    if elems:
        elems[0].click()
        time.sleep(wait)
        return True
    print(f"[SKIP] 未出现 {desc}")
    return False
```

两个设计点：

- **`find_elements` 当探针**：验证你给的 xpath 时先 `bool(driver.find_elements(...))` 打印 True/False（比如"账号定位输入前能找到: True"），不中断流程；
- **soft_click 容错编排**：弹窗顺序不固定时，"存在才点、不存在跳过"，保证探索脚本本身不会因某一步缺失而整轮报废；输入步骤还带了**回退定位器**（用户 xpath 找不到就退化成"第 N 个 `puc_text_input`"），确保每轮都能走到登录点击，拿到完整的状态时间线。

## 三、解析层：两个坑和两种解析器

**坑 1：标签名不是 `node`。** 我第一版用 `ET.fromstring(src).iter('node')` 遍历，结果一个控件都打印不出来。检查原始 XML 才发现这个 App 的 page_source **节点标签名是 class 全名**（`<android.widget.EditText .../>`），没有 `<node>` 标签。修正为 `root.iter()` 遍历所有标签、按属性过滤：

```python
root = ET.fromstring(src)
for el in root.iter():                       # 不假设标签名
    rid = el.get("resource-id") or ""
    text = el.get("text") or ""
    if ("smartVillage" in rid and (text or el.get("checked"))) or text in ("允许", "不同意", "同意"):
        print(f"{el.get('class')} | id={rid.split('/')[-1]} | text=[{text}] | checked={el.get('checked')}")
```

**坑 2：正则取属性的边界。** 批量对比多个 dump 文件时我改用原始文本正则（快、不用建树），但 `showing-hint="false"` 会误匹配 `hint` 的pattern，所以属性名前必须加空白边界：

```python
s = open(path, encoding="utf-8").read()

# ① 整屏控件 id 集合——用于"屏幕指纹"对比
ids = sorted(set(re.findall(r'resource-id="([^"]+)"', s)))

# ② 单控件段内取属性
def get(seg, k):
    m = re.search(r'\s' + k + r'="([^"]*)"', seg)   # \s 前缀防 showing-hint 误配 hint
    return m.group(1) if m else ""

for m in re.finditer(r'<android\.widget\.EditText[^>]*>', s):
    seg = m.group(0)
    print(get(seg, "resource-id"), get(seg, "text"), get(seg, "hint"), get(seg, "password"))
```

## 四、解析结果如何驱动决策（这才是价值所在）

| 批量解析的发现 | 得出的结论 | 落地的动作 |
|---|---|---|
| `page_3` 与 `page_4` 的 **id 集合完全相同** | 点击登录后**根本没跳页**（不是跳得慢） | 继续往下查原因 |
| 两份 dump 里 `puc_ckb_agree` 均 `checked=false`，而密码框 `text=••••` | 密码已输入、**协议没勾** → 登录被静默拦截 | 新增 `agree_protocol()` 步骤 |
| 账号框 `text=13392231931` 且 `showing-hint=false`、`hint=请输入手机号码` | 账号是**预填**的，你给的 `@text` 定位只在预填态成立 | 改用恒定的 `@hint` 定位 |
| 各轮首启 dump 依次出现 `permission_deny_button`→`ensure(我知道了)`→`notificationSettingCloseBtn`→`bt_cancel`，且**两轮顺序不同** | 5 层弹窗链、顺序不固定 | 全局弹窗注册表 `base/dialogs.py`（单一事实来源）+ 逐轮扫描关闭 |
| 失败截图：输入齐全、协议已勾、按钮仍在 | 冷启动首次点击被吞 | `wait_login_success` 补点重试 |

配合的旁路侦察还有：`pm list packages` 确认安装、`cmd package resolve-activity` 查启动 Activity、`ping` 排除网络因素、失败截图人工（视觉）复核——XML 回答"控件在不在"，截图回答"屏幕上到底发生了什么"。

## 五、成本与边界

每轮"改脚本→真机跑→dump→解析"约 1~2 分钟，这轮总共跑了七八轮才收敛；它的前提是**控件树可见**——WebView 深层 DOM、Canvas、验证码这类 dump 里看不到的东西，这套方法就失效了，得退回图像识别或接口层验证。

以后 App 改版定位器失效，标准动作就是：snap -k 关键字 抓新定位器 → 改 login_page.py 一处 → 跑用例验证。
## 六、探索一个"指定页面 + 指定业务"并落成测试代码的标准流程
以框架现有分层（config → utils → base → pages → data → scripts）为骨架，探索一个"指定页面 + 指定业务"并落成测试代码的标准流程是 7 步。下面用上一轮 `snap` 时真实看到的"**我的房屋**"页面作为例子走一遍。

## 第 1 步：确认环境和配置

- Appium Server（4723）、模拟器已启动；
- [config.yaml](file:///D:/project/自动化框架/config/config.yaml) 里 `appPackage` / `appActivity` / `deviceName` 与被测 App 一致。换 App 才需要动它，探索新页面不用改。

## 第 2 步：探索页面 —— ui_dump.py 抓控件

```powershell
# ① 手动在模拟器上点到目标页面（比如：首页 → "我的"tab → 看到"我的房屋"入口）
# ② 拍快照：先看整页有什么
python utils/ui_dump.py snap -n mine_page
# ③ 用关键字缩小范围，找目标控件
python utils/ui_dump.py show log/ui_dump/mine_page.xml -k 房屋
```

输出直接给出定位器素材（上次实测的真实数据）：

```
RelativeLayout | mine_house |          |
TextView       | tv_des     | 我的房屋 |
```

两个探索技巧：

- **验证跳转**：操作前 `snap -n before`，操作后 `snap -n after`，`diff before after`——id 集合有差异才说明真的跳页了，差异列表就是新页面的控件；
- **点击没反应**：diff 结果相同 → 要么被弹窗挡住，要么点击被吞，再 snap 看当前屏到底停在哪。

## 第 3 步：写页面对象（pages 层）

新建 `pages/mine_page.py`，继承 [BasePage](file:///D:/project/自动化框架/base/base_page.py)，按"**定位器 → 单步操作 → 业务方法 → 判定方法**"四段式组织（照抄 [login_page.py](file:///D:/project/自动化框架/pages/login_page.py) 的结构）：

```python
class MinePage(BasePage):
    # 一、定位器：从 snap 表里挑，优先 resource-id，其次 text/hint
    MINE_TAB = (AppiumBy.XPATH, '//android.widget.TextView[@text="我的"]')
    MY_HOUSE_ENTRY = (AppiumBy.XPATH, '//android.widget.RelativeLayout[@resource-id="com.hd.smartVillage:id/mine_house"]')
    HOUSE_PAGE_FLAG = (AppiumBy.XPATH, '...')   # 新页面独有控件，用 diff 结果确定

    # 二、单步操作
    def goto_mine_tab(self):
        self.click(self.MINE_TAB)

    def click_my_house(self):
        self.click(self.MY_HOUSE_ENTRY)

    # 三、业务方法：组合成完整业务动作
    def enter_my_house(self):
        self.goto_mine_tab()
        self.click_my_house()

    # 四、判定方法：给脚本层断言用
    def is_house_page_displayed(self, timeout=3):
        return self.is_element_present(self.HOUSE_PAGE_FLAG, timeout)

    def wait_enter_house_page(self, timeout=15):
        return self.wait_element_absent(self.MY_HOUSE_ENTRY, timeout)   # 入口消失=已离开
```

**判定依据怎么选**：找一个"目标页独有"或"原页面独有"的控件，用 BasePage 现成的 `is_element_present`（还在=没跳）/ `wait_element_absent`（消失=跳了）来断言，不要 sleep 后硬查。

## 第 4 步：处理测试数据（data 层）

有数据驱动需求才建 `data/mine_data.yaml`；纯导航类用例（点进去验证到达）不需要数据文件。

## 第 5 步：写测试脚本（scripts 层）

新建 `scripts/test_mine.py`，结构照抄 [test_login.py](file:///D:/project/自动化框架/scripts/test_login.py)：**准备 → 调页面方法 → 断言**，脚本层绝不直接碰元素（PO 原则）：

```python
@allure.epic("移动端 App 自动化测试")
@allure.feature("我的模块")
class TestMine:

    @allure.story("我的房屋")
    @allure.title("从我的页进入我的房屋页面")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_enter_my_house(self, driver):
        mine_page = MinePage(driver)
        with allure.step("进入我的tab并点击我的房屋"):
            mine_page.enter_my_house()
        with allure.step("校验已到达房屋页面"):
            assert mine_page.wait_enter_house_page(), "点击我的房屋后未进入房屋页面"
```

**注意 conftest 的隔离策略**：[conftest.py](file:///D:/project/自动化框架/scripts/conftest.py) 提供三级隔离 fixture——`clean_app`（函数级强隔离：清数据 + 重启，回到未登录首启态，约 15 秒）、`relaunch_app`（函数级弱隔离：仅重启保留登录态，约 6 秒）、`logged_in_app`（模块级共享登录态：只登录一次）。“我的房屋”是**登录后**的功能，应让用例依赖 `logged_in_app`（模块内共享登录）+ `relaunch_app`（每条回首页），无需每条重登。这是新业务接入时最容易踩的坑。

## 第 6 步：运行调试

```powershell
# 只跑新模块，快速迭代
venv\Scripts\python.exe -m pytest scripts/test_mine.py -s
```

失败时的排查顺序：控制台日志 → `report/screenshot/` 自动截图（看当时屏幕停在哪）→ 对可疑页面再 `snap`，用 diff 定位是"没跳到"还是"跳到了但判定控件选错了"。

## 第 7 步：出报告

全量跑 `python run.py`（pytest + Allure 一条龙），报告里 epic/feature/story 会自动把你新模块归类到"我的模块"下。

## 循环总结

```
手动到达页面 → snap/diff 抓控件 → pages 写 PO → scripts 写用例 → 跑 → 失败看截图再 snap → 通过 → run.py 出报告
```

核心心法就一条：**探索靠 ui_dump（所见即所得的控件表），沉淀靠 PO 分层（定位器只写一处）**——以后这个页面改版，只需要重新 snap 后改 `mine_page.py` 的定位器，脚本层一行不用动。

## 七、实战案例：首页绑定房屋业务（已落地，4 条用例全部通过）

按上面 7 步流程真实执行了一遍，产出：`pages/bind_house_page.py` + `data/bind_house_data.yaml` + `scripts/test_bind_house.py`（4 passed in 305s）。

**探索过程（3 轮 dump 下钻）**：

1. 第 1 轮：清数据→过弹窗→登录后扫首页，发现 `court_name` 登录后显示「请绑定房屋」（同一控件未登录时进登录页）；「我的→我的房屋」页有 `btn_house_bind`；
2. 第 2 轮：点绑定入口先弹**位置权限系统提示**（`bt_cancel` 取消 / `bt_confirm` 去设置），点取消后进入表单页：城市（定位失败）/小区/房号三级选择器 + 姓名/手机号/类型/身份 + `submit` 绑定按钮；
3. 第 3 轮：验证校验规则——未选城市点小区 Toast「请先选择城市」；未选小区点房号静默拦截；只填姓名提交 Toast「小区未填写」且停留表单页。

**关键设计决策**：

- 真实绑定成功需要物业登记数据且有业务副作用（改变账号状态），数据驱动聚焦**可稳定重复的表单校验规则**（级联拦截/提交拦截/默认值）；
- Toast 是瞬态控件，事后取 `.text` 会抛 StaleElementReferenceException，必须在点击后**立即捕获**并 try/except 兜底（`BindHousePage.perform_action` 返回 Toast 文本）；
- 无 resource-id 的控件用恒定 hint 定位（姓名框/占位文本），类型/身份取容器内第 2 个 TextView（第 1 个是标签）；
- conftest 每条用例前 clearApp 退出登录，所以绑定用例的公共前置是先走登录流程（`login_and_enter_bind_page`）。

**新用例清单**：

| 用例 | 预期（来自 yaml） |
|---|---|
| 从首页进入绑定页，表单默认值正确 | 标题=绑定房屋、手机号预填、类型=个人客户、身份=业主 |
| 未选城市点小区 | Toast=请先选择城市 + 停留绑定页 |
| 未选小区点房号 | 停留绑定页（静默拦截） |
| 只填姓名提交 | 停留绑定页（提交拦截） |

## 八、把探索踩的坑固化为框架级防护

探索“首页绑定房屋”时踩的 5 个坑，除了临场绕过，都已下沉成框架代码，
以后所有用例 / 探索自动受益，不用再靠人记着规避。

| # | 坑 | 框架级防护（代码） | 落地文件 |
|---|---|---|---|
| 1 | uiautomator2 偶发 socket hang up，客户端无限等待（实测挂 14 分钟） | 建会话前设 selenium 客户端命令超时 `COMMAND_TIMEOUT=120` 秒，假死最多 2 分钟即报错 | `config/setting.py`、`utils/appium_driver.py`（`RemoteConnection.set_timeout`，须在 `webdriver.Remote()` 前调用） |
| 2 | Toast 瞬态，延迟取 `.text` 抛 StaleElementReferenceException 使脚本崩 | `get_toast_text` 取值逐级降级 `.text → get_attribute("text") → None`，并用 try/except 兜底，绝不中断用例 | `base/base_page.py` |
| 3 | 弹窗定位分散在各页面、新场景弹窗漏登记 | 全局弹窗注册表 `KNOWN_DIALOGS` 单一事实来源，各页面/fixture 统一委托 `dismiss_known_dialogs()`；新弹窗加一行全局生效 | `base/dialogs.py`（`LoginPage.dismiss_startup_dialogs`、`BindHousePage.handle_location_dialog` 均改为委托） |
| 4 | 首启弹窗链每轮重跑约 100 秒（隐式等待 10 秒 × 每个不在屏定位器） | 扫描期临时把隐式等待降为 0（在就点、不在秒过），`finally` 还原；首启链降到约 15 秒 | `base/dialogs.py` |
| 5 | 探索轮次切分太细、每轮重复建会话 + 登录前置 | `ui_dump.py` 新增 `walk`：复用一个会话连续走查多屏、每回车快照 + 自动 diff 上一屏，一次登录探索多个假设 | `utils/ui_dump.py` |

实测效果：全量 7 条用例从约 507 秒降到 **177 秒**（缩短约 65%），主要来自坑 3/4 的弹窗链提速。

**探索新页面的推荐姿势（省积分）**：

```powershell
# 一次登录，人工在手机上逐屏导航，每按回车快照 + 自动 diff，走到哪拍到哪
python utils/ui_dump.py walk -p <业务名>
```

探索出的新页面/弹窗/坑点，随手补录进 [docs/page_map.yaml](file:///D:/project/自动化框架/docs/page_map.yaml)（页面地图），下次新用例先查图、零探索编码。


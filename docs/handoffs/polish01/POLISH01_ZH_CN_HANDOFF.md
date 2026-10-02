# ShockPath Competition Polish 01 — 中文界面交接

本轮完成中文主界面、科学术语统一与中文排版适配。品牌 ShockPath、科研标识、公式、数据、路由和接口身份保持原样。未进入下一轮视觉体系优化。

```text
POLISH_STAGE=01
SCOPE=ZH_CN_LOCALIZATION
POLISH01_STATUS=PASS
BASE_COMMIT=9dfc886b558311fc3a0145fea686a8dc6f3627f7
FUNCTIONAL_V1_FREEZE=061cac00e7dc41211a7d347124328b92ac9aff82
FINAL_COMMIT=HEAD
BRANCH=codex/polish01-zh-cn
PRIMARY_LANGUAGE=ZH_CN
SCIENTIFIC_IDENTIFIERS_LANGUAGE=ORIGINAL
PAGES_TRANSLATED=20_PRIMARY_VIEWS;43_ROUTE_AND_TAB_SELECTIONS
REMAINING_ORDINARY_ENGLISH_ITEMS=0_IN_AUDITED_VIEWS
AMBIGUOUS_LANGUAGE_ITEMS=0
ROUTES_CHANGED=NO
API_CONTRACT_CHANGED=NO
SCIENTIFIC_SCHEMA_CHANGED=NO
SCIENTIFIC_VALUES_CHANGED=NO
BACKEND_TESTS=PASS;1356
FRONTEND_UNIT=PASS;18
FRONTEND_E2E=PASS;202;FAILED=0;SKIPPED=0;FLAKY=0
TYPECHECK=PASS
BUILD=PASS
OPENAPI_DIFF=NONE
BACKEND_CONTRACT_DIFF=NONE
SCIENTIFIC_SCHEMA_DIFF=NONE
PRODUCTION_MOCK_SCAN=0
SOURCE_PATH_EXPOSURE=0
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
1920x1080_QA=PASS;43_SELECTIONS
390x844_QA=PASS;43_SELECTIONS
BLOCKERS=NONE
NEXT_STAGE=COMPETITION_VISUAL_SYSTEM_POLISH
NEXT_STAGE_STARTED=NO
```

剩余验收已完成。Evidence 路径清除正则保持原样，隐藏提示在清除时通过集中词典输出“[来源路径已隐藏]”，因此即使嵌在长字符串中也能正确显示；单测保留五类 locator 清除和受控相对来源断言，E2E 保留无路径泄漏、无 file 链接和无下载断言。定向用例 1 项通过，随后完整前端套件 220 项通过（18 unit + 202 E2E），零失败、零跳过、零重试。最终结果见 [FRONTEND_TEST_RESULTS.json](FRONTEND_TEST_RESULTS.json) 与 [CHECKS.json](CHECKS.json)。此前中止运行和旧 78 项报告已被完整验收结果取代。

完整验收还发现并修复一项旧 E2E 选择器：门控对比按钮实际名称为“打开 匹配预算的门控对比”，测试原先查找“打开匹配预算门控对比”。角色选择器现使用按钮相同的两段集中词典文案，全部科学数值、URL、身份和返回状态断言保留；定向用例通过后重新完整运行 220 项套件并全部通过。首次完整运行报告仅作诊断留在忽略缓存中，最终收据来自第二次完整运行。

后端 1356 项通过记录沿用上个窗口（558.67 秒）；接手后未修改后端，最终 Git 审计确认 backend/config 与 BASE_COMMIT 完全一致。重新完成类型检查、生产构建、合同/公开资产审计、最终生产扫描与科研源完整清单对比，并用最终构建刷新两种分辨率的 86 组正文及 93 张截图。未启动 CFD，未进入下一轮优化。

提交身份使用 `HEAD` 解析：在本交接提交完成后运行 `git rev-parse HEAD` 即得到最终提交哈希，最终聊天报告给出字面 SHA。提交无法在自身内容中保存自身哈希，因此此处保留可解析引用。Git 审计与逐文件 OWNED 清单见 [GIT_AUDIT.json](GIT_AUDIT.json)。

完成区域包括 Entry、Home、Explore S1–S7、数字实验室目录、Case 8、门控消融、熵预算闭合、横向模态频谱、模态验证、Mach 3 圆柱绕流、跨流动对比、独立机制解析、证据中心三个分区和证据详情。加载、缺失、不支持、错误、来源、验证状态、返回动作、浏览器标题、无障碍标签与图表展示文案一并中文化。

新增轻量展示层 `frontend/src/presentation/zh-CN.ts` 与 `zh-CN.json`，包含 1353 条精确文案映射、集中状态词汇和七幕叙事。原始 DTO、API、registry 和 canonical enum 不变。选择器的显示标签与提交值分离；`option.value`、路由 query、证据返回上下文继续使用原值。映射未登记的身份、数值和公式原样透传，不进行全局单词替换。

图表只转换标题、图例、轴名、说明、tooltip 和无障碍文字。`chartCopy` 跳过数据、坐标、维度和数据源数组，并由单测验证引用保持、原始选项不变、零值与高精度小数不变。已有数值计算、选择步逻辑、快照索引、投影算法、掩膜和空间积分规则均未改动。

统一系统字体栈加入 PingFang SC、Microsoft YaHei、Noto Sans CJK SC、Source Han Sans SC；未下载字体。仅适配行距、文字换行、窄屏导航、表格与长标题。窄屏频谱/模态图局部滚动；增长验证与特征模态图的说明和绘图区留出间距，避免中文说明重叠。原有主题与组件结构沿用。

科学语义复核包括：严格一维下声学触发可存在，切向接收内容及跨模态切向输出为零；正熵产不代表所有模态统一增强阻尼；预算、空间分配、宏观响应不同；跨流动比较为描述性比较，不作统一排名。证据可读取与当前源码能否复现分开表达。源码漂移、数据漂移、依赖漂移的真假方向保持准确。

缺口继续显示：Cylinder 全轨迹累计二维分配、Near1D 权威五组 ε 原始扫描、Spectrum 序列化矩阵、完整线性/RK3 振幅历史。未补零、插值、生成生产科研数据或启动 CFD。

验证使用 PowerShell 7：

```powershell
# 仓库根目录：全部后端测试，1356 项通过（558.67 秒）
.\.venv\Scripts\python.exe -m pytest -q

# frontend 目录：类型检查、生产构建、18 单测 + 202 E2E
npm run build
npx playwright test --config=playwright.phase11.integration.config.ts

# 仓库根目录：已有冻结验证脚本
.\.venv\Scripts\python.exe -B -m scripts.verification.phase11_integration contracts
.\.venv\Scripts\python.exe -B -m scripts.verification.phase11_integration public
.\.venv\Scripts\python.exe -B -m scripts.verification.phase11_integration scan

# 真实 API + 生产 preview；分别运行两种分辨率
$env:POLISH_UI_URL='http://127.0.0.1:4410'
$env:POLISH_QA_WIDTH='1920'
$env:POLISH_QA_FOCUS='1'
node scripts/verification/polish01_browser.mjs
$env:POLISH_QA_WIDTH='390'
node scripts/verification/polish01_browser.mjs
```

完整前端套件沿用冻结阶段配置：单 worker、零重试，真实 API 与隔离的开发 MOCK 项目分别运行。旧测试只更新显示文本/角色选择器；scientific ID、DTO、精确科学数值和状态断言保留。新增三项单测专门验证展示映射对科学身份、科学数组及叙事边界的保护。运行明细见 [CHECKS.json](CHECKS.json)。

OpenAPI 独立导出、运行时文档与保存文档字节一致，47 条路径、298 个 schema，生成 TypeScript 类型字节一致。OpenAPI SHA-256 为 `4aaf96c4120805c61948cf590af12a4e21cd98b04d68e2585ca5f97e377626c4`，类型 SHA-256 为 `1fb6bff5d5075e6818c1f481995ce30dffd98cb2a7fd2d65ea379445811c1631`。详见 [CONTRACT_AUDIT.json](CONTRACT_AUDIT.json)。

生产扫描未发现 MOCK provider/payload、科研根目录或正向夸大结论。私有后端科研根目录和 locator 清除正则仅为内部实现。公开资产审计覆盖 2438 个来源资产，绝对路径暴露为 0、下载路由为 0；见 [PRODUCTION_SCAN.json](PRODUCTION_SCAN.json) 和 [PUBLIC_ASSET_AUDIT.json](PUBLIC_ASSET_AUDIT.json)。Vite 仍提示既有大 chunk；构建成功，本轮未扩大范围进行拆包重构。

科研源目录按路径、文件大小、修改时间和 SHA-256 对比前后完整清单。27843 个文件完全一致，目录指纹 `8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`。见 [SOURCE_PRESERVATION.json](SOURCE_PRESERVATION.json)。

截图、逐页正文扫描、可见英文动作标签清单与页面宽度记录见 [SCREENSHOT_AUDIT.md](SCREENSHOT_AUDIT.md)。自动普通英文残留扫描结合人工科学身份分类及图片复核使用，不把公式、文件名、哈希或 ID 误判为漏译。语言策略见 [LANGUAGE_AUDIT.md](LANGUAGE_AUDIT.md)，模糊项见 [AMBIGUOUS_LANGUAGE_ITEMS.md](AMBIGUOUS_LANGUAGE_ITEMS.md)。

Git 分类：起始工作区干净，PREEXISTING=0、UNRELATED=0；本轮前端、显示文案测试、截图验证脚本和交接材料为 OWNED。临时处理脚本及草稿已移入被忽略的 `.cache/polish01/tools`，不提交；后台服务、科研源、配置、依赖锁文件、生成类型均未变更。全部 gate 已通过；按逐文件 OWNED 清单暂存并提交，最终聊天报告确认实际提交和干净工作区。不推送，不自动进入下一轮。

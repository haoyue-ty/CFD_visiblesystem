# PHASE_A_STATUS

日期：2026-10-11。范围：ShockPath V2.5 Phase A 界面与功能整合，保留 Flask + Vue + TypeScript。

## 交付内容

| 项目 | 实施结果 |
| --- | --- |
| 顶部导航 | 两行布局；严格保留首页、新建计算、运行任务、算例库、帮助五个一级入口；等宽线性图标、Hover、键盘 Focus、子路由父级高亮。服务状态读取真实 Case Registry，区分可用、未启动和未知。 |
| 首页 | `/` 重定向 `/home` 并保留 query/hash；统一系统概览、两种真实模板、API 近期运行和六项能力说明。模板选择不启动计算，仍需验证、确认、启动。 |
| 算例库 | 只在实时区展示后端 `execution_available` 的算例；完整保留 Case 8、Gate、熵闭合、频谱、模态验证、圆柱绕流及跨流动回放。历史卡片标明“历史数据回放”，详情复用真实元数据提供统一信息结构。 |
| 运行任务 | 统一“全部任务 / 运行对比 / 参数扫描”二级导航；列表支持状态筛选、刷新和分页；详情整理身份、配置、时间、真实进度、日志与熵记录；结果保留流场、指标、熵曲线、原生 face 分配、右侧 AI、报告和证据。 |
| 对比与扫描 | 保留现有 A/B、q_aa / q_at 扫描与科学可比性检查；未改动计算或比较规则。 |
| 帮助中心 | 新增 `/help`：三步入门、CFD/Mach/CFL/网格/q_aa/q_at、运行状态、七幕教程/机制/证据入口，以及计算、回放、配置匹配、复现和 AI 的区别。 |
| 视觉规范 | 共享字体、宽度、颜色、间距、面板、按钮、表格、空状态和错误状态；没有新增 UI 框架或依赖。 |
| 路由兼容 | 保留所有 Run、报告、证据、比较、扫描、历史实验、教程与跨流动路径；旧跨流动 alias 继续有效。 |

顺带修复两处 Windows 运行文件竞争：读句柄占用导致心跳 JSON 原子替换失败；同时首次打开空锁文件时，在取得锁之前初始化可能与其他调用竞争。前者对已识别的 Windows 占用错误最多重试 20 次（累计等待上限 1.9 秒），后者把初始化放到取得锁之后。保留原子提交、跨进程互斥和异常传播，不涉及数值算法或 API 语义。已完成 Run 不再建立多余的 SSE 连接。

## 修改文件

新增组件与页面：

- `frontend/src/components/AppIcon.vue`、`AppNavigation.vue`：轻量图标和主导航。
- `frontend/src/components/WorkspaceNavigation.vue`、`RunSummaryList.vue`：运行分区导航和共享运行卡片。
- `frontend/src/components/LiveCaseCard.vue`、`HistoricalCaseInfo.vue`：真实可执行算例入口及历史算例信息。
- `frontend/src/pages/HelpPage.vue`：帮助中心。

新增支持文件：

- `frontend/src/presentation/navigation.ts`、`navigation.css`、`runs.ts`。
- `frontend/src/data/v2/useCaseRegistry.ts`、`frontend/public/shockpath.svg`。
- `frontend/playwright.phase-a.config.ts`、`frontend/tests/navigation.unit.spec.ts`、`frontend/tests/phase-a-workbench.spec.ts`。
- `tests/v2_p0/test_atomic_runtime_writes.py`、`tests/v2_p0/test_runtime_lock_initialization.py`、本报告。

修改现有文件：

- 应用与样式：`frontend/src/App.vue`、`frontend/src/router.ts`、`frontend/src/presentation/typography.css`、`frontend/src/presentation/zh-CN.json`、`frontend/index.html`。
- 页面：`frontend/src/pages/EntryPage.vue`、`HomePage.vue`、`LabPage.vue`、`ExperimentBuilderPage.vue`、`ExperimentDetailPage.vue`、`RunListPage.vue`、`RunWorkspacePage.vue`、`RunComparisonPage.vue`、`ParameterSweepPage.vue`、`RunReportPage.vue`、`RunEvidencePage.vue`。
- 数据与 AI 布局：`frontend/src/data/v2/experiments.ts`、`runs.ts`、`frontend/src/views/runs/RunAIView.vue`。
- 运行文件提交与锁初始化：`backend/solver_runtime/artifacts.py`、`run_store.py`。
- 测试与工具：`frontend/package.json`、`frontend/tests/case8-acceptance.spec.ts`、`case8-real-integration.spec.ts`、`evidence-real-api.spec.ts`、`explore-real-api.spec.ts`、`phase10-final-integration.spec.ts`、`phase11-final-integration.spec.ts`、`phase12-final-integration.spec.ts`、`routes.spec.ts`、`v2-p1-experiments.spec.ts`、`frontend/live-tests/v2-p7.spec.ts`、`tests/window3_frontend/case8_slice.spec.ts`、`scripts/verification/v2_p7_browser.mjs`。
- 说明文档：`README.md`、`项目说明.md`。

后续启动体验补充：新增根目录 `python.py`，支持 PyCharm 直接 Run；`scripts/serve_backend.py` 提供共享入口及启动输出，README 补充运行方式。该补充不涉及数值算法、接口或科学资产。

启动补充已完成语法检查、不同工作目录下的直接文件入口检查、原有模块入口兼容检查；通过截获 HTTP 监听调用验证入口，不启动重复服务。另检查当前真实 API 可响应、Case 8 可执行、前端返回 HTTP 200，记录于 `.cache/phase-a/python-entry-smoke.log`。

旧测试只更新入口、名称、对应导航操作和截图输出位置，保留科学断言、真实 API 联调和已有功能检查。新增截图写入 `output/playwright/phase-a/`，历史阶段验收截图保持原内容。

## 验证结果

| 检查 | 最终结果 | 记录 |
| --- | --- | --- |
| TypeScript 与生产构建 | `npm run build --prefix frontend` 退出码 0；无新增依赖。保留现有大型图表包的 chunk 大小提示。 | `.cache/phase-a/build-final.log` |
| 前端单元测试 | 20 passed。 | `.cache/phase-a/frontend-final-full.json` |
| 导航、功能及兼容 E2E | 222 passed，其中 187 项使用真实 API / 生产构建，35 项为原有隔离 Mock UI 回归；0 skipped、0 unexpected、0 flaky。与单元测试合计 242 passed，耗时 10.5 分钟。 | `.cache/phase-a/frontend-final-full.json`、`frontend-final-full.xml` |
| 旧路由刷新强化检查 | 18 个子页面均等待真实数据加载、检查父级高亮后再刷新；独立重跑 1 passed，耗时 48 秒。 | `.cache/phase-a/frontend-routes-final.json` |
| 后端完整回归 | 1682 passed、1 skipped，耗时 715.40 秒。唯一跳过项是 `test_runtime_symlink_escape_rejected`：Windows 缺少创建符号链接的权限。 | `.cache/phase-a/backend-accepted.xml`、`backend-accepted.log` |
| Windows 文件竞争定向回归 | 原子写入、真实慢读句柄、锁初始化竞争、队列及 P7 扫描：69 passed。 | `.cache/phase-a/runtime-regression.xml` |
| 依赖与科学资产 | 43 个锁定依赖文件匹配，`scientific_writes=0`、`environment_changed=false`；冻结 Solver、API 模型与原有科学资产无 Git 差异。 | `.cache/phase-a/locked-source-verification.json` |

各轮计数独立记录，不相加。`git diff --check` 退出码 0。

真实运行验收记录：Run `7be66354-00ed-4d4e-849b-e97deefab32c`，Case 8 快速配置，64×16、CFL=0.05、T=0.04，478 个接受步、6 个真实快照。已核查流场、熵记录、四张原生 face 分配图、AI 不可用提示、报告生成/下载及运行证据。

- `config_hash`：`9b5263971c7a0814203080c1ad33303aaa0496fb4d738be5a7c73f225a7acd85`。
- `result_hash`：`67655ab02914ac8e772a2a0277bf9a2f100535cc1a5809738d5fd34c4bf70da0`。
- [已导出的真实 HTML 报告](../../output/playwright/phase-a/ShockPath-7be66354-00ed-4d4e-849b-e97deefab32c.html)。
- 四种宽度 × 五个一级页面的 20 张截图位于 `output/playwright/phase-a/`，例如 [桌面首页](../../output/playwright/phase-a/home-1440.png)、[手机首页](../../output/playwright/phase-a/home-390.png)、[完整运行结果](../../output/playwright/phase-a/completed-run-1440.png)。

## 原始目录保护

`D:\Paper\passage6` 始终只读使用。所有回归结束后的最终全目录审计为 **PASS**：修改前后均为 27,843 个文件、5,429,811,970 字节；相对路径、大小、mtime_ns 和每个文件的 SHA-256 全部一致。

修改前后的清单指纹均为 `8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`。原始目录没有新增、删除或修改文件；[完整审计结果](../../.cache/phase-a/source-preservation.json) 保存在本项目中。

冻结方法 `solver/fluxes/cross_mode_ec_unified_v1.py` 的 SHA-256 保持为 `98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0`。

## 本地启动

在 PowerShell 7 中打开两个终端。使用项目现有依赖：

终端一：

```powershell
Set-Location 'D:\code_project\CFD_visiblesystem'
./.venv/Scripts/python.exe -B -m scripts.serve_backend
```

终端二：

```powershell
Set-Location 'D:\code_project\CFD_visiblesystem\frontend'
npm run build
npm run preview -- --port 4173 --strictPort
```

打开 [首页](http://127.0.0.1:4173/home)。后端默认端口 5000；前端通过 Vite 代理访问真实 API。原始科研目录仍只读使用，输出与本次测试记录位于本项目 `runtime/`、`.cache/phase-a/`、`output/playwright/phase-a/`。

PyCharm 可使用项目 `.venv\Scripts\python.exe` 解释器，直接运行根目录 `python.py` 代替终端一的命令。它启动后端并显示地址；服务持续运行时控制台不会退出，前端仍需终端二。切换入口前先停止原后端，避免重复占用端口。

## 本地验收

1. 首页选择 Case 8 快速配置；在创建页验证、核对并确认配置，点击“启动求解”。三项主要操作分别为选择配置、验证确认、启动真实计算。
2. 在运行详情观察真实步数、物理时间和日志；完成后查看流场、熵曲线及原生 face 空间分配。
3. 在同一工作区打开 AI、生成报告并保存 HTML，进入科学证据核查配置与结果哈希。没有 AI 密钥时确认提示不可用，确定性报告仍可导出。
4. 查看运行列表的状态筛选，进入运行对比和参数扫描；核查不同条件的比较限制仍显示。
5. 在算例库区分实时计算和历史回放；通过帮助进入七幕教程、机制解释及证据中心。
6. 在 1440、1024、768、390px 宽度检查五项导航、当前高亮、键盘 Focus 和内容布局；断开后端时应显示未知/错误状态。

自动回归：

```powershell
Set-Location 'D:\code_project\CFD_visiblesystem'
npm run build --prefix frontend
npm run test:phase-a --prefix frontend
./.venv/Scripts/python.exe -B -m pytest -q
```

Phase A E2E 使用 5151/4451/4551 端口，自动关闭外部 AI 请求；真实 API 项目使用生产构建。4551 仅承载原有隔离的 Mock 回归，不参与真实求解验收。P7 兼容测试读取项目已有真实运行与扫描记录。

空记录、断网和运行管理器未启动的边界通过显式浏览器网络拦截检查；不删除已有运行，不构造科学结果。响应式检查使用 Chromium 的四种目标视口，并保存真实数据加载后的截图。

## 需要人工验证

Phase A 代码实施项已完成。

真实外部 AI 提供商的解读与问答未执行：本次明确关闭密钥，已验证不可用提示及无 AI 的真实求解、结果、证据和确定性 HTML 报告流程。若需验收外部 AI，按 README 配置本地密钥后，在已完成 Run 的右侧助手发起解读与问答。

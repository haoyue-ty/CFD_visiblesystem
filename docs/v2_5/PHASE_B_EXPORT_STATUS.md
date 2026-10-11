# ShockPath V2.5 Phase B 导出验收

日期：2026-10-11。项目：`D:\code_project\CFD_visiblesystem`。

已经实现从已验证、已完成 Case 8 Run 生成原始数据 ZIP、VTK/PVD ZIP、实验报告 ZIP，并分别下载 HTML 与 A4 PDF。运行详情和报告页面共用三个等宽 Lucide 图标卡片。下面的文件、大小、时间和哈希均来自本机真实 Run；导出验收没有重新执行这些 Run 的 Solver。

```text
PHASE_B_EXPORT_STATUS=COMPLETE
RAW_EXPORT=PASS; verified NPZ/JSON ZIP
CSV_EXPORT=PASS; all 39 source columns, round-trip floats, NA for missing
VTK_EXPORT=PASS; 18 real VTI frames, 9 Float64 CellData arrays
PVD_EXPORT=PASS; actual snapshot times and references
HTML_EXPORT=PASS; existing verified ReportService, offline SVG/data
PDF_EXPORT=PASS; 3 readable Chinese A4 documents, 15/13/13 pages
EXPORT_DIRECTORY=PASS; independent runtime/runs/<run_id>/exports/
EXPORT_MANIFEST=PASS; schema 1.0, per-file SHA-256/size/source
BACKEND_API_TESTS=PASS; full pytest 1705 passed / 1 skipped, including 23 export tests
FRONTEND_BUILD=PASS; vue-tsc and production Vite build
FRONTEND_E2E=PASS; final full run 230 E2E + 20 unit tests, 0 failed/skipped/flaky
SCIENTIFIC_DATA_MATCH=PASS; NPZ hashes and CSV/VTK values exact
PROVENANCE_UNCHANGED=PASS; three Runs retain all original scientific identities
KNOWN_LIMITATIONS=Case8 only; ParaView GUI not installed; PDF needs optional Chromium/fonts
```

## 实现与边界

生成入口先核对 Run 为 `COMPLETED`，原始文件与 provenance 清单的大小/SHA-256、科学结果身份、初末状态和真实快照的时间/形状。旧 Run 缺少已落盘的 `scientific_result.json` 时，使用既有 ScientificResultService 的只读投影，仅在 `exports/raw/` 序列化；没有给原始 Run 补写该文件。

原始 NPZ、配置、生效配置、provenance、已落盘科学结果、JSONL 和已有 derived 数组直接复制。CSV 保留 JSONL 所有列的并集，熵 CSV 作为附加投影；空缺和 null 均写 `NA`，浮点使用可往返精度。说明文件列出本次 Run 实际 NPZ 键和形状、守恒/原始变量、原生 face 的瞬时 Pi 与累计 A、SSP-RK3 各阶段和权重、诊断列及模型单位。没有把模型量宣称为已经标定的 SI 量。

Case8Exporter 独立于资源、缓存和 API 服务，复用 `backend/postprocess/case8.py` 的 `primitive_fields` 和网格定义。VTI 保存 density、pressure、velocity_x、velocity_y、speed、mach 和两个动量密度、总能量密度。只实现当前规则矩形网格的 ImageData；后续算例可登记相应导出器，VTS/VTU 不冒充当前可用格式。

VTK 使用 `(ny,nx)` 的 C 顺序，x 索引最快；数组位于 CellData。二维网格表现为一层 z 单元，z 厚度 `min(dx,dy)`、原点 `-min(dx,dy)/2`，单元中心位于 z=0。x/y 原点为域边界，单元中心为半格偏移后的原始位置，单元数严格为 nx×ny。二进制 Float64 数组无损输出；PVD 只引用真实快照和真实时间。

报告直接复用既有 ReportService、报告渲染器、受验证科学结果和可用 AI 缓存；本阶段生成和验收报告没有调用 AI provider。PDF 在受时限控制的独立 Chromium 进程中打印同一份 HTML，扩展已存在的指标说明、重复表头、控制分页和中文字体。PDF 失败时保留可用 HTML/报告 ZIP，清单明确原因，页面提供可用格式和重试；不会发布空 PDF。

`worker.py`、`case8_adapter.py`、`backend/postprocess/case8.py`、ScientificResultService 和 ReportService 均没有本阶段 Git 修改，冻结科研源码保持只读。

## 新增与修改文件

下表列的是 Phase B 的范围；工作区原有 Phase A 修改继续保留。

| 类型 | 文件 | 用途 |
| --- | --- | --- |
| 新增 | `backend/models/v2/export.py` | 分类、状态、能力、格式与下载元数据 |
| 新增 | `backend/services/v2/exports.py` | 来源验证、独立清单、锁、配额、缓存、原子发布与下载 |
| 新增 | `backend/services/v2/case8_exports.py` | 原始包、完整 CSV、说明、VTI/PVD |
| 新增 | `backend/services/v2/pdf_export.py`、`pdf_worker.py` | 可选能力发现和受控 A4 PDF 打印 |
| 新增 | `backend/api/v2/exports.py` | 遵循现有 catalog 的状态、生成和二进制下载接口 |
| 修改 | `backend/core/settings.py`、`.env.example` | 独立导出限制及可选 PDF 配置 |
| 修改 | `backend/api/catalog.py`、`backend/schemas/openapi.py`、`backend/core/app.py` | 注册新接口及 ZIP/HTML/PDF 响应契约 |
| 修改 | `backend/solver_runtime/artifacts.py`、`run_manager.py` | 原始输出指纹和 Solver 容量统计排除 exports；不改数值方法 |
| 修改 | `backend/api/v2/reports.py`、`frontend/src/data/v2/reports.ts` | 统一原有 HTML 下载文件名 |
| 新增 | `frontend/src/components/RunExportCenter.vue` | 三等宽卡片、真实能力、生成/失败/重试/下载反馈 |
| 新增 | `frontend/src/data/v2/exports.ts` | 类型化 API、下载响应核查、取消陈旧请求 |
| 修改 | `frontend/src/pages/RunWorkspacePage.vue`、`RunReportPage.vue` | 嵌入共享导出中心，保留已有结果和报告 |
| 修改 | `frontend/src/pages/ParameterSweepPage.vue` | 回归发现的定时刷新问题：加载状态恢复只清除加载错误，保留配置验证错误 |
| 修改 | `frontend/package.json`、`package-lock.json` | 官方 `@lucide/vue` 1.55.0、Phase B 浏览器测试入口 |
| 修改 | `config/openapi.json`、`frontend/src/types/generated/api.d.ts` | 同步生成接口契约 |
| 新增 | `tests/v2_exports/test_exports.py` | 23 项导出 API/格式/缓存/并发/失败/安全/配额验证 |
| 新增 | `frontend/playwright.phase-b.config.ts`、`frontend/tests/phase-b-exports.spec.ts` | 真实 Run 下载及负向交互的 8 项 E2E |
| 修改 | `tests/window1_evidence_core/test_evidence_core.py` | 保留 V1 来源保护；只允许新增的有限 V2 下载路由 |
| 修改 | `frontend/tests/phase-a-workbench.spec.ts`、`frontend/live-tests/v2-p7.spec.ts` | 保留路由/确认/预算断言，区分常驻导出状态并核查刷新不会抹除验证错误 |
| 修改 | `scripts/verification/phase11_integration.py` | 原有公开数据/生产扫描继续禁止 V1 下载，只识别受控 V2 文件发送器 |
| 新增 | `scripts/verification/phase_b_exports.py` | 已完成真实 Run 的 API、科学值、原始身份与 ZIP 验收 |
| 新增 | `scripts/verification/validate_case8_vtk.py` | 独立 VTK reader 数值、单元中心和 PVD 验证 |
| 新增 | `scripts/verification/validate_export_pdf.py` | PyMuPDF 实际打开、中文、A4、身份、边界和渲染检查 |
| 新增/修改 | `requirements-export-pdf.lock.txt`、`pyproject.toml` | 可选 PDF 依赖，保留原 Solver 核心环境 |
| 新增/修改 | 本文、`README.md` | 使用与完整验收记录 |

## 完整标准目录实例

实际 Run：`08f92162-b308-47ac-9a61-4aa1af08c048`。以下为面向用户的完整导出文件树；内部生成锁不是用户文件，临时目录在生成后已清理。

```text
runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/
├── raw/
│   ├── config.json
│   ├── effective_solver_config.json
│   ├── provenance.json
│   ├── result.json
│   ├── scientific_result.json
│   ├── initial_state.npz
│   ├── final_state.npz
│   ├── README.md
│   ├── export_manifest.json
│   ├── diagnostics/history.jsonl
│   ├── derived/
│   │   ├── physical_fields.npz
│   │   └── cumulative_faces.npz
│   └── snapshots/
│       ├── index.json
│       ├── step_000000.npz
│       ├── step_000096.npz
│       ├── step_000191.npz
│       ├── step_000287.npz
│       ├── step_000382.npz
│       └── step_000478.npz
├── diagnostics/
│   ├── history.csv
│   ├── entropy_budget.csv
│   ├── physical_metrics.json
│   └── README.md
├── visualization/
│   ├── field_000000.vti
│   ├── field_000001.vti
│   ├── field_000002.vti
│   ├── field_000003.vti
│   ├── field_000004.vti
│   ├── field_000005.vti
│   ├── timeseries.pvd
│   ├── README.md
│   └── export_manifest.json
├── reports/
│   ├── report.html
│   ├── report.pdf
│   ├── README.md
│   └── export_manifest.json
├── bundles/
│   ├── raw_data.zip
│   ├── flow_field.zip
│   └── experiment_report.zip
└── manifest.json
```

该 Run 清单登记 39 个真实导出文件。根 manifest 自身不递归记录自己的 SHA；ZIP 内附本分类的 `export_manifest.json`，避免清单与自身 ZIP 的循环哈希。根清单记录所有导出文件及 ZIP 的大小、SHA-256、来源，并单独绑定 `source_result_hash`、`source_identity_sha256`、exporter 版本和源码指纹。生成失败的格式不计入成功格式。

## API

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| GET | `/api/v2/runs/{run_id}/exports` | 真实能力、源身份、三类状态/清单和不可用原因 |
| POST | `/api/v2/runs/{run_id}/exports/raw` | 生成/复用 NPZ、JSON、CSV ZIP |
| GET | `/api/v2/runs/{run_id}/exports/raw/download` | 下载 `ShockPath_<run_id>_raw_data.zip` |
| POST | `/api/v2/runs/{run_id}/exports/visualization` | 生成/复用 VTI/PVD ZIP |
| GET | `/api/v2/runs/{run_id}/exports/visualization/download` | 下载 `ShockPath_<run_id>_flow_field.zip` |
| POST | `/api/v2/runs/{run_id}/exports/report` | 默认完整 ZIP；可选 `?format=html` 或 `?format=pdf` |
| GET | `/api/v2/runs/{run_id}/exports/report/download` | 默认报告 ZIP；同样支持 `format=html/pdf` |

实际 catalog 用有限 `kind=raw|visualization|report` 统一注册，因此 OpenAPI 新增 3 个路径、3 个操作，覆盖上述 7 个逻辑入口。原有 `/api/v2/reports/{run_id}` 及 HTML API 保留。JSON 继续使用原 V2 envelope；下载是真实 attachment，返回 Content-Length、正确 MIME 和 `X-Export-SHA256`，使用文件句柄流式发送。

状态为 `NOT_GENERATED / GENERATING / READY / FAILED`。非完成 Run 返回 409；无效分类/格式/额外参数返回 400；同一 Run 正在生成或全局并发满时返回可重试 429；容量超限为 413；PDF 缺失/渲染失败、超时等有明确错误。UUID、类型和格式受 DTO 校验，客户端不传任意文件路径。

同一 Run 用跨进程文件锁互斥；全局还有独立槽位和配额预约。写入临时目录、完整计算 ZIP 和哈希、复验原始来源后，通过原子重命名发布文件，最后提交 manifest。下载先取得锁和文件句柄；来源、导出器或文件校验变化会使缓存失效。生成中断会被状态检查识别，失败只影响 exports 层。

默认 Solver 原始输出上限仍为 64 MiB；**exports 不参与其容量或原始 fingerprint**。导出默认每 Run 256 MiB、全局 2 GiB、同时 2 个任务、每任务 90 秒，PDF 子进程最多 45 秒。全局按每 Run 上限保守预约，不自动删除已有科学结果或用户缓存。配置见 `.env.example`。

## 三组真实 Run 验收

三组均来自任务前已有的已完成 V2 Run，每组 6 个实际快照；导出过程不启动 Solver，不插值，不补造快照。

| Run ID | 网格 | CSV 行×列 | 原始文件哈希核对 | PDF | 特殊覆盖 |
| --- | --- | --- | --- | --- | --- |
| `08f92162-b308-47ac-9a61-4aa1af08c048` | 64×16 | 478×39 | 26 个，全一致 | 15 页 | 已存储科学结果/原生累计 face |
| `0ae640ee-5571-430e-8a07-5b1cd5c329e8` | 64×16 | 478×39 | 24 个，全一致 | 13 页 | 旧 Run 未存科学结果 JSON、无累计 face 文件 |
| `bc8cc641-951f-493c-a484-cd6b6f4eb0c6` | 128×32 | 956×39 | 26 个，全一致 | 13 页 | 不同真实网格及时间记录 |

主实例的实际 PVD 时间为：`0`、`0.008033472803347281`、`0.01598326359832636`、`0.024016736401673643`、`0.03196652719665272`、`0.04`。没有把记录时间替换为等间隔理想时间。

主实例实际 ZIP：

| 文件 | 大小（字节） | SHA-256 |
| --- | --- | --- |
| [raw_data.zip](../../runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/bundles/raw_data.zip) | 1,037,811 | `3aafe2824a1c2277b3e65f44175032ea4977f9ff20e7102baa5d9424481098a8` |
| [flow_field.zip](../../runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/bundles/flow_field.zip) | 283,451 | `59748f8f85106eda9b5ae70cfbd2e9ffcd036c3d6606c26131cc26c50cb6283d` |
| [experiment_report.zip](../../runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/bundles/experiment_report.zip) | 499,656 | `b3541e99fc4cd058e87e7cd8d1f660d339dda77e90b9e941fa7652fbece5a481` |

[实际 manifest](../../runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/manifest.json)、[离线 HTML](../../runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/reports/report.html)、[A4 PDF](../../runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048/exports/reports/report.pdf)。另外两组的三个 ZIP 和清单分别位于各自 `runtime/runs/<run_id>/exports/`。

### 科学一致性

| 内容 | 实际验证 |
| --- | --- |
| NPZ | 每份初始、最终、快照与已有 derived NPZ 的源/导出 SHA-256 相同；直接字节复制 |
| CSV | 所有源列和记录保留，时间、每个数值、最后累计量往返完全相同；缺失字段为 NA；单元测试另覆盖前后行缺列 |
| VTK | analysis-env 中 `vtkXMLImageDataReader` 实际打开全部 18 个 VTI，无格式错误；每个快照 9 个场均逐值相同，`rtol=0, atol=0`，最大绝对误差 0 |
| 网格 | 64×16 为 1024 单元、维度 65×17×2；128×32 为 4096 单元、维度 129×33×2。无 PointData，首末真实单元中心误差≤1e-14 |
| PVD | 引用存在，文件数=6，时间与源 NPZ/index 完全相同且严格递增 |
| HTML | 嵌入配置、科学结果、指标和累计量与既有 API 相同，4 个离线内嵌 SVG，Run/结果 hash 一致 |
| PDF | PyMuPDF 打开每页，A4、可提取中文、身份和所需章节匹配，无页外文字框；首屏、流场、熵图及表格已实际渲染检查 |
| 原始身份 | result_hash、solver_result_sha256、config_hash、冻结方法 hash、provenance SHA 以及原始 output_inventory 在导出前后不变 |

主实例的前后相同身份：

```text
result_hash=2ae44046772b2f2fe4018e29a161e1737812078b83e7ad2a07c6dbcb8daf621c
solver_result_sha256=ff592808ae2e7675ed530c45384187191d1e7f83ee9c0ecefeba0a831192fc6d
config_hash=9b5263971c7a0814203080c1ad33303aaa0496fb4d738be5a7c73f225a7acd85
method_sha256=98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0
provenance_sha256=5ab77806f3215060900fe5e59d8db7ee75a96fb4f782639f3d8e852a9b3fef2e
```

旧 Run `result_hash=0685bfb41d271ed2d0217b71260c6d4c604fd074e3a44116b64c632cf013e724`；128×32 Run `result_hash=63a092fe5f22844c9e408960970d2cc1d6b179774ea72809ec20d38bb041285e`。全部原始身份、NPZ 清单和 ZIP 元数据见三组 `output/phase-b/<run_id>/acceptance.json`，独立格式验收为同目录 `vtk-acceptance.json` 和 `pdf-acceptance.json`。

## 最终回归记录

| 检查 | 本轮结果 | 证据 |
| --- | --- | --- |
| 完整后端 pytest | 1705 passed / 1 skipped，818.68 秒；包含全部 23 项导出测试 | `.cache/phase-b/backend-results.xml`、`backend-results.txt` |
| 前端类型与构建 | PASS；仅既有图表包大于 500 kB 的构建提示 | `.cache/phase-b/frontend-build.log` |
| Phase B E2E | 8 passed，0 skipped/failed/flaky | `.cache/phase-b/frontend-results.json`、`frontend-results.xml` |
| 既有前端单元与全面兼容 E2E | 250 passed：20 单元 + 230 E2E；0 skipped/failed/flaky，15.4 分钟；含全部 8 项 Phase B 导出测试 | `.cache/phase-b/frontend-compatibility-final.json`、`frontend-compatibility-final.xml` |
| OpenAPI 与类型独立生成 | PASS；74 paths / 402 schemas，运行时与保存/独立生成完全一致 | `.cache/phase11-final/contracts.json` |
| 公开数据与生产扫描 | PASS；2438 个 source assets 无公开绝对定位路径；V1 无下载路由，仅有限 V2 导出发送器 | `.cache/phase11-final/public-audit.json`、`production-scan.json` |
| 冻结科研目录全量保护 | PASS；27,843 文件、5,429,811,970 字节；path/size/mtime_ns/SHA-256 全一致 | `.cache/phase-b/source-preservation.json` |

全部前端回归结束后再次完成冻结目录全量只读审计，结果仍为 PASS。最终桌面截图实际视口为 1440 px，手机为 390 px；浏览器最后保存的三个 ZIP 与相应 manifest SHA-256 完全相同。`git diff --check` 退出码 0。

新增 23 项后端测试覆盖原始/CSV/VTK/PVD/报告/ZIP/manifest、缓存损坏与复用、旧 Run、生成互斥与重复请求、失败状态、目录安全、大小与全局槽位限制、异常清理、初末状态及快照一致性。8 项 Phase B 浏览器测试使用真实 Run 完成三个 ZIP、HTML、PDF 下载和缓存复用；错误案例模拟服务/生成/下载失败及 PDF 缺失。390 px 与桌面均核查三等宽列和无横向溢出。

最终前端完整单轮的 230 项 E2E 中，195 项在真实 API / 生产构建项目，35 项为保留的隔离 Mock UI 回归；20 项单元测试单独计数。导出专项的 8 项包含在最终完整单轮中，不与其他轮次重复相加。机器可读汇总见 `output/phase-b/acceptance-summary.json`，公开契约/来源保护汇总见 `output/phase-b/compatibility-audit.json`。

原有 V1 测试的全应用“无下载路由”规则与本阶段新增下载冲突，因此明确限定为 V1；保留原公开 DTO、无绝对来源、无附件头、拒绝危险查询及来源下载的全部断言，并对全应用下载路由集合精确检查为唯一受控 V2 路径。原有测试没有删除。

冻结目录本轮只读审计的前后清单指纹均为 `8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`，与 Phase A 开发前的全量基线相同。验收用的 VTK/PDF 读取环境是 conda analysis-env，生产导出不引入 VTK 求解依赖。

后端唯一跳过项为 `test_runtime_symlink_escape_rejected`，原因是当前 Windows 无创建符号链接权限；其他路径、UUID、类型、清单与跨目录保护检查通过。前端完整兼容回归发现扫描列表定时刷新会清除用户验证错误，已将加载错误与操作错误分开，并强化原 P7 测试：非法预算仍不提供启动确认，刷新后错误持续可见。此修复不改变扫描配置、预算或 Solver 规则。

### 导出中心截图

![1440 px 真实完成 Run 的导出中心](../../output/playwright/phase-b/export-center-1440.png)

[完整运行页截图](../../output/playwright/phase-b/run-workspace-1440.png) · [390 px 三列布局](../../output/playwright/phase-b/export-center-390.png) · [实际 PDF 熵图与表格](../../output/phase-b/08f92162-b308-47ac-9a61-4aa1af08c048/page-06.png)。浏览器实际保存的五种下载文件位于 `output/playwright/phase-b/`。

## 使用与复验

在 PowerShell 7 启动原项目后，打开已完成 Run 的 `/runs/<run_id>`；三张卡片按需生成并下载，报告可选 ZIP、HTML、PDF。PDF 是可选服务端依赖，本机已安装锁定依赖并使用与 Playwright 匹配的 Chromium：

```powershell
./.venv/Scripts/python.exe -m pip install -r requirements-export-pdf.lock.txt
./.venv/Scripts/python.exe -m playwright install chromium
```

服务器还需可用中文字体，例如 Microsoft YaHei 或 Noto Sans CJK SC。未安装依赖/浏览器或管理员关闭 PDF 时，后端能力说明原因，页面仍支持 HTML。可用 `EXPORT_PDF_BROWSER` 指定可信可执行文件；配置不接受客户端提交的路径。

以下导出验收直接复用已有 Run，不启动数值 worker：

```powershell
./.venv/Scripts/python.exe -B -m pytest tests/v2_exports -q
./.venv/Scripts/python.exe -B -m scripts.verification.phase_b_exports --run-id 08f92162-b308-47ac-9a61-4aa1af08c048 --include-pdf
npm run build --prefix frontend
npm run test:phase-b --prefix frontend
```

独立 VTK/PDF 读取脚本使用用户 conda `analysis-env`，示例：

```powershell
conda run -n analysis-env python -B scripts/verification/validate_case8_vtk.py --run-dir runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048 --reference output/phase-b/08f92162-b308-47ac-9a61-4aa1af08c048/vtk-reference --output output/phase-b/08f92162-b308-47ac-9a61-4aa1af08c048/vtk-acceptance.json
conda run -n analysis-env python -B scripts/verification/validate_export_pdf.py --run-dir runtime/runs/08f92162-b308-47ac-9a61-4aa1af08c048 --output output/phase-b/08f92162-b308-47ac-9a61-4aa1af08c048
```

## 尚未实施与限制

1. 目前标准导出器实际支持 Case 8；VTS/VTU 和其他求解算例留待相应真实网格/结果支持后扩展。
2. 本机未安装 ParaView GUI，因此没有声称完成 GUI 人工打开；使用真实 VTK 读取器验证了全部数组、单元、时间、格式，而非仅检查 XML。
3. 旧 Run 缺少原生累计 face 数据时保留 `UNAVAILABLE`，不从标量历史反推或补造二维分配。
4. 模型尺度没有额外 SI 标定；PDF 需要可选依赖、Chromium 和中文字体。依赖缺失或渲染失败时 HTML 可用且 PDF 明确不可用。
5. 本阶段设置硬容量、时长和并发限制；没有新增自动缓存淘汰或大规模分布式导出队列。超过上限会明确拒绝，管理员可调整独立导出容量。

当前请求范围内的三个真实下载入口及所需格式均已实现，最终全量回归和科学验收结果见以上状态块与记录。

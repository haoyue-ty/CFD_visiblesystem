# ShockPath · 耗散路径数字实验与可视分析平台

> 项目目录：`CFD_visiblesystem`  
> 当前形态：**V1 回放 + V2 实时 Case 8**  
> 目标：把数值耗散的讨论从"结论"推进到"可追溯的证据链"

ShockPath 是一个面向计算流体力学（CFD）的交互式可视分析与数字实验平台，帮助使用者理解：**数值耗散由什么触发、作用在哪里，以及如何影响流动和不同模态。** 系统把两类实验统一在同一套界面中：

- **V1 · 回放**：只读加载已冻结、已验收的科研资产，覆盖 Case 8、Gate、熵预算闭合、横向模态频谱、模态验证、Mach 3 圆柱绕流、跨模态机制解释、七幕引导探索、跨流动对比与证据中心。启动或切换图表不会运行新的求解。
- **V2 · 实时**：在 V1 基础上，为 Case 8 提供"模板 / 专业参数 / 自然语言 → 后端校验 → 用户确认 → 独立 Run → 真实求解 → 确定性后处理 → AI 解释 → HTML 报告 → 对比与扫描"的完整闭环。原始科研源码保持哈希锁定、只读导入，**不做任何修改**。

项目始终强调三层关系的区分：**路径预算 → 空间分配 → 流动响应**。累计耗散量接近，并不保证空间分配相同；相同的耗散路径，在不同流动中也可能产生不同的响应。

---

## 1. 项目能做什么

| 场景 | 系统提供的能力 |
| --- | --- |
| 理解数值耗散机制 | 把触发信息、输出子空间、空间分配和宏观流动响应放在同一分析流程中 |
| 分析已有实验 | 切换配置、快照和结果视图，查看流场、熵预算、指标、频谱与模态验证 |
| **现场做新实验（V2）** | 用模板、专业参数或自然语言描述实验，确认真实求解并得到完整科学结果 |
| 教学与科普 | 通过七幕引导探索逐步阅读图表与结论，再进入完整实验分析 |
| 科研交流与答辩 | 从图表追溯到证据，核对方法、数据、哈希、验证状态与科学限制；一键导出 HTML 报告 |
| 结果对比 | 对两次已完成运行做同条件对比，或按已登记的 q_aa / q_at 做小规模串行扫描 |

---

## 2. 功能总览

### 2.1 V1：已有实验回放

**四个主要入口**

| 入口 | 用途 | 页面路径 |
| --- | --- | --- |
| 首页 Home | 进入平台、了解主题并选择分析入口 | `/home` |
| 引导探索 Explore | 按七幕故事浏览问题、图表、结论与证据 | `/explore?scene=1` |
| 数字实验室 Lab | 自主选择实验，进入完整工作区 | `/lab` |
| 证据中心 Evidence | 查询当前证据、数据缺口与历史记录 | `/evidence` |

网站入口是 `/`，点击「进入系统」进入首页。

**六类实验工作区**

| 实验 | 主要内容 | 阅读时需了解的边界 |
| --- | --- | --- |
| Case 8 | 流场回放、熵耗散历史、空间分配、指标与证据 | 支持 `A_u / B_u / C_u / D_u`；累计原生面空间分配仅 `D_u` 有记录 |
| 门控消融 Gate | 比较 Acoustic、Pressure、Ungated 的累计分配 | 各门控使用各自记录的匹配参数 |
| 熵预算闭合 Entropy Closure | 半离散、全离散诊断与时间加密对比 | 全离散残差属于数值诊断，非精确熵恒等式 |
| 横向模态频谱 Spectrum | 查看已记录频谱、模态及相关证据 | 序列化 Jacobian / Fourier 矩阵仍缺失 |
| 模态验证 Modal Validation | 查看记录的增长率与 CFD 投影幅值 | 已保存的线性 / RK3 幅值历史仍缺失 |
| Mach 3 圆柱绕流 Cylinder | 瞬时场、熵历史、扇区累计分配、指标与证据 | 完整轨迹累计二维分配仍缺失 |

另有跨模态耗散机制解释（`/lab/mechanism`）、跨流动对比（`/cross-flow`）与证据详情（`/evidence/:evidence_id`）。跨流动对比属于**描述性对比**，保留两侧不同定义与来源，不提供统一优劣排名。

所有实验目录入口均已交付；具体数据是否可用，仍由配置、数据资产与验证状态决定。

### 2.2 V2：实时数字实验（Case 8）

| 阶段 | 交付内容 |
| --- | --- |
| P0 | 能力核查与契约：候选源 symbol 清单、Capability Registry、transport 扩展与 runtime 隔离；V1 契约保持 byte-identical |
| P1 | 实验创建：模板 / 专业表单 / 自然语言三种入口，共享后端归一化、能力校验、模板血缘与 SHA-256，确认前反复校验 |
| P2 | 独立真求解：子进程复用哈希锁定的原始初始化、flux、有限体积 RHS、阶段保护的 SSP-RK3 与熵观测器 |
| P3 | 运行工作台：网页提交、单 worker 队列、真实进度、SSE 流、取消与重启恢复 |
| P4 | 科学结果：流场与派生场、全轨迹熵、宏观指标、原生 face 瞬时/累计分配、Run 专属证据 |
| P5 | AI 解释与科研助手：按结果哈希 / prompt 版本 / 模型缓存的自动解读，与基于当前视图的问答 |
| P6 | 实验报告：固定十二节、可离线打开的自包含 HTML，所有图表与数据内联 |
| P7 | 运行 A/B 对比与系数扫描：同条件对比、已登记 q_aa / q_at 四组合串行扫描 |

**关键设计原则**

- **验证与执行分离**：校验、AI 草稿与确认过程**不会启动 CFD**；只有明确的「启动求解」才会以确认后的哈希提交 Run。
- **软件状态与科学状态分离**：`RUNNING` 等运行状态与 `LIVE_PAPER_PROFILE` 等科学分类是两个独立字段。
- **AI 不参与计算**：AI 只产出已校验的解释文本；无密钥时模板 / 表单 → 确认 → 真实求解 → 科学结果 / 证据 → 确定性 HTML 报告仍然完整可用。

---

## 3. 快速开始

### 3.1 环境要求

- Windows 终端使用 **PowerShell 7（`pwsh`）**。
- Python **3.12 或更高版本**（见 `pyproject.toml`）。
- Node.js 满足 Vite 要求：`^20.19.0` 或 `>=22.12.0`。
- npm，用于安装与运行前端依赖。
- 可访问的原始科研数据目录。默认科研根目录为 `D:\Paper\passage6`。

Python 依赖锁定在 `requirements.lock.txt`，前端依赖锁定在 `frontend/package-lock.json`。当前功能不依赖 MySQL、邮箱验证码或账号登录；账号扩展保持关闭。

> 仅复制代码仓库**不能保证**所有科学图表在另一台电脑上可用，完整回放与实时求解都需要相应的原始科研资产。

### 3.2 首次安装

在项目根目录执行：

```powershell
Set-Location 'D:\code_project\CFD_visiblesystem'

python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
./.venv/Scripts/python.exe -m pip install --no-deps -e .

npm ci --prefix frontend
```

### 3.3 启动后端（终端一）

```powershell
Set-Location 'D:\code_project\CFD_visiblesystem'
./.venv/Scripts/python.exe -B -m scripts.serve_backend
```

默认后端地址为 `http://127.0.0.1:5000`，由 Waitress 承载 Flask 服务。

需要指定数据根目录时，在**启动后端的同一终端**先执行：

```powershell
$env:SCIENTIFIC_DATA_ROOT = 'D:\Paper\passage6'
```

如需从本地 Git 忽略的 `.env` 载入后端环境（包括 `DEEPSEEK_API_KEY`），使用 PowerShell 启动器代替 Python 入口：

```powershell
pwsh -NoProfile -File ./scripts/serve_backend.ps1
```

该启动器只载入已登记的设置、保留已有进程设置，**不会执行或打印** `.env` 内容。Python 入口与前端不会自动读取 `.env`；`.env.example` 是配置模板。

### 3.4 构建并启动前端（终端二）

```powershell
Set-Location 'D:\code_project\CFD_visiblesystem\frontend'
npm run build
npm run preview -- --port 4173 --strictPort
```

打开 [http://127.0.0.1:4173/](http://127.0.0.1:4173/) ，点击「进入系统」。`npm run build` 含 `vue-tsc --noEmit` 类型检查与生产构建；修改前端代码后需重新构建。Vite preview 将 `/api` 代理到 `127.0.0.1:5000`。

开发页面时可用 `npm run dev -- --port 5173 --strictPort` 代替，随后访问 `http://127.0.0.1:5173/`（后端仍需单独启动）。

端口被占用时分别设置 `$env:API_PORT`（后端）与 `$env:API_PROXY_TARGET`（前端代理目标）。

---

## 4. V2 使用流程（以 Case 8 为例）

1. 打开 **新建实验**（`/experiments/new`），选择 **模板 / 专业参数 / 自然语言** 之一，填写或描述实验配置。
2. 后端做归一化与能力校验，返回分类、模板血缘、协议差异与 SHA-256；界面要求**审阅并确认**，确认时再次校验。
3. 点击 **启动求解**，以确认后的哈希与持久重试键提交 Run（进入单 worker 队列）。
4. 在运行工作台 `/runs/:runId` 观察真实步数与时间、进度日志；成功后得到完整科学结果：
   - 选择密度 / 压力 / 速度分量 / 速度 / Mach，逐帧或播放六个已存快照；
   - 熵曲线覆盖全部已接受步；瞬时 Pi 与累计空间分配使用各自的原生 x / y face 视图；
   - 区域矩形统计基于真实网格中心；
   - **查看本次运行证据**（`/runs/:runId/evidence`）查看配置、有效配置、依赖 / 软件 / 输出哈希与科学限制。
5. 查看 **自动解读**，针对当前选中视图提问（问答基于当前字段、快照与矩形，无对话记忆）。
6. 点击 **生成 / 查看实验报告**（`/runs/:runId/report`），生成固定十二节报告，预览后 **保存 HTML**，可离线打开。
7. 在 `/workspace/compare` 对两次完成运行做同条件对比；在 `/workspace/sweeps` 按已登记 q_aa / q_at 做四组合串行扫描。

**当前开放范围**：仅 Case 8；`Nx/Ny`、`q_aa`、`q_at` 在已完成参数生效验证后开放；论文模式严格沿用已审计的 `A_u/B_u/C_u/D_u` 协议。`LIVE_PAPER_PROFILE` 只表示配置匹配，**不代表科学复现成功**。`epsilon`、Gate、高阶重构与自由快照间隔**不开放**新建运行。

**阅读时间数据时以实际记录时刻为准**：流场快照与标量历史采样粒度不同，时间关联使用已记录快照，不代表生成了任意时刻的新流场。配置、标签页、快照等选择写入 URL，支持刷新与历史恢复。

---

## 5. 配置项

后端设置使用进程环境变量；仅独立的 PowerShell 后端启动器会加载 `.env`。`.env.example` 记录了当前支持的变量：

| 变量 | 说明 |
| --- | --- |
| `SCIENTIFIC_DATA_ROOT` | V1 只读科研资产根目录 |
| `API_HOST` / `API_PORT` | 后端监听地址与端口 |
| `ENABLE_ACCOUNTS` | 账号扩展开关，默认关闭 |
| `DEEPSEEK_API_KEY` | 自然语言草稿与 AI 解释所需，缺失时相应入口不可用 |
| `DEEPSEEK_MODEL` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_TIMEOUT_SECONDS` | 默认 `deepseek-flash`、`https://api.deepseek.com`、30 秒 |
| `DEEPSEEK_MAX_RETRIES` / `AI_MAX_OUTPUT_TOKENS` / `AI_MAX_INPUT_CHARS` | 提供商请求与输入 / 输出保护 |
| `AI_DAILY_TOKEN_BUDGET` | UTC 自然日 token 预算上界，按保守上界预扣 |
| `MAX_CONCURRENT_RUNS` / `MAX_QUEUED_RUNS` / `MAX_RUN_SECONDS` / `MAX_RUN_OUTPUT_BYTES` | 运行并发、队列与资源限制 |
| `WAITRESS_THREADS` / `MAX_SSE_CONNECTIONS` | 服务线程与 SSE 流上限 |

AI 审计记录位于忽略的 `runtime/ai/`，只含哈希、长度、安全错误类别与用量，**不含凭证或提示词正文**。默认数值并发为 1。

---

## 6. 项目结构

```text
CFD_visiblesystem/
├─ backend/                 Python 后端
│  ├─ api/                  HTTP 操作与接口注册（含 api/v2）
│  ├─ adapters/             原始科研数据的只读适配器
│  ├─ services/             结果、证据与比较服务（含 services/v2）
│  ├─ models/               共享数据模型（含 models/v2）
│  ├─ registry/             实验、配置、来源与能力注册表（含 registry/v2）
│  ├─ postprocess/          V2 确定性后处理（流场、指标、face 分配）
│  ├─ ai/                   DeepSeek 客户端、上下文构建与解释
│  ├─ solver_runtime/       运行管理、单 worker 队列、进程与工件
│  ├─ schemas/              请求与 OpenAPI 模型
│  └─ core/                 应用、环境设置与错误处理
├─ frontend/                Vue 3 前端
│  └─ src/
│     ├─ pages/             页面入口（含 V2 新建 / 工作台 / 对比 / 扫描 / 报告）
│     ├─ views/             各科学模块视图
│     ├─ scientific/        科学图表与展示组件
│     ├─ data/              数据访问与结果组织（含 data/v2）
│     ├─ presentation/      中文文案与展示样式
│     └─ types/generated/   自动生成的 API 类型
├─ config/                  启动元数据、内容与接口契约
├─ data/                    科研资产清单与证据元数据
├─ docs/                    设计文档、阶段交接与验收记录（含 docs/v2）
├─ scripts/                 启动、契约导出、运行入口与审计 / 验收脚本
├─ tests/                   后端与科学语义验证（含 tests/v2_p0 … v2_p7）
├─ mind_design/             初期方案与产品规划
├─ requirements.lock.txt    Python 依赖锁定文件
├─ pyproject.toml           Python 包与测试配置
├─ README.md                本文件：项目概览与快速开始
└─ 项目说明.md              面向使用者的中文使用指南（V1 为主）
```

---

## 7. 验证与测试

文档阅读或日常回放无需先跑完整测试。修改代码后，可做基本校验：

```powershell
./.venv/Scripts/python.exe -B -m pytest -q
npm run build --prefix frontend
```

V2 各阶段定向测试：

```powershell
# 后端（示例：P4 科学结果）
./.venv/Scripts/python.exe -B -m pytest tests/v2_p4 -q

# 前端真实浏览器（需先构建）
node scripts/verification/v2_p4_live.py
```

**V1 完整既有验证流程**（按顺序执行，会产生审计输出）：

```powershell
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration capture
./.venv/Scripts/python.exe -B -m pytest -q
npm run build --prefix frontend
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration contracts
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration public
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration scan
Set-Location frontend
npx playwright test --config=playwright.phase11.integration.config.ts
```

仅当修改接口契约时，同步更新 OpenAPI 与前端类型：

```powershell
./.venv/Scripts/python.exe -B -m scripts.export_openapi
npm run generate:types --prefix frontend
```

**最新阶段验收（P7）**：完整后端 **1674 passed / 1 skipped**；最终定向 **128 passed**；P7 浏览器 **4 passed / 0 flaky**；当前 OpenAPI 为 **71 paths / 396 schemas**（V1 paths / schema 子集逐项一致）；科研源 **27,843 文件**的 path / size / mtime_ns / SHA-256 与锁定清单一致。以上为各阶段真实单次运行结果，**不将不同轮次计数相加**。

> 实时 AI 相关验收需要配置真实 provider 密钥并会产生**真实网络请求**；隔离测试套件不使用真实调用。历史 Phase 12 验收记录的 1356 项后端 / 217 项前端通过属于该阶段结果，当前代码状态需重新验证。

---

## 8. 科学边界与已知缺口

### 8.1 状态标记

| 标记 | 含义 |
| --- | --- |
| `IMPLEMENTED` | 软件入口已交付；具体科学能力仍需分别查看 |
| `MISSING` | 对应数据或证据缺失，**不能当作数值零** |
| `UNKNOWN` | 尚无足够记录确定，**不能自动理解为否** |
| `UNSUPPORTED` | 当前实验或配置不支持所选能力 |
| `PARTIAL` | 部分结果或验证可用，需阅读具体原因 |
| `FROZEN_VERIFIED` | 按记录范围已冻结验收 |
| `VERIFIED_NOT_FROZEN` | 已验证但未冻结 |
| `DIAGNOSTIC_RERUN` | 数据来源属于诊断性重运行，保留独立来源说明 |
| `SCHEMATIC` | 机制示意，用于解释概念 |

验证状态、数据来源与软件交付状态是**相互独立**的信息。例如 Case 8 的累计分配保留 `DIAGNOSTIC_RERUN` 来源，Cylinder 保留 `VERIFIED_NOT_FROZEN` 状态；软件功能冻结不会自动提升其科学验证等级。

### 8.2 明确保留的科学缺口

1. Cylinder 完整轨迹累计二维 `Pi_at` 分配 —— MISSING。
2. Near-1D 五个 epsilon 的权威原始扫描数据 —— MISSING。
3. Spectrum 的序列化 Jacobian / Fourier 矩阵 —— MISSING。
4. 已保存的线性 / RK3 模态幅值历史 —— MISSING（已记录的增长率与 CFD 投影幅值仍作为独立可用观测）。

此外：全离散熵残差应作为**数值诊断**理解，不能表述为精确的全离散熵恒等式；Near-1D 机制示意不能替代缺失的原始扫描；跨流动对比为描述性，不构成统一排名。

科学结果的可信度依赖来源一致：受校验的依赖内容发生漂移时，相关数值结果会拒绝加载；HTTP 缓存标识（ETag）**不构成**科学来源证明。

---

## 9. 进一步阅读

- [项目说明.md](项目说明.md) — 面向使用者的中文使用指南
- [项目范围](docs/00_PROJECT_SCOPE.md) · [用户流程与信息架构](docs/03_USER_FLOW_AND_IA.md)
- [系统架构](docs/04_SYSTEM_ARCHITECTURE.md) · [数据模型](docs/05_DATA_SCHEMA.md) · [API 契约](docs/06_API_CONTRACT.md)
- V2 总体技术方案：[ShockPath_V2_总体技术方案.md](ShockPath_V2_总体技术方案.md) · [改造实施计划](ShockPath_V2_改造实施计划.md)
- V2 设计文档：[`docs/v2/`](docs/v2/)（能力审计、契约、求解器绑定、科学结果定义、AI 上下文、报告与对比扫描契约及各阶段验收）
- V1 交接与验收：[`docs/handoffs/phase12/`](docs/handoffs/phase12/)
- 数据资产清单：[data/01_DATA_ASSET_INVENTORY.md](data/01_DATA_ASSET_INVENTORY.md)

判断当前功能时，应结合实际代码、运行时能力与最终验收记录；早期方案文档包含分阶段计划，不作为当前实现结论。

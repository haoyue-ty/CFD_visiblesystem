# ShockPath V1 → V2 改造实施计划

> 编制日期：2026-10-02（Asia/Shanghai）  
> 项目目录：`D:\code_project\CFD_visiblesystem`  
> 需求依据：[ShockPath_V2_总体技术方案.md](ShockPath_V2_总体技术方案.md)  
> 状态：V2-P0、P1、P2、P3、P4、P5、P6 已于 2026-10-03 完成，M1/M2/M3/M4/M5/M6 通过；P7 已于 2026-10-04 完成，M7 通过；同条件对比与四组合真实串行扫描、预算/取消/恢复已交付，epsilon/新 Case 保持未开放。实际记录见 [P7 验收](docs/v2/17_P7_ACCEPTANCE.md)。P2 已通过独立真实 CFD、重复 benchmark 与正式 D_u 对照；P3 已开放网页提交、串行调度与进度/取消；P4 已交付完整科学结果、真实多帧、原生累计 face 与新运行 Evidence；P6 已交付十二节自包含 HTML，并通过三入口真实闭环及无密钥核心链路。实际记录见 [P0 验收](docs/v2/05_ACCEPTANCE.md)、[P1 验收](docs/v2/06_P1_ACCEPTANCE.md)、[P2 验收](docs/v2/07_P2_ACCEPTANCE.md)、[P3 验收](docs/v2/09_P3_ACCEPTANCE.md)、[P4 验收](docs/v2/11_P4_ACCEPTANCE.md)、[P5 验收](docs/v2/13_P5_ACCEPTANCE.md)、[P6 验收](docs/v2/15_P6_ACCEPTANCE.md)。

## 1. 改造目标与实施策略

在现有 Vue 3 + TypeScript、Flask + Python 项目上增量升级，保留 V1 回放、Explore、Lab 和 Evidence。首期完成 Case 8 的完整链路：

```text
模板 / 专业参数 / 自然语言
            ↓
同一份经过后端验证的实验配置
            ↓
用户确认 → 独立 Run → 真实 Case 8 求解
            ↓
确定性后处理 → 流场 / 熵预算 / 宏观指标
            ↓
AI 解释与问答 → HTML 实验报告
```

实施采用“每阶段交付一个能验证的纵向切片”。优先顺序为：

**V2-P0 能力核查与契约准备 → P1 实验创建 → P2 真求解 → P3 运行工作台 → P4 科学结果 → P5 AI 分析 → P6 报告 → P7 对比与扫描。**

P0 是对总体方案的必要补充。P1 保留自然语言草稿能力，因此 AI 客户端的最小实现提前到 P1；完整结果解释与科研助手仍在 P5。

编制计划时的工作范围是规划和生成文档，没有执行 CFD、修改产品代码、创建开发分支或更改科学源。随后用户明确要求执行 P0，已在 `codex/shockpath-v2` 完成能力审计、契约基础扩展、runtime 隔离准备与回归；未执行 CFD、未更改科学源。总体方案中的其他开发目标仍按阶段推进。

## 2. 已核查的现状

### 2.1 软件基础

| 已有模块 | 实际位置 | V2 处理方式 |
| --- | --- | --- |
| Flask 应用与依赖组装 | `backend/core/app.py` | 保留，在应用工厂中注册 V2 服务 |
| 环境变量配置 | `backend/core/settings.py`、`.env.example` | 增加 runtime、worker、AI 配置；当前不会自动读取 `.env` |
| API 注册与 OpenAPI 导出 | `backend/api/catalog.py`、`backend/schemas/openapi.py`、`scripts/export_openapi.py` | 补充请求体、响应状态码和流式响应契约 |
| V1 实验与科学模型 | `backend/models/experiments.py`、`backend/models/core.py`、`backend/models/results.py` | 保留 V1 wire format，新增 V2 输入与运行模型 |
| Case 8 回放适配与语义 | `backend/adapters/case8.py`、`backend/registry/case8_*.py` | 继续只读加载历史数据，不改造成运行器 |
| Evidence 与来源核查 | `backend/services/evidence.py`、`backend/registry/evidence_registry.py` | 复用科学语义，为新 Run 增加独立来源登记 |
| 路由、导航和首页 | `frontend/src/router.ts`、`frontend/src/App.vue`、`frontend/src/pages/HomePage.vue` | 增加 V2 页面和入口，保留旧 URL |
| 前端 API 与数据模型 | `frontend/src/services/api.ts`、`frontend/src/data/` | 增加 V2 typed service，复用展示模型 |
| Canvas / ECharts 图表 | `frontend/src/scientific/` | 复用 SnapshotViewer、EntropyChart、MetricsPanel 等 |
| 合约与浏览器验收 | `tests/`、`scripts/verification/` | 按阶段增加 V2 验收，继续回归 V1 |

目前应用核心链路是读取记录好的科学资产，没有发现已接入网页的实时 Solver Adapter、Run Manager 或 AI 模块。已有 `ExperimentConfig` 是 V1 的记录配置描述，包含 protocol、verification 和 evidence，并不是总体方案所需的用户运行输入。

Phase12 交接文档记录了历史验收结果：后端 1356 项通过、前端合计 217 项通过。这是历史记录，本次没有重跑测试，不能作为当前工作区的实时验收结论。

本次检查时，当前分支为 `codex/github-upload`，HEAD 为 `d4abbac4c7cd479ad2e927d5e1902a48df7e26b8`；本地 `FUNCTIONAL_V1_FREEZE` 标签解析为 `21a9add240192a3f6b1c291c80f9c34e60d05b9d`。它们与 Phase12 文档中的旧提交引用不同，P0 应核实差异和继承关系，不能直接使用旧交接 SHA 回退当前项目。

### 2.2 求解源码的只读核查

已定位以下候选依赖，均属于只读科学源：

| 路径（相对 `D:\Paper\passage6`） | 核查结果 |
| --- | --- |
| `solver/fluxes/cross_mode_ec_unified_v1.py` | 包含目标方法和 `q_aa` / `q_at` 入参 |
| `solver/cases/flagship_cross_modal_case8.py` | `initial_setup(n, ny, gas)` 支持网格传入，但 Mach、初始扰动、默认 CFL/T 等由常量定义 |
| `jcp_extension_v1/J2_entropy_diagnostics/J2B0_case8_integration/code/case8_j2_driver.py` | 提供带观测器的 source-equivalent SSP-RK3 步进和微运行入口 |
| `jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/analysis/case8_j2b_formal.py` | 正式驱动锁定 A/B/C/D 配置；默认 CLI 工作目录属于科研目录，不能原样调用 |
| `jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json` | 提供正式网格、时间、步进、边界条件和诊断定义 |

关键结论：现有数值方法可以复用，但正式科研驱动不是任意参数 CLI。需要在软件项目中新增参数化执行包装层，复用原 flux、有限体积 RHS、时间推进和诊断算法；不能仅修改网页字段就声称参数已经生效。

### 2.3 首期参数开放策略

| 参数 | 当前证据 | 首期策略 |
| --- | --- | --- |
| Case | 已定位 Case 8 链路 | 仅开放 Case 8 Live Run |
| `q_aa`、`q_at` | 底层 flux 接收入参，正式驱动使用冻结配置表 | 在 V2 包装层显式传入，完成生效测试后开放 |
| `Nx`、`Ny` | 初始化支持入参 | 核查诊断、坐标、边界和 CFL 对动态网格的支持后开放 |
| CFL、T | 正式协议有固定值，原初始化协议含常量 | V2 包装层实现传参和步长策略；论文模式严格沿用正式协议 |
| Mach | 当前 Case 8 初始化固定为 6 | 首期固定为 6；参数化初始化验证后再开放 |
| `epsilon` | 未在已核查 Case 8 初始化发现对应通用参数 | 暂不开放；先明确是前沿扰动还是切向扰动，禁止套用其他实验的 epsilon |
| Gate | 目标 flux 接口未见 gate 参数 | 首期只显示已核实的方法路径；不得把 V1 Gate 回放选项当作 Live 能力 |
| Reconstruction | 正式协议为一阶 | 首期固定一阶，其他选项列为未支持 |
| Snapshot interval | 需要 V2 驱动实现 | 完成落盘和索引支持后开放，设置数量/容量限制 |

总体方案中的 epsilon=0.0001 是示例输入，不构成已核实的 Case 8 正式协议。Mach/epsilon/Gate/其他重构若被确定为首版必备，必须增加专项求解能力任务和工期，不能绕过验证。

## 3. 迁移边界与关键决策

### 3.1 保留 V1，建立 V2 版本记录

- 保留 `/api/v1` 既有字段、旧结果 identity 和历史科学来源。
- 保留 `/lab`、`/lab/experiments/:experiment_id`、`/explore`、`/cross-flow`、`/evidence` 深链接。
- V2 使用 `/api/v2`、新运行 identity 和独立 runtime 存储。
- 历史 freeze 文件与 docs 03–06 作为 V1 记录保留；新增 V2 架构、输入、运行和验收文档，不覆盖过去的冻结结论。
- V1 所有历史实验继续可回放；“首期仅支持 Case 8”仅限制新建 Live Run。
- 总体方案优先于旧交接中“下一步仅 UI 美化”的旧阶段安排；正式实施另行记录 V2 范围。

### 3.2 避免同名模型冲突

建议采用：

```text
V1 ExperimentConfig            已记录实验的科学配置描述，保持不变
V2 LiveExperimentConfig        三种入口的统一运行输入
V2 ExperimentConfigDraft       AI / 表单未确认草稿
V2 ValidatedExperiment         后端归一化配置、分类、差异和 config_hash
V2 RunRecord                   任务状态与生命周期
V2 ScientificRunResult         后处理后的科学结果
V2 ScientificAIContext         AI 可读取的结构化科学上下文
```

`LiveExperimentConfig` 是总体方案中 V2 ExperimentConfig 的实现名称。避免让两个 Pydantic 类导出同名 OpenAPI component；V1 前端生成类型保持可用。

核心输入仍按 `case_id / profile / physics / grid / time / method / discretization / output` 分组。提交元数据另存 `input_mode`、`template_id`、自然语言原文和解析版本，不把输入方式混入数值计算。

### 3.3 Profile、科学身份与运行状态分离

不要把 `RUNNING` 与 `LIVE_PAPER_PROFILE` 放进同一个 status 字段：

```text
status                  QUEUED / STARTING / RUNNING / POSTPROCESSING / COMPLETED / FAILED / CANCELLED
requested_profile       fast / paper / custom
classification          LIVE_FAST_RUN / LIVE_PAPER_PROFILE / PAPER_SCALE_CUSTOM / CUSTOM_RUN
verification            本次真实科学核查状态
data_origin             本次新运行的来源；不同于 V1 冻结生产数据
```

分类在后端进行，依据归一化的完整协议，不信任前端提交的“论文配置”标签。

| 条件 | 分类与 UI 标签 |
| --- | --- |
| 使用已登记 fast 模板且计算配置未改 | `LIVE_FAST_RUN`；普通配置 |
| 选择指定论文标准模板，完整数值协议匹配 | `LIVE_PAPER_PROFILE`；论文标准配置的新运行 |
| 从论文模板修改任何正式数值参数 | `PAPER_SCALE_CUSTOM`；论文模板·自定义参数，列出差异 |
| 从 fast 模板改参数或直接使用自定义协议 | `CUSTOM_RUN`；自定义实验 |

`PAPER_SCALE_CUSTOM` 保留总体方案的枚举，但修改网格后不能用“仍是论文尺度”误导用户，应展示实际网格、T 和差异。若用户希望从 D_u 切换为 B_u 标准实验，应明确选择 B_u 模板，而不是静默把参数修改重新命名为标准复现。

论文配置匹配不等于复现已经成功。只有本次对参考结果的核查完成，才可显示对应复现结论；仍不得把新运行提升为历史 `FROZEN_PRODUCTION`。

当前已核查标准参数：

| 模板 | q_aa | q_at | 论文网格 | CFL | T |
| --- | ---: | ---: | --- | ---: | ---: |
| A_u | 13.2 | 0 | 128×32 | 0.05 | 0.08 |
| B_u | 3.96 | 0 | 128×32 | 0.05 | 0.08 |
| C_u | 13.2 | 0.396 | 128×32 | 0.05 | 0.08 |
| D_u | 3.96 | 0.396 | 128×32 | 0.05 | 0.08 |

完整标准协议还包括 Mach=6、γ=1.4、初始条件、边界条件、一阶离散、SSP-RK3 和步长策略。不能仅比较上表就认定复现。正式 128×32 协议记录 1912 步；fast/custom 不得硬编码该步数或正式 dt。

### 3.4 Solver 依赖与文件写入

首选在受控子进程中只读导入经核查的源模块，执行入口和输出全部位于软件目录：

```text
backend/solver_runtime/worker.py
    → 经哈希登记的源 flux / RHS / SSP-RK3 / 诊断
    → runtime/runs/<run_id>/
```

- 启动前核实实际导入路径和依赖哈希，防止同名 solver 副本被错误导入。
- 科学目录存在多个归档/交付副本；P0 选定唯一依赖清单，不按搜索先后选择。
- worker 设置工作目录、日志、缓存和临时目录到 runtime；Python 使用 `-B` 或 `PYTHONDONTWRITEBYTECODE=1`，防止在科研源生成 `__pycache__`。
- 不直接启动原 formal CLI，不调用其默认科研输出目录。
- 参数化和观测封装放在软件项目，保持源算法只读；禁止通过修改源模块全局常量实现输入。
- 若依赖包无法在只读源上运行，可在软件目录建立带来源清单和 SHA-256 的受控镜像；它复用同一算法实现，不维护第二套数值方法。
- Run 输出路径由服务端产生，禁止由用户/AI 指定输出目录、命令或任意脚本。

## 4. 建议代码与文档布局

以下是实施时的建议布局；P0 仅创建隔离基础、审计工具和 `docs/v2` 文档，其余模块留给后续阶段，实际交付见 P0 验收记录：

```text
backend/
  models/v2/
    experiment.py           统一输入、校验结果、能力声明
    run.py                  RunRecord、事件、索引
    result.py               ScientificRunResult
    ai.py                   草稿、解读、对话上下文
  registry/v2/
    cases.py                Live Case Registry
    capabilities.py         输入/输出能力和已验证取值
    templates.py            fast / paper 标准模板
  api/v2/
    experiments.py
    runs.py
    ai.py
    reports.py
  services/v2/
    experiments.py
    results.py
    evidence.py
  solver_runtime/
    solver_adapter.py
    case8_adapter.py
    worker.py
    run_manager.py
    run_store.py
    progress.py
  postprocess/
    case8.py
    fields.py
    entropy.py
    metrics.py
  ai/
    client.py
    config_parser.py
    context_builder.py
    interpreter.py
    assistant.py
    report.py
    prompts.py

frontend/src/
  pages/
    ExperimentBuilderPage.vue
    RunWorkspacePage.vue
    RunListPage.vue
    RunReportPage.vue
  views/experiments/         模板、专业参数、AI 草稿、配置摘要
  views/runs/               运行状态、结果、AI、时间轴
  data/v2/                  类型化请求与科学展示模型转换
  scientific/               继续复用已有图表

runtime/
  runs/<run_id>/
    config.json
    effective_solver_config.json
    status.json
    provenance.json
    events.jsonl
    solver.log
    diagnostics/
    snapshots/
    derived/
    ai/
    report/

docs/v2/
  01_CAPABILITY_AUDIT.md
  02_CONTRACTS.md
  03_SOLVER_BINDING.md
  04_BENCHMARK.md
  05_ACCEPTANCE.md
```

目录可随实际实现精简。目标是责任边界清楚，不要求提前创建大量空文件。`runtime/` 应加入 `.gitignore`，测试数据和小型规范样例另存测试目录。

## 5. 分阶段任务与验收

### V2-P0：核实基线、Solver 能力和 API 扩展点

**目标：明确“当前能做什么、需要补什么”，让后续表单与真实执行一致。**

任务：

- [x] 记录当前 HEAD、工作区差异与 V1 标签关系，保留 V1 可回退基线；实施分支 `codex/shockpath-v2`，新增 `V1_PRE_V2_P0_20261002` 回退标签。
- [x] 运行现有项目基线测试与构建，保存实际结果；首次测试受到提前编辑干扰的归因、历史快照重测及最终完整回归均已记录。
- [x] 输出 Case 8 源模块、依赖、协议和诊断定义的清单及哈希（37 文件）。
- [x] 明确 `epsilon` 歧义与两种实际扰动物理定义，Gate 不支持、一阶 Reconstruction 固定；未知参数不开放。
- [x] 设计 Case Registry 和 Parameter Capability Registry，同时区分“能验证配置”与“已能启动求解”。
- [x] 确定配置归一化、profile 分类、Run 状态、资源缺失和错误 DTO。
- [x] 设计并实现 JSON POST、202、SSE、HTML 响应的最小 catalog/OpenAPI 扩展，未注册生产 V2 路由。
- [x] 建立科学目录写入隔离检查及软件 runtime 路径策略；完整科研根 27,843 文件前后核查通过。

**特别需要处理的现有接口限制：** `OperationCatalog.bind()` 当前只从 path/query 构造输入，并统一验证/返回 JSON；OpenAPI 导出默认成功响应为 200、输入为 parameters。建议以兼容默认值扩展 Operation 元数据和绑定逻辑，保留所有 V1 行为，再支持 V2 `requestBody`、202、`text/event-stream` 等。流式响应不能被当成普通 Pydantic JSON 返回；实际路由仍需纳入 catalog 一致性检查。

交付：能力核查文档、V2 契约初稿、依赖清单、当前基线报告。

**通过条件：** 每个拟开放参数都有来源或明确待实现项；原 V1 合约保持兼容；没有求解器入口会默认写入科研目录。

### V2-P1：统一实验创建，保留三种入口

**目标：输入能形成真实、可执行范围内的配置；本阶段可以尚不启动 CFD。**

建议内部顺序：

1. **P1a：模型、能力、模板与验证 API。**
2. **P1b：模板/专业表单、配置摘要与前后端联通。**
3. **P1c：最小 DeepSeek 客户端、自然语言草稿与确认流程。**

任务：

- [x] 实现 `LiveExperimentConfig` 和后端验证；拒绝未知字段、非有限数、非整数网格、越界值与未支持枚举。
- [x] 从经核查协议登记 A_u/B_u/C_u/D_u；fast 候选为 64×16、CFL=0.05、T=0.04，标“待 benchmark”。
- [x] 完成 `/experiments/new`；专业页只提供 capability 允许的字段。
- [x] 返回 normalized config、classification、warnings、unsupported fields、差异和 config_hash。
- [x] 实现自然语言结构化草稿；含糊或未支持要求返回待澄清字段，不静默替换（模拟输出与异常链路已验收）。
- [x] 三入口都使用相同后端验证和配置摘要（真实 provider 连通另行验收）。
- [x] 确认配置时再次后端验证；公共验证函数供 P3 Run 创建复用。P1 未建立 Run API，Run 创建时的实际二次校验留到 P3 验收。
- [x] 求解未接通时明确显示“运行能力尚未开放”，不提供伪进度；启动按钮始终禁用。
- [x] 使用用户提供的后端密钥完成 DeepSeek 连通与真实草稿验收；6 个真实 API 场景与 1 个真实浏览器端到端场景通过。

DeepSeek 密钥只从后端环境变量读取；模型 ID 与 endpoint 在实施时核实，本文不指定未验证的模型名称。无密钥、超时或非法 AI 输出时，模板/专业创建仍可用，自然语言入口显示明确失败。

交付：三入口 → 同一配置 → 验证 → 用户确认的可演示流程。

**通过条件：** 等价的三种输入得到相同 normalized config；论文参数改动被准确标记；AI 草稿没有触发任何 CFD；未支持字段不会假装有效。

### V2-P2：真实 Case 8 求解接通

**目标：不用网页长流程，也能通过 V2 adapter 完成两次独立真实 CFD。**

任务：

- [x] 实现 `Case8SolverAdapter.validate_config / prepare_run / execute / postprocess` 的最小链路。
- [x] 软件包装层显式构建初始条件、网格、RHS、flux、时间推进和 observer；记录有效 Solver 配置。
- [x] 复用源实现，保留 SSP-RK3 stage guard、诊断范围和正确时间权重；四系数 smoke 与原无 observer 步进逐位一致。
- [x] 实现 fast/custom 步长规则；paper 模式沿用完整正式协议；失败不自动降低 CFL 或修改配置。
- [x] 每次运行落盘初始状态、终态、真实 history、日志、依赖 hash 和输出 hash。
- [x] 增加四系数短小真实 smoke；fast D_u 三次完整重复 benchmark 均成功，最终中位数 26.196s，记录同机回归负载与 RSS/输出大小。
- [x] 正式 D_u 新 Run 完成 1912 步；终态与参考 BITWISE，比较的终态宏观指标及 1912 行全域熵 stage/history 列误差均 0，规则与参考 hash 记录完整。

最低实验：

| 实验 | q_aa | q_at | 验证目的 |
| --- | ---: | ---: | --- |
| Run A | 3.96 | 0 | 独立真实运行，验证 cross-mode at 零通道行为 |
| Run B | 3.96 | 0.396 | 独立真实运行，验证参数进入目标 flux |

两次使用同一初始化和数值协议；差异来自指定参数。检查 effective config 和实际调用，不只比较输入 JSON。分别保存 run_id、起止时间和输出；同配置重新运行也必须新建 Run，不直接读取 V1 冻结结果充当求解结果。

注意：`q_aa=3.96, q_at=0` 对应 B_u 参数，不能误称 A_u；Run A/Run B 只是本阶段测试名。允许某些宏观指标不随参数单调变化，不以“看起来更好”作为正确性验收。

交付：真实适配器、运行样例、有效配置映射、基准报告。

**通过条件：** 两次真实计算与参数映射有证据；结果有限且满足明确的数值有效性检查；零通道遵守源诊断容差；科研源路径/大小/mtime/hash 与前置记录一致。

**实际验收：M2 通过。** [P2 验收](docs/v2/07_P2_ACCEPTANCE.md)、[benchmark](docs/v2/08_P2_BENCHMARK.md)、[原始运行摘要](docs/v2/p2_solver_acceptance.json)。fast 已登记 PASSED，数值协议未改的模板分类为 LIVE_FAST_RUN；网页 execution_available 仍为 false。完整后端 1539 passed / 1 skipped，最终 V2/contract 定向 249 passed / 1 skipped，完整浏览器 225 passed，最新 builder 5 passed；首轮默认双 worker 的 15 项浏览器超时与单 worker 重跑结果分别保留。完整科研根 27,843 文件前后完全一致。P4 的累计空间分配与 V2 结果 DTO 不在本阶段交付范围。

### V2-P3：任务管理、进度与运行工作台

**目标：浏览器提交后立即获得 run_id，后台运行可观察、可取消、可恢复记录。**

任务：

- [x] 实现 RunStore、单 worker 调度、独立 subprocess，`MAX_CONCURRENT_RUNS=1`。
- [x] `POST /runs` 成功返回 202 和 QUEUED；仅落盘、入队，不等待数值求解完成。
- [x] 实现状态转换、持久队列索引、原子状态文件写入，避免并发/刷新时读到半个 JSON。
- [x] 保存 PID/worker 身份和 heartbeat；服务重启识别中断任务，显式记录 `WORKER_INTERRUPTED`，不伪装完成或自动续算。
- [x] 防止重复 worker 启动；`create_app()` 和 OpenAPI 导出不启动求解进程，开发 reloader 不重复消费队列。
- [x] 增加请求幂等机制，防止重复点击/网络重试新建多个高成本任务；主动再次运行则生成新 Run。
- [x] 设置最大队列、网格、运行时长、快照数量和输出容量；依据 benchmark 给出上限。
- [x] SSE 提供事件序号、心跳与断线重连；状态查询作为可用回退。
- [x] 实现 `/workspace` 列表与 `/runs/:runId` 运行视图、最终 Density。
- [x] 实现排队取消、运行中停止请求和超时后的进程树终止；Windows 下不遗留子进程。

进度读取真实 completed step/physical time。可按 `physical_time / final_time` 展示求解阶段进度，同时区分后处理阶段；不能用定时器生成虚假百分比。ETA 只有通过基准校准后才显示。

状态约束：

```text
QUEUED → STARTING → RUNNING → POSTPROCESSING → COMPLETED
任一非终态 → FAILED
成功接收并完成取消 → CANCELLED
```

取消处理中可用独立 `cancel_requested` 字段表示；最终状态只有一个，取消/完成竞态由 Run Manager 统一处理。只有后处理结果通过校验并原子提交后才进入 COMPLETED。

交付：完整网页真运行、列表、日志/进度、取消与重启处理。

**通过条件：** 第二个任务排队、不并发求解；刷新/断线后恢复状态；取消能停止实际计算；worker 崩溃得到失败记录；持续 SSE 不使普通 API 无法响应。Waitress 的线程配置须验证能同时服务事件连接和普通请求。

### V2-P4：科学结果与 V2 Evidence

**目标：新运行结果复用既有可视化，但具有独立科学身份和可靠定义。**

任务：

- [x] 实现 `ScientificRunResult`，包含 identity、config、runtime、fields、entropy、metrics、allocation、limitations、provenance。
- [x] 转换真实数组为前端展示模型，保留 shape、axes、unit、time 和坐标；64×16 / 128×32 真运行逐帧对照通过。
- [x] 由保守变量和气体模型确定性计算 ρ、p、速度、Mach；六种字段与锁定源 Euler 对照误差为 0，保存派生定义与输入 hash。
- [x] 接入真实 E_bg/E_aa/E_at history；记录 stage/RK 权重、face measure、空间范围和累计规则，重新核对所有真实接受步。
- [x] Pi_at 等 face field 保留 native x/y-face 几何，复用 FaceAllocationView；无 face-to-cell reshape。
- [x] 分别标记瞬时 Pi、全轨迹累计空间分配、累计标量 E；新 worker 保存 stage-weighted cumulative faces，积分与 scalar E 通过容差核对。
- [x] Shock width、Front RMS、HF 复用经核查 detector，记录单位、窗口、归一化、有效行计数和适用条件；缺失前沿的 HF 不使用源补零值冒充可用结果。
- [x] 多帧来自真实 snapshot；支持上一帧/下一帧/播放，URL 恢复变量/帧/区域，不插值伪造中间帧。
- [x] 缺失结果用 `null + availability + reason`，与真实数值 0 区分；旧 P3 累计 face 缺失及 q_at=0 的真实零均已验收。
- [x] 创建 V2 run evidence 与 `/runs/:runId/evidence`，保存 config、effective config、方法/源码/后处理版本、依赖及输出哈希。
- [x] 将当前变量、snapshot、区域选择同步为结构化 view context；区域统计由真实 cell centers 确定性计算，供 P5 使用。

若某诊断仍不可用，相关控件显示明确限制，不用 V1 D_u 的值补齐。输入已确认但输出不支持，也应分别报告 capability。

交付：`/runs/:runId` 完整结果工作台和可追溯的 V2 Evidence。

**通过条件：** 页面数值可逐项对应本 Run 文件；与直接后处理对照一致；fast/custom 网格正确；源/方法/结果哈希相互区分；新 Run 不继承历史冻结状态；可视化、报告、AI 使用同一份结果定义。

### V2-P5：AI 自动解读与上下文科研助手

**目标：AI 解释真实科学上下文，失败时不影响 CFD 结果。**

任务：

- [x] 扩展 P1 客户端：超时、有限重试、错误分类、调用记录和费用/长度限制。
- [x] `ScientificAIContext` 只引用可用结果和明确的证据 ID，不直接提交 NPZ/NPY 或无关服务器文件。
- [x] 完成自动 interpretation JSON：summary、key_findings、observations、limitations、suggested_questions。
- [x] 新 Run 完成后按 `result_hash + prompt_version + model` 缓存解读，刷新不重复触发相同调用。
- [x] 助手绑定当前 Run、变量、快照、区域统计、结果和 limitations；区域数值由后处理确定性计算。
- [x] 将 AI 数值性结论绑定 evidence refs，区分事实、解释和局限；未支持数据明确回答不可用。
- [x] 将用户消息与数据中的文本当作内容，不允许其改变系统边界、读取密钥或直接启动求解。
- [x] AI 不可用时提供重试入口，已有结果、图表与 Evidence 继续使用；确定性 HTML 报告留 P6，尚未交付。

交付：结果自动解读与同页科研助手。

**通过条件：** 正常、超时、无密钥、错误 JSON、缺失指标、无效证据和诱导夸大结论均有验证；不会推测缺失值或声称普适稳定/最优；不把更大的 E_at 直接解释为更好方法。

### V2-P6：自动 HTML 实验报告与首版验收

**目标：固定结构报告可复查、可保存，完整 Case 8 闭环达到首版交付标准。**

- [x] 实现 `/runs/:runId/report`，采用总体方案 12 节固定结构。
- [x] 程序生成配置表、运行信息、数字、图表、局限和 provenance；AI 只提供经过 P5 校验的解释段落，报告不新增 provider 调用。
- [x] 终态密度/压力/Mach 与全接受步熵图绑定 snapshot/time/变量/单位/源 hash；报告记录 result/context hash、report/renderer 版本和 AI prompt/model/content hash。
- [x] 用户/AI 文本转义，内嵌 JSON 转义 HTML 解析符；CSP 与空 sandbox 限制执行，禁止直接插入 AI HTML。
- [x] 真正无密钥后端完成模板确认、真实 CFD、结果和完整确定性报告；不存在或损坏的解读缓存明确不可用。
- [x] 保存自包含 HTML；三份实际下载文件 hash 一致，断网本地重开十二节/四 SVG，资源请求为 0，手机无横向溢出。
- [x] 同步 README、启动说明、环境变量示例、演示步骤与已知限制，新增报告契约/验收和 live/finalize 脚本。
- [x] 完成最终后端 1645 passed / 1 skipped、既有浏览器 225 passed、定向 88 passed；三个输入入口各独立真实求解/解读/问答/报告通过；27,843 科学源文件不变。

交付：首版 V2、验收报告、可下载 HTML 报告和演示脚本。

**通过条件：** 同一 Run 在结果页、AI context 和报告中的配置/数字一致；三个入口均可完成“确认 → 真求解 → 结果 → 解读/问答 → 报告”；AI 服务关闭时核心链路仍成立。

### V2-P7：同条件对比与参数扫描（首版后）

- [x] Run A/B 比较核查 Case、完整初始条件、网格/域、T/CFL/推进、离散/边界、方法/源与 detector；不一致明确非同条件，并禁止指标差值。
- [x] 六变量、共同真实 snapshot time、联合色标、计算域几何比例、终态指标定义与物理时间熵曲线统一，列出协议差异；无共同时间不插值。
- [x] 完成已登记 q_aa/q_at 四组合真实独立扫描，复用串行队列；总任务/墙钟预算、逐项验证/确认、幂等/重启恢复、真实进度与活动取消均通过。
- [x] 检查 epsilon 扫描前提：物理语义与 Solver 生效验证尚未完成，因此保持未开放，未假装交付 epsilon 扫描。
- [x] 更广 Case 保持单独立项边界；本期没有新增 Case，后续须复用 adapter 接口和能力登记验收。

交付与实际验收：新增 `/workspace/compare`、`/workspace/sweeps`、`/sweeps/:sweepId` 和六条 P7 API；M7 于 2026-10-04 通过。完整后端 1674 passed / 1 skipped，最终定向 128 passed，P7 最终浏览器 4 passed，真实四组合各 478 步及活动取消/预算耗尽通过。既有浏览器首次 224 passed / 1 服务共享导致的 failed，独立相关复测 9 passed；失败归因和原记录保留。27,843 科学源文件不变。见 [P7 契约](docs/v2/16_P7_COMPARISON_SWEEPS.md)、[P7 验收](docs/v2/17_P7_ACCEPTANCE.md)、[最终核查](docs/v2/p7_final_checks.json)。

P7 不成为 P1–P6 的交付前置条件。不得据单个 Case 或不可比协议建立通用性能排行榜。

## 6. API 与页面安排

### 6.1 API 分阶段表

| 阶段 | 接口 | 主要用途 |
| --- | --- | --- |
| P1 | `GET /api/v2/cases` | Live Case / 输入输出 capability 与模板 |
| P1 | `POST /api/v2/experiments/validate` | 校验、归一化、分类、差异 |
| P1 | `POST /api/v2/experiments/parse-natural-language` | AI 草稿，禁止入队 |
| P3 | `POST /api/v2/runs` | 二次验证后创建，成功 202 |
| P3 | `GET /api/v2/runs` | 分页/筛选列表，为 workspace 提供数据 |
| P3 | `GET /api/v2/runs/{run_id}` | 持久状态与有效配置摘要 |
| P3 | `GET /api/v2/runs/{run_id}/events` | SSE 心跳、事件与进度 |
| P3 | `POST /api/v2/runs/{run_id}/cancel` | 幂等取消请求 |
| P3–P4 | `GET /api/v2/runs/{run_id}/history` | 运行历史与科学标量 |
| P3–P4 | `GET /api/v2/runs/{run_id}/snapshots` | 真快照索引 |
| P3–P4 | `GET /api/v2/runs/{run_id}/snapshot/{snapshot_id}` | 元数据与受控科学字段 |
| P4 | `GET /api/v2/runs/{run_id}/result` | 结构化结果，未完成时给明确状态 |
| P4 | `GET /api/v2/runs/{run_id}/evidence` | 新运行来源/定义/验证记录 |
| P5 | `POST /api/v2/ai/runs/{run_id}/interpret` | 幂等/缓存解读 |
| P5 | `POST /api/v2/ai/chat` | 明确 run_id 与 view context 的问答 |
| P6 | `POST /api/v2/reports/{run_id}` | 生成或复用版本化报告 |
| P6 | `GET /api/v2/reports/{run_id}` | 报告状态与元数据 |
| P6 | `GET /api/v2/reports/{run_id}/html` | HTML 导出，按受控 Run identity 获取 |
| P7 | `POST /api/v2/comparisons` | 核查同条件、共同真实帧、联合色标、终态指标与差异 |
| P7 | `POST /api/v2/sweeps/preview` | 逐项验证系数扫描和任务/时间预算，不入队 |
| P7 | `POST /api/v2/sweeps` | 重新校验已确认扫描并持久保存，成功 202 |
| P7 | `GET /api/v2/sweeps` | 扫描分页列表 |
| P7 | `GET /api/v2/sweeps/{sweep_id}` | 持久状态、子 Run、真实进度与预算 |
| P7 | `POST /api/v2/sweeps/{sweep_id}/cancel` | 幂等取消，停止活动子 Run 并跳过未提交项 |

`GET /cases`、Run 列表、新运行 Evidence 和 HTML 导出是对总体方案的补充，分别补齐能力发现、工作台列表、来源追踪和报告保存。

明确非法输入、未支持组合、未知 Run、队列满、求解失败、未完成结果、AI 不可用的错误格式与 HTTP 状态；错误不替换成空科学结果。API 只接受受控 identity，不暴露任意磁盘浏览或日志中的本地绝对路径。

### 6.2 页面与导航

| 页面 | 路由 | 完成阶段 |
| --- | --- | --- |
| 新建实验 | `/experiments/new` | P1 |
| 实验工作台列表 | `/workspace` | P3 |
| 运行/结果工作台 | `/runs/:runId` | P3 最小版，P4/P5 完整版 |
| 运行证据详情 | `/runs/:runId/evidence` | P4 |
| HTML 报告 | `/runs/:runId/report` | P6 |
| Run A/B 对比 | `/workspace/compare` | P7 |
| 系数扫描/列表 | `/workspace/sweeps` | P7 |
| 扫描详情 | `/sweeps/:sweepId` | P7 |

P1 先增加新建实验入口；P3 页面可用后逐步形成“首页 / 新建实验 / 实验工作台 / 引导探索 / 证据中心”的导航。Lab 和已有回放仍可通过首页/探索/证据入口进入，旧路由保持兼容。AI 助手放在结果工作台，不成为一级导航。

V1 回放与 V2 真运行始终显示独立的数据来源说明；页面不能因为使用 REAL API 就宣称发生了实时求解。

## 7. 验证策略

| 层次 | 核心验证 | 对应阶段 |
| --- | --- | --- |
| 配置 | 三入口等价、能力拒绝、默认值、标准协议差异、重复提交 | P1/P3 |
| Solver | 参数真实生效、独立两次计算、finite/物理有效性、零通道、参考对照 | P2 |
| 调度 | 单并发、排队、崩溃、重启、取消、重复 worker、资源上限 | P3 |
| SSE | 事件序号、断线重连、心跳、并行普通 API | P3 |
| 科学结果 | 单位/shape/time、RK 权重、face 几何、派生定义、缺失与零 | P4 |
| AI | JSON 校验、来源引用、缺失事实、上下文、失败独立性 | P1/P5 |
| 报告 | 数值一致、版本/哈希、AI 关闭、保存后资源可用 | P6 |
| 兼容性 | V1 URL、API/schema、Evidence、类型生成、已有浏览器流程 | 每个里程碑 |
| 源保护 | 路径/大小/mtime/SHA-256 前后比较，检查缓存和临时写入 | 首次真运行及最终验收 |

测试按变更选择：常规单元/契约测试使用软件目录下明确的测试夹具；真实 smoke run 使用小配置并单独记录；正式规模复现和完整 V1 浏览器回归在里程碑运行。测试夹具不得成为生产 fallback，不为每次文档修改启动 CFD。

当前实际可用的 V1 验证入口如下，实施时在 PowerShell 7 运行：

```powershell
./.venv/Scripts/python.exe -B -m pytest -q
npm run build --prefix frontend
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration contracts
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration public
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration scan
```

完整浏览器回归使用 `frontend/playwright.phase11.integration.config.ts`，源保护工作流使用既有 capture/source audit；实施前确认相应基线已经捕获。新增 V2 suite 后同步 runner 与审计规则，不删除旧检查来消除兼容性失败。

`npm run build` 已含 `vue-tsc --noEmit`，不要假设存在独立 typecheck 命令。V2 合约实现完成后同步 OpenAPI 和 TypeScript 生成；V1 类型及路径的兼容性单独检查。

Python 科研绘图如有需要，使用用户指定的 conda `analysis-env`；应用和测试继续沿用项目 `.venv`，不混用运行环境。

## 8. 工期与里程碑

以下为一名熟悉当前项目的开发者的有效工作日估算；不是完成日期承诺。未运行 benchmark，暂不承诺求解秒数。Mach/epsilon/Gate/其他重构的专项扩展、远程部署和新 Case 不包含在估算中。

| 阶段 | 估算 | 依赖 | 里程碑 |
| --- | --- | --- | --- |
| P0 | 2–3 天 | 当前项目、源代码可读取 | M0：基线与 capability 明确 |
| P1 | 3–5 天 | M0；AI 子项需服务可用 | M1：三入口生成可验证配置 |
| P2 | 5–8 天 | P1 输入契约 | M2：真实 Solver 连通与 fast benchmark |
| P3 | 4–6 天 | M2 | M3：网页提交、进度、取消、终态 |
| P4 | 5–8 天 | M3；真实诊断输出 | M4：科学结果和新运行证据完整 |
| P5 | 4–6 天 | M4；P1 AI 基础 | M5：解读、问答与降级完整 |
| P6 | 2–4 天 | M4/M5 | M6：首版 V2 验收与报告 |
| P7 | 3–5 天 | M6 | M7：同条件对比和小规模扫描 |

**P0–P6 合计约 25–40 个有效工作日，即约 5–8 周；P7 另计。** P0 核实源依赖复杂度、P2 完成 benchmark 后，应更新估算。

建议阶段交付顺序：

```text
可复用 V1 基线
    → 模板/专业配置与校验
    → AI 草稿与确认
    → 独立真实两次求解
    → 网页运行与取消
    → 真实科学结果及来源
    → AI 结果解释与问答
    → 报告与完整验收
```

AI 不可用时继续推进不依赖 AI 的任务，但 M1/M5 的 AI 子项仍标未完成，不能宣称三入口全部交付。

## 9. 风险与处理

| 风险 | 对进度/结果的影响 | 处理措施 |
| --- | --- | --- |
| 源驱动锁定协议，不能任意传参 | 表单参数不生效 | capability 驱动 UI，先实现/验证包装层再开放 |
| 同名源副本与方法哈希不匹配 | 执行了错误版本算法 | 明确导入路径和依赖哈希，漂移显式报错 |
| 普通配置仍较慢 | 演示阻塞 | 重复 benchmark，调整登记模板；不暗改正在运行的配置 |
| 正式驱动写科研目录 | 破坏只读原则 | 软件 worker、受控输出路径、禁写 bytecode、前后审计 |
| 工作区/冻结记录引用不一致 | 选错开发起点 | 检查真实 Git ancestry，保留当前提交和历史标签 |
| Waitress SSE 占用线程 | 状态/取消 API 无响应 | 验证线程容量、单 worker，状态轮询回退 |
| 熵预算权重或 face/cell 混淆 | 科学量错误 | 源 observer 复用，定义/积分一致性检查 |
| 新运行借用旧证据状态 | 错误宣称论文复现 | profile、verification、origin 分离，新证据 ID |
| AI 编造数值或强行排名 | 科学解释不可信 | 结构化 context、来源引用、边界验证与失败降级 |
| 参数扫描提前扩张 | 首期闭环延期 | P7 后置；首期无分布式/通用 PDE/任意几何 |

## 10. 立即执行的第一批开发任务

开发总顺序如下；P0/P1/P2 的第 1–7 项、P3 任务管理、P4 科学结果/Evidence、P5 AI 解读/科研助手及 P6 HTML 报告/首版验收已完成，实际记录见各阶段验收。首版 Case 8 闭环已经通过；P7 同条件对比与参数扫描也已完成，复用既有验证/运行/结果定义并保存了可复查产物；后续 epsilon、连续系数或新 Case 扩展须单独立项：

1. **核实当前 V1 基线和 Git 关系**，记录现有工作区差异、测试与构建结果。
2. **完成 `docs/v2/01_CAPABILITY_AUDIT.md`**，锁定真实 Case 8 源依赖、输入能力、输出能力及 epsilon 定义。
3. **完成 `docs/v2/02_CONTRACTS.md`**，确定 V2 模型、profile 分类、API 错误、JSON/SSE 契约。
4. **实现 V2 最小 API 扩展**，保持 V1 catalog/生成类型兼容，不启动 worker。
5. **实现统一配置、Case Registry、模板与 validate API**。
6. **实现模板/专业输入和配置摘要，再接 AI 草稿**；未接通执行时按钮显式不可用。
7. **进入 P2 完成两次真实运行和 benchmark**，再开放网页后台提交与 Live Workspace。

首版完成标志是：**同一个 Case 8 真实求解链路，三个输入入口，共享科学结果、证据、AI 上下文和报告，并且旧 V1 回放仍可正常使用。** 页面增加、AI 能聊天或报告能生成，都不能单独算作 V2 改造完成。

## 11. 实施进度记录

| 阶段 | 当前状态 | 完成日期 | 验收产物 |
| --- | --- | --- | --- |
| P0 | 已完成（通过；1 项 Windows symlink 权限 skip 已记录） | 2026-10-03 | [验收记录](docs/v2/05_ACCEPTANCE.md)、[基线/回归](docs/v2/04_BASELINE_REPORT.md)、[能力审计](docs/v2/01_CAPABILITY_AUDIT.md)、[契约](docs/v2/02_CONTRACTS.md)、[依赖锁](docs/v2/source_manifest.json) |
| P1 | 已完成；M1 通过（后端 1508 passed / 1 skipped、前端 225 passed、真实 AI API 6 场景与浏览器 1 项通过） | 2026-10-03 | [P1 验收](docs/v2/06_P1_ACCEPTANCE.md)、`/experiments/new`、三条 V2 API、后端与真实浏览器验收产物 |
| P2 | 已完成；M2 通过（独立 Run A/B、四系数 smoke、三次 fast benchmark、正式 D_u BITWISE、回归与源保护） | 2026-10-03 | [P2 验收](docs/v2/07_P2_ACCEPTANCE.md)、[benchmark](docs/v2/08_P2_BENCHMARK.md)、[真运行与比较记录](docs/v2/p2_solver_acceptance.json)、`scripts.run_case8` |
| P3 | 已完成；M3 通过（真实 HTTP/浏览器、串行/幂等/取消/重启、Density、完整回归与源保护） | 2026-10-03 | [P3 验收](docs/v2/09_P3_ACCEPTANCE.md)、[真实运行](docs/v2/p3_live_acceptance.json)、[最终核查](docs/v2/p3_final_checks.json)、`/workspace`、`/runs/:runId` |
| P4 | 已完成；M4 通过（完整后端 1600 passed / 1 skipped、既有浏览器 225 passed、真实 fast/custom 六帧字段/face/entropy、源码对照、区域/Evidence、源保护） | 2026-10-03 | [P4 定义](docs/v2/10_P4_SCIENTIFIC_RESULTS.md)、[P4 验收](docs/v2/11_P4_ACCEPTANCE.md)、[真实运行](docs/v2/p4_live_acceptance.json)、[当前浏览器](docs/v2/p4_browser_acceptance.json)、[最终核查](docs/v2/p4_final_checks.json) |
| P5 | 已完成；M5 通过（完整后端 1627 passed / 1 skipped、既有浏览器 225 passed、最终定向 76 passed、真实 AI 六场景、P5 浏览器三项、缓存/降级/证据/预算与源保护） | 2026-10-03 | [P5 上下文](docs/v2/12_P5_AI_CONTEXT.md)、[P5 验收](docs/v2/13_P5_ACCEPTANCE.md)、[真实 AI](docs/v2/p5_live_ai_acceptance.json)、[最终核查](docs/v2/p5_final_checks.json) |
| P6 | 已完成；M6 通过（完整后端 1645 passed / 1 skipped、既有浏览器 225 passed、定向 88 passed、三入口独立真实闭环、无密钥核心链路、离线报告与源保护） | 2026-10-03 | [P6 报告契约](docs/v2/14_P6_REPORTS.md)、[P6 验收](docs/v2/15_P6_ACCEPTANCE.md)、[真实网页](docs/v2/p6_live_acceptance.json)、[最终核查](docs/v2/p6_final_checks.json)、`/runs/:runId/report` |
| P7 | 已完成；M7 通过（同条件/异网格、统一真实时间/色标/指标、四组合真扫描、预算/取消/恢复、定向与兼容重测、源保护；epsilon/新 Case 保持能力边界） | 2026-10-04 | [P7 契约](docs/v2/16_P7_COMPARISON_SWEEPS.md)、[P7 验收](docs/v2/17_P7_ACCEPTANCE.md)、[真实网页](docs/v2/p7_live_acceptance.json)、[最终核查](docs/v2/p7_final_checks.json) |

每阶段记录实际提交、通过/失败的检查、benchmark、未完成能力和下一步，不用预估状态代替验收证据。

## 12. 核查依据

- [V2 总体技术方案](ShockPath_V2_总体技术方案.md)。
- [当前项目 README](README.md)、[依赖定义](pyproject.toml)、[前端脚本](frontend/package.json)。
- [Phase12 历史交接](docs/handoffs/phase12/PHASE12_FINAL_HANDOFF.md)。
- `backend/core/app.py`、`backend/core/settings.py`、`backend/api/catalog.py`、`backend/schemas/openapi.py`。
- `backend/models/experiments.py`、`backend/registry/case8_source_constants.py`、`backend/registry/case8_registry.py`、`backend/registry/case8_semantics.py`。
- `frontend/src/router.ts`、`frontend/src/App.vue`、`frontend/src/data/provider.ts`、`frontend/src/scientific/SnapshotViewer.vue`。
- 本文 2.2 所列科学源文件的只读检查。本次未运行源求解器，未完成性能 benchmark、完整依赖审计或数值复现验证。

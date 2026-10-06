# V2-P0 契约初稿与已实现的 transport 基础

日期：2026-10-02（Asia/Shanghai）。本文件冻结 P0 的边界和供 P1–P6 落地的设计；没有发布实验创建或运行 API。V1 `ExperimentConfig`、`/api/v1`、47 个路径、298 个 schema、已生成 TypeScript 均保持原样。

## 1. V2 模型边界（待 P1 实现）

`LiveExperimentConfig` 使用独立模型命名，strict+extra=forbid+allow_inf_nan=False。schema 版本 `2.0.0`，capability revision 单独记录，不继承 V1 frozen provenance。

| 分组 | 字段 / 规则 |
| --- | --- |
| case_id / profile | case8；profile=fast/paper/custom，仅用户请求偏好 |
| physics | mach、gamma、完整具名初始条件；首期均固定，拒绝 epsilon |
| grid | nx、ny 严格整数（拒绝 bool、小数及数字字符串）；domain 固定 |
| time | cfl、final_time、integrator=SSP_RK3、dt_strategy=INITIAL_STATE_FIXED_STEP；数值有限 |
| method | method_id=cross_mode_ec_unified_v1、q_aa、q_at；不提供 Gate |
| discretization | reconstruction=FIRST_ORDER；固定边界协议 |
| output | 已登记 snapshot schedule policy；自由 interval 等待 P2/P3 |

提交元数据独立：`input_mode(template/form/natural_language)`、`template_id`、`natural_language_text`、`parser_version`、`capability_revision`。用户/AI 不能提交输出路径、命令、Python 或 shell 内容作为执行选项。

`ExperimentConfigDraft` 含候选 config、unresolved_fields、unsupported_fields、warnings、parser_version；不能入队。`ValidatedExperiment` 含 normalized_config、requested_profile、classification、protocol_diff、warnings、config_hash、capability_revision、execution_available；可校验不等于可执行。

## 2. 归一化和分类

1. 拒绝未知字段、不合法 JSON、NaN/Inf、超出已登记能力的枚举/数值。缺少必需字段直接失败；模板缺省值只由 server registry 填充，AI 不猜默认值。
2. 统一正式字段名、数值类型、负零→零、浮点整数形式→同一规范浮点形式；网格从最初验证起就是 int。三入口共用同一后端归一化函数。
3. 把固定 γ、Mach、初始条件、domain、边界、重构、积分器、dt 策略和 output policy 补全到完整 normalized_config。不要仅比较网格/q 系数判断论文匹配。
4. `config_hash = SHA256(UTF8(JSON(normalized_config, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)))`。在 normalized_config 中包含 config schema/protocol revision；排除输入原文、入口模式、时间戳、run_id 和模板来源元数据。运行依赖哈希另存 provenance，不混作 config_hash。
5. template_id 必须从 server registry 解析；profile 与 classification 分离。等价的数值输入得到同一个 hash，但 lineage 不同可有不同 classification。

| 已登记模板来源 + 完整数值协议 | classification |
| --- | --- |
| fast 模板，配置未改且 benchmark 已批准 | LIVE_FAST_RUN |
| 明确选择某 paper 模板且全部数值协议匹配 | LIVE_PAPER_PROFILE |
| 来源为 paper 模板，任一正式数值参数修改 | PAPER_SCALE_CUSTOM（UI 列出真实网格/T/差异） |
| 来源为 fast 且修改，或直接 custom | CUSTOM_RUN |

从 D_u 改为 B_u 数值不自动重命名 paper.B_u；必须明确选 B_u 模板。论文 profile 也不能证明科学复现已成功。展示/输出设置的变化单列 output_diff，不影响数值协议匹配；仍计入 config_hash。Run 提交再次验证 config、模板/能力版本、幂等键，不能信任一次预览返回的标签。

## 3. Run 生命周期（待 P3 实现）

RunRecord：run_id（服务端 UUID）、status、requested_profile、classification、verification、data_origin=LIVE_RUN、config_hash、normalized_config、effective_solver_config_ref、created_at/started_at/finished_at、completed_step/physical_time、worker_identity/heartbeat、cancel_requested、error、provenance_ref。V2 data_origin 为独立枚举，不扩展/复用 V1 FROZEN_PRODUCTION。

```text
QUEUED → STARTING → RUNNING → POSTPROCESSING → COMPLETED
任一非终态 → FAILED
取消成功 → CANCELLED
```

只有真实求解和后处理校验通过、输出原子提交后才能 COMPLETED。cancel_requested 是请求事实，取消未结束不能提前 CANCELLED。重启发现丢失 worker 标为 FAILED / WORKER_INTERRUPTED；不自动伪续算。verification 初始 UNVERIFIED，科学核查有记录才升级为核查状态，不能由 profile 自动设置。

## 4. 缺失资源与错误 DTO（待 V2 路由实现）

V2 成功 envelope：`schema_version:2.0.0, request_id, data, warnings`；失败 envelope：`schema_version:2.0.0, request_id, error:{code,message,retryable,target:{resource_type,identity},details:[{field,reason}]}`，不带伪造 data。V2 model 单独命名，不能把 V1 FailedEnvelope 改为新形状。

| HTTP | V2 error code / 场景 |
| --- | --- |
| 400 | INVALID_REQUEST：语法、类型、未知字段、重复 JSON key |
| 415 | UNSUPPORTED_MEDIA_TYPE：JSON body 路由收到非 JSON |
| 422 | UNSUPPORTED_PARAMETER / UNSUPPORTED_COMBINATION / CLARIFICATION_REQUIRED |
| 404 | UNKNOWN_RUN / SNAPSHOT_NOT_FOUND / REPORT_NOT_FOUND |
| 409 | CAPABILITY_REVISION_CONFLICT / RESULT_NOT_READY / IDEMPOTENCY_CONFLICT |
| 429 | QUEUE_FULL（可重试，资源上限待 benchmark） |
| 503 | RUN_EXECUTION_UNAVAILABLE / AI_UNAVAILABLE |
| 500 | SOURCE_DATA_DRIFT / SOLVER_FAILED / POSTPROCESS_FAILED / INTERNAL_ERROR |

GET /runs/{id} 对已失败任务仍 200 返回 FAILED + safe error；读取其不存在结果则 409 RESULT_NOT_READY，并包含终态原因。未知 identity 与已知但文件丢失区分：后者 500 RUN_STORAGE_ERROR，不能返回空数组或 HTTP 200 science=0。

可选科学结果：`value:null, availability:MISSING/UNSUPPORTED/ERROR, reason`；真实零是 `value:0, availability:AVAILABLE`。这属于 V2 契约，不替换 V1 Fact 格式。公开 DTO 不泄漏本地路径、命令或 raw traceback。

## 5. 已实现 OperationCatalog 扩展

新增兼容默认值：`request_body_model=None`、`success_status=200`、`response_media_type='application/json'`；`response_model` 可为 None，仅限 text。

| 请求/响应 | catalog 与 OpenAPI 行为 |
| --- | --- |
| 既有 path/query | request_model + request_parser，原重复参数/未知参数/覆盖 path 拒绝规则不变 |
| JSON POST/PUT/PATCH | body 使用独立 request_body_model；handler(query, body=validated_body, **path_values)；OpenAPI required requestBody/application/json，保留 path/query parameters |
| 202 JSON | 成功状态由 success_status 控制；response_model 仍验证结果；OpenAPI 成功响应键为 202 |
| SSE | response_media_type=text/event-stream、response_model=None；handler 返回 Flask Response/iterator，catalog 不做 JSON model_validate，不预消费流 |
| HTML | response_media_type=text/html、response_model=None；handler 返回 Flask Response；OpenAPI schema type=string；转义责任属于 P6 report renderer |

JSON body parser 拒绝非 object、重复 key、非标准 JSON NaN/Infinity；之后使用 Pydantic `model_validate_json` 保留严格 JSON 的 tuple-array / ISO date 语义；body 不与 query/path 合并。错误处理继续使用原 V1 FailedEnvelope，待 V2 路由实现时接入 V2 专用错误输出；这些新增 transport 当前仅由软件测试路由验证。

注册期拒绝非整数/非法 success status、204（当前所有 transport 均有 body）、success/error 状态冲突、GET body、不支持 media type、JSON 没有 model 或 text 带 model。JSON body 路由不能用 `{body}` 作 path selector，避免覆盖 handler 的专用参数。text handler 返回错类型/MIME/状态视为服务器错误，不能把 handler 的失败状态改成成功。所有实际 API 路由仍经过 catalog.assert_routes。

P3 SSE 事件草案：UTF-8 `id: <monotonic sequence>`、`event: status/progress/completed/failed/cancelled`、`data: <JSON>`，注释 heartbeat，支持 Last-Event-ID。流建立之前检查身份/可用性，失败返回 JSON；流开始之后用 error event 报告，不能再更换 HTTP 状态。P3 还须补充 Header 契约、重连、线程容量和轮询回退；P0 没有实现 SSE 服务。

默认 export OpenAPI 和 TypeScript 与现有保存文件 byte-identical；当前没有新增 V2 product route，因此无需修改生成文件。P1 注册真实 V2 路由后再生成并保持 V1 paths/schemas 稳定。

## 6. P1 实际落地（2026-10-03）

以上“待实现/未发布”是 P0 时点记录。P1 已实现模型、登记与 `GET /api/v2/cases`、`POST /api/v2/experiments/validate`、`POST /api/v2/experiments/parse-natural-language`。实际验收见 [06_P1_ACCEPTANCE.md](06_P1_ACCEPTANCE.md)。V1 paths/components 保持一致；合并 OpenAPI 与生成类型增加 V2，不能再要求整个文件等于纯 V1 文件。

- 配置的 schema/protocol 为 `2.0.0` / `case8.protocol.p1.1`，capability 为 `case8.capability.p1.1`；source manifest 为 `v2-p0.1`。
- 仅登记网格组合 64×16、128×32；q_aa=3.96/13.2、q_at=0/0.396、CFL=0.05、T=0.04/0.08。候选值可验证但 `execution_verified=false`，没有连续范围或已验证稳定性声明。
- 物理、具名两种扰动、计算域、边界、一阶 FV、SSP-RK3、步长与源 checkpoint fractions 自动补全。用户提供这些固定字段时仍验证；未知字段、非有限数、非整数网格及非法枚举拒绝。
- 非法字段/类型/JSON 返回 400，未登记能力值/组合 422，能力版本过期 409，非 JSON 415；V2 body 上限 64 KiB，超过返回 413 INVALID_REQUEST。错误 details 只返回 field/reason，不回显原始值、provider 错误或 traceback。
- `config_hash` 严格按第 2 节 JSON 规范计算；包括 normalized_config.profile，入口、template lineage 与自然语言原文不计入。同一 profile 与完整配置的三入口 hash 相同。来源不同仍可有不同分类。当前 output 固定，`output_diff` 保留契约供未来开放策略。
- fast 候选没有 benchmark 批准，因此仍为 `CUSTOM_RUN`，不提前赋予 `LIVE_FAST_RUN`。UI 展示待 benchmark；标准 paper template 完整数值匹配才为 `LIVE_PAPER_PROFILE`，从 D_u 改为 B_u 数值仍属 `PAPER_SCALE_CUSTOM`，直到明确切换 B_u 模板。
- AI 返回结构化草稿；问题以 unresolved/unsupported 返回 HTTP 200 草稿，`ready_for_confirmation=false`、`validated=null`；服务缺密钥/网络/超时为 503，错误/空/截断 JSON 为 502 AI_INVALID_OUTPUT。这两个状态不带伪造 data。
- 草稿使用同一 `validate_experiment` 函数；AI 不得猜模板基线，缺参数要澄清。对明确数字、网格、q 歧义、epsilon/Gate/高阶/快照间隔、其他 Case 与笼统性能目标增加服务端复核。语义处理不能视为完美 NLP 保证，最终仍由用户核对原文和完整摘要。
- UI 确认再次提交原始配置和 capability revision；修改参数/入口/原文后确认失效。未建立 Run API、存储或调度，P3 创建 Run 时必须再次调用服务端验证，不可信任预览响应中的分类/hash。
- 密钥仅在 `DeepSeekClient` 私有属性中读取后端环境；不进入 Settings/model/OpenAPI/前端。单次请求有 2048 output-token / 256 KiB provider response / 30s 默认期限；没有工具调用或自动重试，不跟随携带授权头的重定向。

默认模型及 JSON mode 在实施时依据 [DeepSeek 官方 JSON Output](https://api-docs.deepseek.com/guides/json_mode/) 与 [官方 Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) 核实，使用 `deepseek-flash` 和 `https://api.deepseek.com/chat/completions`。这不等于本机已通过真实账号调用验收。

用户随后提供密钥，已完成 6 个真实 provider 场景与 1 个真实浏览器流程，见 P1 验收与对应 JSON 记录。密钥保存于 Git 忽略的 `.env`，由 `scripts/serve_backend.ps1` 显式加载到后端进程。原 Python 入口与 frontend 不自动加载；不改变 V1 的环境读取行为。

## P2 实施追加（2026-10-03）

上节保留 P1 当时的能力状态。当前 capability revision 为 `case8.capability.p2.1`，source manifest 为 `v2-p2.1`；配置 schema/protocol 仍为 `2.0.0` / `case8.protocol.p1.1`，数值配置 hash 规则不变。

- `LiveCase.execution_status=STANDALONE_VERIFIED` 表示独立 Adapter/CLI 已验证；`execution_available=false` 保持网页提交关闭。Run HTTP API/队列/SSE 属于 P3，目前 `/api/v2/runs` 仍为 404。
- 支持的 INPUT capability `execution_verified=true`，以 P2 的参数生效、短程/完整协议实际执行为依据；不声称登记值全部组合都已获得稳定性证明。UNSUPPORTED 及 OUTPUT capability 仍为 false；P4 scientific result API 尚未交付。
- fast D_u 64×16、CFL=.05、T=.04 已完成三次独立重复 benchmark，`benchmark_status=PASSED`。来自该已登记模板且数值协议未变的配置为 `LIVE_FAST_RUN`；修改参数回到 `CUSTOM_RUN`。paper 模板 lineage 规则不变。
- `execution_verified` schema 改为 boolean；benchmark enum 增加 PASSED；运行状态 Literal 更新为 STANDALONE_VERIFIED。OpenAPI 与 TypeScript 同步再生成，原 47 条 V1 路径/298 个 V1 schema 子集经定向回归仍不变。
- 同一配置反复 CLI 运行生成不同 UUID，source/config/effective config/output 哈希独立记录。smoke 为显式部分运行，不能赋予完整复现身份。

实际输出与比较误差见 [P2 验收](07_P2_ACCEPTANCE.md)。P1 真实 AI 的历史记录不重新改写；其复查脚本已适配 fast 的新分类，本轮没有新增 provider 付费调用。


## P3 实施追加（2026-10-03）

- 新增八条操作（七条路径）：Run 创建、分页/筛选列表、详情、取消、SSE、分页 history、snapshot index、snapshot Density。成功创建返回 HTTP 202；重试相同请求标识返回相同 Run。当前 OpenAPI 为 57 paths / 350 schemas；V1 路径与科学模型保持兼容。
- 创建 body 继承 P1 config/submission，额外要求 UUID v4 的 idempotency_key 和 64 位 confirmed_config_hash。后端重新验证、重算 hash；确认不匹配或复用 key 改请求为 409。旧能力 revision 为 409，未支持参数为 422。队列满为 429，manager 不在线为 503；幂等重试已有 Run 在离线时仍可读到同一记录。
- LiveCase/ValidatedExperiment.execution_available 改为 bool，由 API 根据 manager PID、创建时身份和新鲜 heartbeat 决定；在线时 execution_status=LIVE_AVAILABLE。纯数值验证与独立 Adapter 保持不依赖 daemon，配置 hash 规则及数值能力 revision 未改变。
- RunRecord 将 status、classification、data_origin、cancel_requested 分开，progress 仅来自 worker 的 completed_steps/physical_time。QUEUED 不等待求解；发布 COMPLETED 前必须校验输出和完整时间区间。成功接收的取消由 manager 仲裁；终态取消幂等且不会覆盖 COMPLETED/FAILED。
- 事件在每 Run 的原子 run_control.json 中与记录一起提交，单调 event ID；SSE 接受 after 或 Last-Event-ID，重放之后的事件。10 秒心跳、30 秒连接轮换、最多四连接，超过为 429；前端同时四秒轮询。无 ETA。
- 列表 offset≥0、limit=1–100、可选状态筛选；history limit=1–200。查询重复键、非法 cursor、未知 selector 与 path override 拒绝。只接受服务端 UUID 与登记 snapshot identity，不公开文件路径或 traceback；日志仅显示真实数值进度行。
- snapshot 仅在成功完成后可读；未完成为 409 RUN_RESULT_NOT_READY，未知快照为 404。Density 直接来自本次快照保守变量第 0 分量，C order / y,x，提供实际 shape、原生 cell 坐标、extent、model density 单位、时间和快照 hash。P3 history 与 Density 不冒充 P4 的完整 ScientificRunResult 或累计空间分配。
- factory/OpenAPI 无求解启动副作用。显式 launcher/daemon 使用跨进程独占 leader lock；事务锁保护队列、幂等映射、取消和事件。中断活跃 Run 记录 WORKER_INTERRUPTED，队列恢复；提交在 Run 与 index 两次提交之间崩溃时，重试及 dispatcher 都修复索引，不重复启动高成本任务。
- 原生 PID 加进程创建时间识别身份；恢复与终止不会仅凭旧 PID 杀进程。worker 每步检查 manager 存活，避免 daemon 突然丢失后继续积分。科学输出 inventory 排除可变 run_control/status/log 和临时提交文件；数组与诊断仍按 SHA-256 核查。

## P4 实施追加（2026-10-03）

完整结果契约、五条新增 API、六种派生场、全步熵历史、原生瞬时/累计 face、宏观 detector 与结构化 view-context 见 [P4 科学结果定义](10_P4_SCIENTIFIC_RESULTS.md)。之前章节记录相应阶段的历史状态；当前 OUTPUT capability 已验证并开放，三类核心结果及 allocation 的本 Run 可用性仍单独返回。输入数值协议未变，capability revision 保持 p2.1；结果后处理定义独立登记 p4.1。

新 Run 在 worker POSTPROCESSING 内提交经过严格校验的 ScientificRunResult 并纳入输出 hash 清单；结果、Evidence、区域上下文共享 result_hash。保留 P3 Density 接口和 V1 wire format。缺失累计空间分配不补算、不借旧数据；真实零保留为 AVAILABLE / 0。快照、变量和区域选择保存在 URL 查询中，刷新恢复。

## P5 实施追加（2026-10-03）

新增 `POST /api/v2/ai/runs/{run_id}/interpret` 与 `POST /api/v2/ai/chat`，成功均为 200 的 V2Envelope[AIAnalysis]。OpenAPI 当前为 64 paths / 378 schemas。解读无用户参数 body，引用验证后的 Run；问答 body 只允许 run_id、message（1–2000 字符）和严格 view selection，统计量全部由服务器重算。

AIAnalysis 记录 result/context hash、prompt version、model、created_at、cached、可选 interpretation/assistant、确定性 evidence、limitations 和 current_view。claim 类别与数值必须对应本上下文事实；缓存不是科学 verification，也不触发运行。错误包括 UNKNOWN_RUN/SNAPSHOT_NOT_FOUND=404、RUN_RESULT_NOT_READY=409、AI_INPUT_LIMIT=413、AI_BUSY/AI_BUDGET_LIMIT=429、AI_INVALID_OUTPUT=502、AI_UNAVAILABLE=503、AI_CACHE_INVALID/RUN_OUTPUT_INVALID=500。详见 [上下文与科学边界](12_P5_AI_CONTEXT.md)。

## P6 实施追加（2026-10-03）

新增 `POST/GET /api/v2/reports/{run_id}` 与 `GET /api/v2/reports/{run_id}/html`，OpenAPI 为 66 paths / 380 schemas。前两者返回 V2Envelope[ReportMetadata]；HTML 是 catalog 登记的 text/html Flask Response，并带 CSP sandbox。ReportMetadata 将报告状态、Run/result/context/renderer/report identity、AI 可用性/model/prompt/content hash、HTML SHA-256/长度和受控 URL 分开。报告只读已验证结果及现有 AI 缓存；不调用 provider、不创建 Run。未生成、版本变化、文件漂移、非完成 Run、未知 Run 与生成冲突均有独立状态/错误。详见 [P6 报告契约](14_P6_REPORTS.md)。

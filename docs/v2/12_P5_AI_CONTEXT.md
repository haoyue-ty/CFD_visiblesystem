# V2-P5 科学上下文、解读与问答

日期：2026-10-03（Asia/Shanghai）。用户授权范围为实施计划 P5，复用 P1 DeepSeek、P3 RunStore 和 P4 结果服务；没有添加 AI 求解执行权限或 P6 HTML 报告。

## 结构化上下文

`backend/ai/context_builder.py` 从 `ScientificResultService.result()` 构造 `ScientificAIContext`。先核实本 Run 已完成、输出哈希及科学身份，再投影 normalized config、identity、runtime、熵定义/终值、宏观指标、累计 allocation 可用性与积分误差、limitations 和 evidence。不传 history 全步 rows、cell/face values、NPZ/NPY、软件磁盘路径、提交原文、密钥或其他服务器文件。初始条件与运行信息的每个数值标量也有对应证据，防止真实数据出现在 prose 中却没有可引用 ID。

证据 ID 为 `ev.run.<uuid>#<quantity-path>`，是本 Run Evidence 的结构化事实选择器；不是历史冻结证据。每个事实包含 value、unit、availability、reason 和 definition，缺失值与 AVAILABLE/0 分开。identity 证据说明本次 classification 和 verification，不承诺复现成功。

问答请求只提交 `run_id / message / view`。view 包含登记变量、真实 snapshot identity 和可选矩形四边界；不能提交 mean、result_hash、路径、命令或任意额外字段。后端重新计算 P4 view-context，将 cell center 数量、min/max/mean、时间、步数、区域、snapshot hash 加入上下文。早期快照统计与终态 detector 指标保留各自时间；局部 Pi face 统计及其他运行/论文差值未提供，明确列入局限。

## AI 输出和科学校验

解读包含 `summary / key_findings / observations / limitations / suggested_questions`；问答包含 answer claims 和 limitations。claim 区分 FACT、INTERPRETATION、LIMITATION，每条有本上下文的 evidence_refs。summary 必须为解释，observations 必须为事实；缺失证据只可用于局限。系统提示要求精简输出，防止引用列表挤满 provider 输出预算。

严格 JSON/DTO 拒绝重复键、非有限值、额外字段、非法类别和无效引用。每条 claim 的数字标量必须与该条引用的 AVAILABLE 数值事实一致（真实零和整数要求精确相等；其他浮点使用相对容差 5e-6、绝对容差 1e-12，只用于格式化表示且保持符号；不计算新科学量）。百分比换算与中文数词数量不作为可绑定标量接收；已登记协议/方法名称中的数字单独识别，不混作计算结果。前端额外直接呈现引用的服务器事实和值。

系统提示和断言校验限制普适稳定性、最优方法、所有模态改善与根据 E_at 大小排名；允许明确否定这些结论和提出后续验证问题。用户消息和数据文本都是内容，没有文件、密钥、命令或求解工具。HTML 和危险路径/凭证样式不会作为合格 prose 发布；前端只用 Vue 转义文本。格式/引用/数字校验失败最多重写一次，仍不合格即 502，不写入成功缓存。

机器核查覆盖身份、数值标量、可用性和引用存在性；定性解释仍需要科研判断。有效引用不会自动证明所有自然语言因果或比较结论。问答为每次依当前视图独立回答，首期不保存并使用对话记忆。

## 缓存与隔离

`POST /api/v2/ai/runs/{run_id}/interpret` 的 key 为 `[result_hash, prompt_version, model]` 的 SHA-256。Run 内跨进程锁防止同时刷新重复调用；正在生成返回 429 AI_BUSY。原子文件同时记录 context_hash、模型、prompt version、结果身份、引用事实、局限和生成时间。命中时再次验证 Run、结果、上下文与内容；密钥缺失/服务关闭不影响已有合法缓存。非法缓存返回明确错误，不把它当作科学结果。

`POST /api/v2/ai/chat` 为无工具、无执行权限的独立问题。回答绑定提交时的视图，前端切换变量/帧/区域会丢弃旧响应；跨 Run 请求也有 generation 隔离。成功记录不保存用户原文，仅保存经过验证的回答和上下文身份。

Run 的 `ai/` 与预留 `report/` 从科学 output inventory 排除。解读、费用记录或刷新不会重写 config、provenance、数组或 result_hash。AI 失败也不改变 Run COMPLETED 状态、既有图表和 Evidence。确定性 HTML 报告仍属 P6，不能据本阶段宣称已交付。

## 调用预算、重试与错误

- 每次 provider 网络请求总 deadline 默认 30 秒（环境可改至 60）；最多一次暂时性网络/429/5xx 重试，退避和读取都在同一 deadline 内。认证、永久 HTTP 拒绝不重试，禁止重定向携带密钥。
- 默认输入 32,000 字符、输出 2,048 token、响应 256 KiB；结构校验最多一次额外模型重写，最多两次 complete_json。全部网络尝试均计入预算。
- UTC 日默认 500,000 token 预算，前置保守预留 `UTF-8 输入字节 + 输出上限 + 协议余量`。成功响应的合法 provider usage 一次性核销多余预留；失败/中断不退款。预算不足在请求前返回 429 AI_BUDGET_LIMIT。不是人民币/美元计价或报价。
- 每个后端 provider 客户端最多两个同时 complete_json；解读另有跨进程 Run 锁，预算也由跨进程锁保护。长度越界 413 AI_INPUT_LIMIT；未配置、超时或连接故障为 503；不合法输出为 502。安全记录区分 TIMEOUT、CONNECTION、AUTH、RATE_LIMIT、PROVIDER_5XX 等，不返回 provider 原始错误正文。
- `runtime/ai/calls` 保存 call ID、输入 hash/长度、模型、attempt、时间、状态、usage 和额度；不保存 prompt、用户原文、密钥或 Authorization。科学 Run 内拒绝记录只存输出 hash、错误类别/受控字段位置和版本。

服务端使用 `.env.example` 中的变量，PowerShell 7 launcher 的显式 allowlist 已同步。测试环境与可控 provider 夹具不成为生产 fallback；真实验收使用已保留 P4 Run，不新增 CFD。

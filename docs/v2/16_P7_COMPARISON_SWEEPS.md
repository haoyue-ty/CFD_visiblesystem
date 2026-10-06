# P7 同条件对比与参数扫描契约

日期：2026-10-04（Asia/Shanghai）。仅扩展 Case 8，科学源与源算法保持只读。

## 同条件判定

`POST /api/v2/comparisons` 接收 `run_a / run_b / field / snapshot_time`，仅使用成功完成且来源哈希通过校验的 V2 Run。返回双方完整结果身份、来源、差异、原生字段、统一色标及终态指标。

核查完整 Case、物理量和初始条件、计算域和网格、CFL、终止时间、积分器和步长策略、通量方法及源 hash、离散/边界、后处理版本/hash、detector/window/normalization/适用条件以及熵积分定义。`q_aa / q_at` 是允许改变的因素；profile 和输出策略不改变同条件判定，但其差异仍列出。其他差异令 `same_conditions=false`。

共同快照按真实模型时间匹配（绝对容差 1e-12），默认最后共同时间，不按 snapshot 序号、最近帧或插值替换。显式指定无共同帧的时间返回 409 `COMPARISON_TIME_UNAVAILABLE`。没有任何共同时间时字段和色标为 null，附不可用原因。联合原生字段最小/最大值构成两图共同色标；不重采样。字段单位和定义不一致时返回 409。

宏观指标始终来自双方各自终态，与选择的流场快照时间分开标注。只有同条件、定义/时间一致、双方指标均有效时才返回 `b_minus_a`；缺失保留 null 与原因，真实零保留 0。累计熵曲线按各自真实接受步绘制，单位和空间/RK 积分定义来自结果。非同条件只能并列观察，不能作普适稳定性或性能排名。

页面：`/workspace/compare`；支持 `?a=<run_id>&b=<run_id>`。

## 预算受控扫描

| API | 用途 |
| --- | --- |
| POST `/api/v2/sweeps/preview` | 验证基础配置与每个组合，返回分类、hash、组合数、预算和警告；不入队 |
| POST `/api/v2/sweeps` | 携带 `confirmed_sweep_hash` 和 UUID4 `idempotency_key`，重新验证并持久保存；202 |
| GET `/api/v2/sweeps` | 分页列表：offset>=0，limit=1..100 |
| GET `/api/v2/sweeps/{sweep_id}` | 父状态、每个子 Run、真实步数、处理/成功计数 |
| POST `/api/v2/sweeps/{sweep_id}/cancel` | 幂等取消，等待活动子 Run 停止后进入终态 |

输入复用 `config / submission`，增加 `q_aa_values / q_at_values / max_tasks / time_budget_seconds`。模型上限每轴 3 值、总任务预算 1..9；实际能力仅登记 q_aa={3.96,13.2}、q_at={0,0.396}，所以当前最多四个唯一组合。未核查的连续系数返回 422 `UNSUPPORTED_PARAMETER`。重复值、空轴、非有限数、布尔数值、超组合预算、任意额外字段均拒绝。

总墙钟预算 1..1800 秒，从提交时计算，包含排队、求解、后处理；预算已纳入确认 hash。未完成父扫描最多三项。每次只为最早未完成扫描提交一个子 Run，复用 P3 的同一串行队列，不启动第二个求解 worker。普通 Run 保持原队列顺序和资源限制。

持久记录位于 `runtime/sweeps/<uuid>.json`；扫描锁先于 RunStore 锁。每项独立 UUID4 提交键在入队前持久保存，重启或“Run 已提交但父状态未更新”的崩溃窗口会用既有 RunStore 请求索引恢复原身份，禁止重复计算。中断 worker 仍沿用 P3 `WORKER_INTERRUPTED` 失败语义，不恢复半条数值轨迹。

取消和预算耗尽先持久保存停止意图，取消排队/活动子 Run，跳过所有未提交项。活动子 Run 未停止时父状态 `CANCELLING`；全部停止后用户取消为 `CANCELLED`，预算耗尽为 `FAILED / SWEEP_TIME_BUDGET_EXCEEDED`。子运行失败仍记录实际失败，扫描其余已确认组合；全部处理后若有失败，父状态为 `FAILED / SWEEP_CHILD_FAILED`。`settled_tasks` 包含完成、失败、取消、跳过，`successful_tasks` 仅统计完成。

取消/预算通过现有 manager 每约 250 ms 核查，并等待进程终止，属于有界响应而非硬实时截止。manager 停机时不会执行求解；恢复后根据持久墙钟预算立即停止过期扫描。

页面：`/workspace/sweeps` 创建/分页列表；`/sweeps/:sweepId` 刷新后继续查看、取消和进入成功 Run 的对比。网页从基础 Run 复制数值配置，使用专业表单元数据及 custom profile，预览明确展示实际网格、T、CFL、离散、积分器、分类与逐项 hash。

## 能力边界

epsilon 仍无统一物理语义与 Solver 生效验收，当前不提供 epsilon 扫描；不以其他扰动系数替代。更广 Case 必须单独立项、登记 adapter、参数能力与科学定义。此次没有增加分布式执行、任意脚本/路径、连续系数能力或通用性能排行榜。

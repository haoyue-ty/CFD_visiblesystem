# V2-P6 HTML 报告契约与版本

日期：2026-10-03（Asia/Shanghai）。使用 P4 `ScientificRunResult`、`ScientificResultService.field()` 与 P5 `ScientificAIContext`，没有第二套诊断或报表数值计算。报告端点不启动 CFD、不调用 provider。

## 页面与 API

完成 Run 的结果页提供报告入口；`/runs/:runId/report` 先核查状态，用户点击生成/更新后预览，再保存 HTML。

| 方法与路径 | 行为 |
| --- | --- |
| `POST /api/v2/reports/{run_id}` | 同步生成或复用当前版本，200 + `V2Envelope[ReportMetadata]` |
| `GET /api/v2/reports/{run_id}` | 200；状态为 `NOT_GENERATED / READY / STALE`，不会创建 HTML |
| `GET /api/v2/reports/{run_id}/html` | 200 `text/html; charset=utf-8`；核查身份、长度与 SHA-256 后读取 HTML |

未知 Run：404；非法 query：400；Run 未成功完成：409 `RUN_RESULT_NOT_READY`；未生成或旧版本 HTML：409 `REPORT_NOT_READY`；同 Run 并发生成：429 `REPORT_BUSY`；科学输出/报告文件漂移：500。只接受服务端 Run identity；没有文件路径、任意内容、下载目录或 AI HTML 入参。V1 操作与 schema 保持兼容。

## 十二节与数据来源

1. 实验概况：Run identity、分类、verification、配置/结果/报告哈希与版本。
2. 输入方式：受校验 `request.json` 中的 submission，包含原始自然语言、模板与 parser 版本；全部作为文本转义。
3. 流动物理参数：归一化 physics 与完整初始条件。
4. 数值配置：grid/domain、time、离散、边界、输出策略。
5. ShockPath 方法配置：真实 q_aa/q_at、method_id 与模板差异/warnings。
6. 求解过程：起止 UTC、接受步、实际终止时间、dt、运行耗时/RSS 与全部真实快照索引。
7. 流场结果：终态密度、压力、Mach；真实 cell 矩形、C-order `[y,x]`，y 轴下→上；各自 min/max 色标、单位、snapshot_id/time/源哈希及全部六种变量定义。
8. 熵耗散路径：全部真实接受步 E_bg/E_aa/E_at 曲线、最终 totals、RK 权重/时间与 face measure/空间范围/累计定义；原生累计 face 的可用性、定义、标量积分核查信息。缺失不填零。
9. 宏观指标：P4 指标原值/null、可用性/原因、单位/time、detector/window/normalization/适用条件/分辨率限制。
10. AI 科学解读：只读取当前 result/prompt/model 的合法 P5 自动解读缓存；重新校验 context、证据与 prose。事实/解释/局限保留类别，每条引用显示对应确定性证据。没有缓存或缓存损坏时明确不可用。
11. 科学边界：P4 limitations 与 P5 已定义边界，确定性提供；不把 E_at 大小作为方法优劣，不继承历史冻结状态。
12. Provenance / Evidence：相对来源、method/source/software/postprocess/effective-config/output 哈希；完整数据在内嵌 JSON 中可核查。

AI 解读在结果页生成；报告不会为了填满第十节发起收费请求。服务关闭时，已有合法缓存仍能纳入；没有合法缓存时仍有完整十二节报告。问答为当前视图临时上下文，不自动纳入实验报告。图是终态的三个变量，不伪造其他帧；报告没有提供自由字段/时刻选择。

## 版本、保存与隔离

`report_version=case8.html.p6.1`。`report_id` 是 result_hash、renderer 文件 SHA-256、scientific_context_hash、submission hash、经校验 AI content hash（含 model/prompt/context）与降级原因的摘要；任一变化生成新版本。`report/current.json` 是当前指针，`report/<report_id>.html/.json` 保存历次产物。report 与 ai 不进入科学 output inventory；原 provenance、result_hash、queue identity 不因报告发生变化。

同 Run 生成有跨进程 file lock；HTML 与 metadata 使用临时文件替换，再提交 current 指针。GET 核查受控路径、identity、版本、HTML 长度与 SHA-256。报告文件损坏会明确拒绝，不能当作有效报告导出。

下载由受控 HTML API → Blob → 文件；所有 SVG/CSS/数据内嵌，离线无 API/CDN、JS 图表库或 runtime 图片依赖。HTML 中的 `report-data` 是 inert JSON，转义 `< > &` 防止 `</script>` 突破边界；可用常规 HTML/JSON 工具解析原值。嵌入的是逻辑版本元数据，HTML 最终字节哈希/长度保存在外部 receipt 与页面中，避免把文件自身哈希嵌入自身的循环定义。

用户、AI、metadata 与 provenance 字符串全部 HTML 转义。服务器响应 CSP sandbox，默认禁止脚本/网络/表单，iframe 采用空 sandbox；保存文件也内嵌 CSP。报告不执行自然语言或 AI 输出。普通文本中的 HTML 片段在报告中仅显示为文本。

未新增环境变量；沿用 `.env.example` 后端 AI 设置、PowerShell 7 launcher 和运行限制。首版报告不提供 PDF、对比/扫描或额外科学断言。

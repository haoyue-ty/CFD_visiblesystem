# V2-P5 AI 解读与上下文科研助手验收

日期：2026-10-03（Asia/Shanghai）。依据用户“进入 p5”与实施计划 P5，沿用 `codex/shockpath-v2`，保留 P0–P4 的未提交内容；未提交/推送 Git，未修改科研源码。

**状态：P5 完成，M5 通过。** 已交付真实结果自动解读、按版本缓存、当前 Run/变量/帧/区域问答、证据标量约束、调用预算/记录和独立降级。HTML 实验报告留在 P6。

## 实际验收

| 检查 | 结果 | 产物 |
| --- | --- | --- |
| 完整后端回归 | 1627 passed / 1 skipped，897.20s；保留既有 Windows symlink 权限 skip | [日志](p5_backend_regression.log)、[JUnit](p5_backend_results.xml) |
| P0–P5 定向回归 | 274 passed / 1 skipped，159.51s | [日志](p5_v2_tests.log)、[JUnit](p5_v2_results.xml) |
| 最终 P5 + P1 客户端 + P4 科学测试 | 76 passed，50.95s；含最后新增的缺失密钥、零/整数严格相等保护 | [日志](p5_targeted.log)、[JUnit](p5_targeted_results.xml) |
| 既有完整浏览器回归 | 225 passed；无失败/flaky，retries=0，571.50s | [日志](p5_browser_regression.log)、[汇总](p5_final_checks.json) |
| 当前 P5 浏览器 | 3 passed；真实缓存解读/刷新、真实区域提交、证据链接、视图切换清除旧回答、缺失密钥/超时重试、流场独立性、旧 Run 缺失 face、390px 手机无横向溢出 | [日志](p5_browser.log)、[JSON](p5_browser_acceptance.json)、[桌面](../../output/playwright/p5-desktop.png)、[手机](../../output/playwright/p5-mobile.png) |
| 真实 DeepSeek | 最终 prompt `case8.science.p5.5` 六场景通过：fast 解读、零新增调用的刷新、q_at/E_at 科学边界、真实区域 Mach、诱导越界拒绝、旧 Run 缺失 allocation | [结果](p5_live_ai_acceptance.json)、[日志](p5_live_ai.log) |
| 缓存与科学隔离 | 离线 provider 可复用缓存；运行索引、原 provenance 和 result_hash 前后不变；真实 AI 验收没有启动新 CFD | [最终核查](p5_final_checks.json)、[真实验收](p5_live_ai_acceptance.json) |
| 构建/契约/生成类型 | PASS；64 paths / 378 schemas；OpenAPI 与 TS 独立生成 byte-identical；既有大 bundle 告警保留 | [构建](p5_build.log)、[契约](p5_contracts.log) |
| V1 合约子集 | HEAD 的原 47 paths / 298 schemas 定义完全相同 | [最终核查](p5_final_checks.json) |
| 公共资源/生产扫描 | PASS；2438 科学资产；生产包无科研绝对路径、mock provider 或禁止的肯定性科学断言 | [公共审计](p5_public_audit.log)、[扫描](p5_production_scan.log) |
| 科学源保护 | 27,843 文件 / 5,429,811,970 bytes，与原锁定基线的 path/size/mtime_ns/SHA-256 完全相同；43 文件依赖锁核查通过 | [源保护](p5_source_preservation.json)、[最终核查](p5_final_checks.json) |

这些 suite 是独立检查，计数不相加。完整后端回归在本阶段初版代码上启动；之后的证据扩展、token 核销、数值引用精化与精简输出由最终 76 项定向测试、真实 provider、当前浏览器与独立最终核查覆盖。没有以旧 P4 的验收数字冒充本阶段结果。

P5 浏览器直接使用真实 Run 和真实缓存解读；问答排版的 UI 夹具使用真实后端区域统计，专门检查提交/渲染，不冒充真实模型回答。实际 provider 的问答另由六场景 live 验收覆盖。无密钥/超时/错误 JSON、缺失指标、无效证据、同 Run 并发、缓存篡改和预算拒绝使用受控测试，可复查且不需人为损坏生产服务。

## 交付和使用

- 后端 `ScientificAIContext`、claim/analysis 严格 DTO、精简上下文 builder、两条 AI API、原子缓存与无工具问答服务。
- 客户端 deadline、有限暂时性重试、安全错误分类、response/input/output 上限、跨进程 token 预算与 provider usage 核销、调用记录。
- `/runs/:runId` 的自动解读和常驻科研助手；当前选择由 P4 真实统计绑定，前端不提供可被 AI 信任的 mean 或任意结果。
- 每条数值标量对应当前 claim 的 AVAILABLE 证据；零与整数要求精确相等，其他浮点仅允许格式化容差。事实、解释、局限与确定性证据值分开展示。
- Run 的 `ai/` 不进入科学输出 inventory，不污染来源与结果身份；AI 失败仍能看流场、熵预算、宏观指标和 Evidence。

PowerShell 7 使用既有 launcher（在后端加载本地忽略的 `.env`）；打开一个完成 Run 即自动生成或读取解读。提出问题前选择真实变量、帧和可选区域，回答使用后端重算统计。刷新使用缓存；失败时提供重试。已有正常缓存在服务不可用时仍可显示。没有对话记忆，每次问题依当前视图独立回答。

```powershell
pwsh -File ./scripts/serve_backend.ps1
npm run dev --prefix frontend
./.venv/Scripts/python.exe -B -m pytest tests/v2_p5 -q
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p5_finalize
```

真实 provider 复查为 `scripts.verification.v2_p5_live_ai`，需要 `.env`/后端环境的密钥和保留的 P4 Run；它不创建新的 CFD。重复复查先读取可用缓存与已成功验收的同版本场景。当前端到端结果使用 fast Run `463bf7f2-8143-483a-9db2-81559203771b` 和旧 Run `ea852646-72ce-40fc-b5f3-99329ff0895b`；均没有提升为历史冻结身份。

## 首轮问题和修正

1. 首次 API 注册遗漏 catalog 的 `request_model=None`，应用构造失败；补齐必需参数后重新导出、构建并回归，没有删除 catalog 一致性检查。
2. 生成类型对 view 的默认 null 字段要求显式提交；前端补齐四个 null 边界，保持后台严格模型。
3. 首轮模型输出暴露数字/证据校验误拦截：协议名称 P2/V2、p10/p50/p90 和“进一步/一个”等被当成计算量。对已登记名称单独识别；数值陈述仍逐条绑定证据。初始条件/runtime 数值也补齐确定性证据，不能把真实但无引用的数字直接放行。
4. 部分实际输出写近似数值却引用错项，或引用数量越界；拒绝记录仅保存 hash/类别。最多一次严格重写要求重新生成 prose、把数值放在证据卡中，不把旧答案当作新事实。最终区域、q_at 与诱导场景均拿到合规真实回答。
5. 旧 Run 的长输出达到 provider max_tokens，返回不完整响应；将解读压缩为简短 summary、各最多两条发现/观察及三条局限/追问。保留输出上限和异常拒绝，最终缺失 allocation 场景通过。
6. 开发验收命中过默认 200,000 token 保守额度。按完整上下文及重试规模将默认额度定为每日 500,000 token、输入 32,000 字符，未修改用户密钥；前置拒绝、跨进程预留与一次核销仍被测试覆盖。这是 token 上限，不是货币报价。正式 provider 记录保存在忽略的 runtime。
7. 首次 P5 浏览器的第三项在旧 Run 尚未生成合法缓存时失败；保留实际问题记录，完成真实 provider 后重新执行三项，最终 retries=0 全通过。没有使用虚构解读替代该旧 Run 的验收。

机器核查不等于自然语言因果论证已获得科学证明，定性解释仍需判断。新运行对照、论文差值、局部 Pi face 统计与 HTML 报告没有在本阶段补造；下一阶段为 P6。

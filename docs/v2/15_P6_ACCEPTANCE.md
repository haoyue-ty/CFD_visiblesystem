# V2-P6 报告与首版闭环验收

日期：2026-10-03（Asia/Shanghai）。依据用户“进入 p6”及实施计划 P6，沿用 `codex/shockpath-v2`，保留 P0–P5 工作区内容；未提交/推送 Git，未修改科学源。

**状态：P6 完成，M6 通过；Case 8 首版 V2 闭环已交付。** 已实现固定十二节、自包含 HTML 报告、页面预览/保存、版本与文件哈希核查、AI 关闭降级，并完成三入口独立真实求解 → 结果 → 真实解读/问答 → 报告的验收。P7 对比与扫描继续后置。

## 实际检查

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 最终完整后端回归 | 1645 passed / 1 skipped，1045.09s；既有 Windows symlink 权限 skip | [日志](p6_backend_regression.log)、[JUnit](p6_backend_results.xml) |
| 最终定向报告/P5/P4/P1 客户端回归 | 88 passed，90.10s；包括报告版本、锁、路径、转义、缺失/零、缓存漂移、AI 故障 | [日志](p6_targeted.log)、[JUnit](p6_targeted_results.xml) |
| 首轮受契约更新影响的四项复查 | 4 passed，44.12s；最终完整回归亦全通过 | [日志](p6_contract_recheck.log)、[JUnit](p6_contract_recheck_results.xml) |
| 既有完整浏览器回归 | 225 passed，711.59s，retries=0，无 flaky/失败 | [日志](p6_browser_regression.log)、[最终汇总](p6_final_checks.json) |
| 三入口真实网页闭环 | 3 个独立 Run，全为 64×16 fast D_u、478 接受步、T=.04；同 normalized config/hash，真实 NLP、真实解读及当前视图问答，问答重试均 0 | [验收 JSON](p6_live_acceptance.json)、[日志](p6_live_browser.log) |
| 实际关闭 AI | 模板入口通过另一无密钥后端完成确认、真实求解、科学结果、AI 不可用提示及完整确定性报告；随后同 Run 在已配置服务上获得真实解读/问答并更新报告 | [模板场景](p6_live_acceptance.json) |
| 保存与离线 | 三个实际下载文件与 API receipt 的 HTML SHA-256 相同；各有十二节/四张 SVG；阻断全部 HTTP 后从本地文件重新打开，资源请求为 0；390px 手机无横向溢出 | [模板 HTML](../../output/reports/p6-template.html)、[专业 HTML](../../output/reports/p6-form.html)、[自然语言 HTML](../../output/reports/p6-natural_language.html) |
| 数值与科学身份 | config/runtime/metrics/entropy 与科学 API 完全相等；AI/context/result hash 一致，快照/变量/time/hash 明确；报告生成/刷新没有 provider 调用，原 provenance 不变 | [独立最终核查](p6_final_checks.json)、[日志](p6_finalize.log) |
| 真实结果可视检查 | 桌面/手机报告页面、终态密度/压力/Mach 与熵曲线均已查看，未发现空白图、乱码或溢出 | [桌面](../../output/playwright/p6-report-desktop.png)、[手机](../../output/playwright/p6-report-mobile.png)、[流场](../../output/playwright/p6-flow-fields.png)、[熵预算](../../output/playwright/p6-entropy.png) |
| 构建、独立契约/类型生成 | PASS；66 paths / 380 schemas；runtime/export/saved 与独立 TS 生成一致，既有 bundle 大小告警保留 | [构建](p6_build.log)、[契约](p6_contracts.log) |
| V1 合约及资源/生产审计 | HEAD 的 47 paths / 298 schemas 定义完全相同；2438 科学资产；生产包无科研绝对路径、mock provider 或禁止的肯定性断言 | [最终核查](p6_final_checks.json)、[公共资源](p6_public_audit.log)、[扫描](p6_production_scan.log) |
| 最终科学源保护 | 27,843 文件 / 5,429,811,970 bytes，与 P2 起锁定的 path/size/mtime_ns/SHA-256 完全相同；43 文件依赖锁核查通过 | [源保护](p6_source_preservation.json)、[最终核查](p6_final_checks.json) |

这些 suite 独立计数，不相加。最终完整后端回归在实现与契约固定后执行，涵盖最终十二个报告测试；既有浏览器回归期间的末次变更只涉及报告 context hash 元数据，最终当前 P6 网页三入口与独立核查使用最新构建/契约。没有把 P5 数字当作 P6 验收。

## 独立真实 Run 与下载文件

| 输入方式 | run_id | HTML bytes | 报告 |
| --- | --- | ---: | --- |
| 模板（先无密钥） | `08f92162-b308-47ac-9a61-4aa1af08c048` | 1,040,444 | [HTML](../../output/reports/p6-template.html) |
| 专业参数 | `91eb2644-fbfc-47ae-8be1-be5b879f8237` | 1,040,465 | [HTML](../../output/reports/p6-form.html) |
| 自然语言 | `912e0b54-c745-49eb-b3a8-f8ef3d2260e8` | 1,040,069 | [HTML](../../output/reports/p6-natural_language.html) |

三入口归一化配置 hash 为 `9b5263971c7a0814203080c1ad33303aaa0496fb4d738be5a7c73f225a7acd85`。每次创建独立 UUID、真实重新求解；没有读取 V1 冻结结果充当新运行。result_hash 包含各 Run 的身份/runtime，彼此不同是正常结果。完整 receipt、AI prompt/model/content hash、科学结果 hash 与问答证据保存在 live/final JSON 中。

## 交付与演示

- 后端报告 DTO、三条 catalog API、当前 AI 缓存只读校验、确定性 HTML/SVG renderer、原子版本文件与导出哈希核查。
- `/runs/:runId/report`、完成 Run 的入口、受 sandbox 限制的预览、Blob 保存 HTML、错误与旧版本状态。
- [报告契约](14_P6_REPORTS.md)、更新后的 README/契约文档/环境变量示例/实施计划，以及可复查的网页演示与最终核查脚本。

PowerShell 7 从项目根启动后端与前端，选择模板/专业参数/自然语言，核对并确认，再启动求解；完成后查看六字段/真实快照、熵预算、指标及证据，查看解读或就当前视图提问，然后进入报告页生成并保存。关闭后端后可直接打开保存的 HTML。

```powershell
pwsh -File ./scripts/serve_backend.ps1
npm run dev --prefix frontend
```

无密钥仍可用模板/专业参数完成真实求解与确定性报告；新自然语言草稿和新解读/问答需要密钥。已有合法解读缓存可在 provider 关闭时复用。报告生成不会新增模型调用。

复查（live 脚本会新建三次真实 CFD，并发生真实 AI 请求）：

```powershell
./.venv/Scripts/python.exe -B -m pytest tests/v2_p6 tests/v2_p5 tests/v2_p4 tests/v2_p1/test_ai_client.py -q
node scripts/verification/v2_p6_browser.mjs
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p6_finalize
```

## 首轮问题及处理

1. 报告提交来源最初按输入模型读取 `config.json`；核实 adapter 后改为读取实际保存的 `request.json`，并核对与结果的 normalized config hash。`config.json` 继续作为已验证配置，未改科学格式。
2. 首轮测试夹具遗漏自然语言 parser version，且按 Windows locale 读取 UTF-8 AI 缓存；修正夹具与编码后重跑，未放宽生产校验。
3. 首轮完整回归运行时补充 `scientific_context_hash` 并重新生成 schema，造成四项进程内旧 schema 与磁盘新 schema 的一致性失败。保留 [首轮日志](p6_backend_attempt1.log)；固定实现/契约、四项复查通过后重新执行完整回归，最终 1645 passed / 1 skipped。最终回归限制该测试进程的 BLAS/OMP/MKL 线程为 1，与 worker 的线程策略一致，没有修改求解配置或算法。
4. 首轮网页验收与完整回归/源审计并行，真实 fast Run 在浏览器 180 秒等待到期时仍在求解；harness 清理进程，后续 manager 按中断规则处理，不将部分输出当作完成结果。保留 [首轮记录](p6_live_attempt1.json) 与 [日志](p6_live_attempt1.log)。增加浏览器等待上限、在完整回归结束后单独重跑；最终三个 Run 全部完成。没有降低 CFL、网格或终止时间。
5. 网页 harness 补齐 API base URL，并增加真正无密钥后端与对应 preview，确保 AI 关闭验收覆盖真实服务器，数字和报告没有浏览器数值夹具。

## 当前限制

首版导出 HTML；PDF、自由报告字段/时刻、问答会话归档、同条件对比与扫描尚未实现。报告固定终态密度/压力/Mach 与全步累计标量熵图，完整六字段/多帧/原生 face 仍在工作台查看。AI 解释仍需科学判断，不因机器校验通过升级为因果证明或普适结论。报告文件漂移会明确拒绝导出。科研根和原 V1 freeze 文档保持不变。

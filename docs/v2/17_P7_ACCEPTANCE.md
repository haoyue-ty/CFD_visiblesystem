# V2-P7 验收记录

日期：2026-10-04（Asia/Shanghai）。结论：**M7 通过；同条件对比与已登记 q_aa/q_at 四组合扫描已交付。**

此次在既有含 P0–P6 未提交改造的工作区增量完成；保留原有修改，未提交、未推送。P7 科学源与科学算法未修改。

## 交付与验收映射

| 要求 | 实现与证据 |
| --- | --- |
| 对比先核查条件 | Case、完整初始条件、网格/域、T/CFL/积分器/步长策略、方法/源、离散/边界、detector 及科学定义；真实 64×16 与 128×32 Run 明确非同条件 |
| 变量、时间、色标、指标统一 | 六种原生字段，共同真实模型时间，联合 min/max 色标，计算域几何比例；完整差异列表、终态指标定义与空值原因；累计熵以真实模型时间绘制，A 实线/B 虚线 |
| 小规模串行扫描 | q_aa={3.96,13.2} × q_at={0,0.396} 四次独立真实 Run，各自参数、config/result/output hash 可核查；单 worker，下一 Run 的 started_at 不早于上一 Run 的 finished_at |
| 预算、进度、取消 | 配置预览/逐项验证后确认，持久独立父 identity 与逐项子 identity；总任务与墙钟预算，真实步数，刷新恢复；真实活动 worker 取消与 1 秒预算耗尽通过 |
| 重试、重启和能力变化 | 并发幂等、确认冲突、队列满重试、入队/父提交崩溃窗口恢复、worker 中断、能力版本改变后失败停止且不崩溃 manager，均由隔离测试核查 |
| epsilon/新 Case 前提 | 明确不开放；不替代扰动物理语义，不修改求解器能力。后续需单独立项、参数生效与 adapter/科学定义验收 |

页面 `/workspace/compare`、`/workspace/sweeps`、`/sweeps/:sweepId` 已接入工作台。六条 P7 API、OpenAPI 与 TypeScript 类型同步。运行、对比、扫描均无需 AI 密钥。

## 真实运行

扫描 ID：`3627fc5a-0681-4846-b0ed-b5150644fa52`。基础网页配置来自已完成 P6 Run，数值协议为 64×16、CFL=0.05、T=0.04；扫描输入使用 custom profile，科学分类由后端验证。

| q_aa | q_at | Run ID | 接受步 | Solver 秒 |
| ---: | ---: | --- | ---: | ---: |
| 3.96 | 0 | `76cecb10-44ee-4837-a07d-488477fa4bc3` | 478 | 22.768 |
| 3.96 | 0.396 | `2008b1f3-fcb9-4d2c-9d0c-fdbf33e9215b` | 478 | 24.090 |
| 13.2 | 0 | `ea1a6fca-a4ee-4f73-92f8-f588e45af1f9` | 478 | 26.134 |
| 13.2 | 0.396 | `8c030ad6-1ddf-4d39-8811-64c9d3b4ed34` | 478 | 26.553 |

每次完成全请求时间、六份快照与 22 份科学输出 hash 核查。q_at=0 的全域 E_at 与原生累计 at face 均为真实零。耗时仅为本次同机负载下记录，不构成承诺或通用性能结论。

真实 Run A/B 核查六个共同时间、终态与初始 Mach、联合色标和宏观指标差值；真实异网格 Run 列出条件差异，所有指标差值为 null。显式无共同时间请求返回 409。

原始过程：[真实验收 JSON](p7_live_acceptance.json)；独立复核：[最终核查 JSON](p7_final_checks.json)。截图：[桌面对比](p7_compare_desktop.png)、[手机对比](p7_compare_mobile.png)、[扫描工作台](p7_scan_desktop.png)。

## 回归与失败归因

- 完整后端：**1674 passed / 1 skipped**，`p7_backend_results.xml`；skip 沿用 Windows 符号链接权限限制。
- 最终定向：**128 passed**，`p7_targeted_results.xml`；包含完整回归之后新增的能力版本变化停止测试，以及 P3–P6 相关功能。
- P7 最终浏览器：**4 passed、0 flaky**，`p7_browser_acceptance.json`；实际服务、真实结果、无 mock，核查物理时间 tooltip、几何比例、参数修改取消确认、非同条件、手机无页面横向溢出及刷新恢复。
- 既有浏览器首次全量：**224 passed / 1 failed、0 flaky**，`.cache/phase11/playwright.json`。全量回归并行启动时复用了 P7 live verifier 拥有的 manager；该 verifier 退出后，P1 的“后台运行服务在线”断言失败，页面正确提示后台服务未启动。这是本次验收进程编排错误，保留原始失败记录，不修改或跳过该断言。
- 随后顺序、独立服务复测：**9 passed、0 flaky**，`p7_v1_recheck.json`，包含原失败的 P1 完整确认流程、V1 熵图/快照/标量点击及相关 Cylinder/Closure 流程。P7 最终图表改动也在此版本复测。不能把首次全量记录改写成“一次 225 全通过”。
- `npm run build --prefix frontend`（含 vue-tsc）通过；保留既有较大 bundle 提示。
- 独立 OpenAPI 导出、OpenAPI 3.1 校验、运行时与落盘 byte equality、类型重新生成 byte equality、公共 Evidence 与生产 bundle 扫描通过。当前 71 paths、396 schemas；HEAD 中 V1 paths/schema 子集逐项一致。
- 最后科学根核查：**27,843 文件**的相对路径、大小、mtime_ns、SHA-256 全部一致，`p7_source_preservation.json`；总指纹 `8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`。

`v2_p7_finalize` 直接读取真实文件、Run/sweep identity、有效 Solver 配置、全部输出与累计 face，再复核对比、取消、预算、兼容子集和验收统计；没有重新启动 CFD 或 provider。

## 已知边界与复查

实际只开放已核查的四个系数组合。扫描模型保留每轴 3 值/总预算最多 9 项的防护上限，不代表连续系数已获得执行能力。时间预算从提交计入排队，manager 约 250 ms 核查，停止过程需等待 worker 退出；不是硬实时截止。父任务终态被持久保存，历史扫描不会在每次 tick 反复读取全部旧 Run 事件。

没有共同快照不插值；不同协议仅并列观察。宏观指标始终为各 Run 的终态，流场切换不改变指标的测量时间。单一 Case、同条件或更低某一指标均不构成通用性能排名。

复查命令（PowerShell 7）：

```powershell
./.venv/Scripts/python.exe -B -m pytest -q tests/v2_p7 tests/v2_p3 tests/v2_p4 tests/v2_p5 tests/v2_p6
npm run build --prefix frontend
# 以下创建真正 CFD，依赖现存 P4/P6 reference receipts；与其他服务验收顺序运行
node scripts/verification/v2_p7_browser.mjs
Set-Location frontend
npx playwright test --config playwright.v2.p7.config.ts
npx playwright test --config playwright.v2.p7.recheck.config.ts --grep 'template and form share hash|entropy|scalar|timeline'
Set-Location ..
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p7_finalize
```

定义与 API 细节：[P7 契约](16_P7_COMPARISON_SWEEPS.md)。

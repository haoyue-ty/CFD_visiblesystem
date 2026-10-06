# V2-P4 科学结果与 Run Evidence 验收

日期：2026-10-03（Asia/Shanghai）。范围依据用户“进入 p4”及实施计划 P4。沿用 `codex/shockpath-v2`，保留既有 P0–P3 未提交内容；未提交或推送 Git，未修改科研源，未调用付费 AI。

**状态：P4 完成，M4 通过。** 完成新运行科学结果、派生场、全轨迹熵、宏观指标、瞬时/累计 native face、真实帧播放、区域上下文与 V2 Evidence。AI 解读和 HTML 报告仍属于 P5/P6。

## 实际验证

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 完整后端回归 | 1600 passed / 1 skipped，884.33s；保留既有 Windows symlink 权限 skip | [日志](p4_backend_regression.log)、[JUnit](p4_backend_results.xml) |
| 完整既有浏览器回归 | 225 passed，0 failed / flaky，576.78s，retries=0 | [日志](p4_browser_regression.log)、[最终汇总](p4_final_checks.json) |
| P4 定向科学测试 | 21 passed；派生代数、非物理状态、RK 权重、snapshot 不参与累计、原生几何、积分不一致、缺失/真实零、区域空集与错误状态 | [日志](p4_targeted.log)、[JUnit](p4_targeted_results.xml) |
| 真实 managed fast/custom | 新 Run 的每帧六种字段、瞬时 face、全步 history、累计空间积分、区域统计及全部输出 hash 均逐项对照通过 | [真实运行与对照](p4_live_acceptance.json)、[运行日志](p4_live.log)、[服务器日志](p4_live_server.log) |
| 锁定源码直接后处理 | 两种网格全部六帧的 Euler 派生场及终态 width/RMS/HF 对照误差均 0 | [对照详情](p4_live_acceptance.json) |
| 新 observer 不改变演化 | 独立三步 smoke 与无 observer 的原 SSP-RK3 轨迹 BITWISE；stage guard/RK history 通过 | [smoke 对照](p4_live_acceptance.json) |
| 当前真实浏览器 P4 | 变量切换、帧选择/刷新、真实播放、区域/刷新、越界区域仍保留流场、Run 专属 Evidence、fast/custom/legacy 与手机均通过 | [检查记录](p4_browser_acceptance.json)、[桌面](../../output/playwright/p4-fast-desktop.png)、[手机](../../output/playwright/p4-fast-mobile.png) |
| 构建 / OpenAPI / TS | PASS；62 paths / 370 schemas；独立导出及生成类型 byte-identical；既有大 bundle 告警保留 | [构建](p4_build.log)、[契约](p4_contracts.log) |
| V1 合约兼容 | HEAD 中原 47 paths / 298 schemas 的完整定义均相同 | [最终核查](p4_final_checks.json) |
| 公共资源 / 生产扫描 | PASS；2438 科学资产；生产包未包含科研绝对路径、mock provider 或禁止的肯定性科学结论 | [公共审计](p4_public_audit.log)、[生产扫描](p4_production_scan.log) |
| 最终科学源保护 | 完整 27,843 文件 / 5,429,811,970 bytes，path/size/mtime_ns/SHA-256 与原锁定清单一致；43 文件依赖锁通过 | [源保护](p4_source_preservation.json)、[最终核查](p4_final_checks.json) |

不同 suite 独立计数，不相加作为新验收数。完整后端/浏览器回归在同机并行执行；这不是新的 benchmark。回归开始后调整的 UI 仅为 V2 指标手机布局和错误区域的独立结果加载，最终 build、当前真实浏览器和生产扫描覆盖该收尾。没有重跑付费 AI 或正式 D_u 1912 步充当 P4 验收。

## 新运行和科学身份

- fast D_u：`463bf7f2-8143-483a-9db2-81559203771b`，64×16、478 步、T=.04、q_at=.396。六帧 × 六种字段；source Euler 的对照误差为 0，独立代数对照的浮点最大绝对差约 1.42×10⁻¹⁴；累计空间积分与标量 E 最大绝对误差约 1.11×10⁻¹⁶。
- custom：`bc8cc641-951f-493c-a484-cd6b6f4eb0c6`，128×32、956 步、T=.04、q_at=0，分类 CUSTOM_RUN。六帧字段/face 几何正确；at 的累计空间数组与 E_at 均为实际零。
- 三步 smoke：`d52d3af2-d880-42bc-9e69-648aa2bee249`，用于源积分器等价认证，不作为完整区间结果发布。
- 旧 P3 Run：`ea852646-72ce-40fc-b5f3-99329ff0895b`。可读本 Run 的真实字段/history/metrics/瞬时 Pi；累计空间分配返回 null + UNAVAILABLE + reason，没有用终态 Pi 或 V1 数据补齐。
- 新 fast 的终态 state hash `a8a8bbb4ef8ba37fb39856987ac5a0c5b84797d92d2d96c109e58512daf44cd9` 与上述旧 P3 fast 相同；P4 诊断扩展未改变完整 fast 演化。

新结果 hash 与方法、源清单、有效配置、Solver 摘要、快照和输出文件 hash 分别记录。结果页、Evidence 与 view-context 一致使用当前 Run 的结果 identity；不继承 FROZEN_PRODUCTION。科学定义及 hash 规则见 [定义文档](10_P4_SCIENTIFIC_RESULTS.md)。

## 交付

- `backend/models/v2/result.py`：完整科学结果、field/face、entropy/metrics/allocation、Evidence 与 view-context 的严格 DTO。
- `backend/postprocess/case8.py`：确定性保守变量派生、坐标/shape/time 保护、全步 RK history 核对、原生 face 几何、源 detector 指标定义及 availability；无科学源 import 或 V1 fallback。
- `backend/postprocess/allocation.py`：仅在原 observer stage 遍历累计 face 数据；snapshot 不累计；复用原源诊断和积分器，不维护另一套数值方法。
- worker 原子提交 `derived/cumulative_faces.npz` / `scientific_result.json`，保存软件/后处理版本与输出 hash；Manager 发布成功前继续复核产物。旧 Run 投影只读，不重写旧 provenance。
- 五条新增 typed API：result、evidence、snapshot field、instantaneous faces、view-context；保留 P3 Density API 和 V1 路由/schema。
- `/runs/:runId`：六变量与实际六帧、上一/下一/播放、URL 恢复、完整熵曲线、带定义的三项宏观指标、瞬时与累计 face 独立视图、区域统计、limits。
- `/runs/:runId/evidence`：独立身份、归一化/有效配置、方法/源码/软件/后处理/output hashes 和结论范围；指标证据链接指向该 Run。
- 当前 field/snapshot/region 同步到结构化上下文，区域 count/min/max/mean 在后端直接计算，供 P5 读取；不触发 AI。

## 首轮问题与修正

1. 首次 smoke `b4280aef-9b00-463e-92da-a494a34b98be` 在后处理严格校验中失败：把 config 的 JSON lists 作为 Python 对象交给 strict tuple 模型。修正为传入已验证模型实例，保留原失败 Run/log；后续新真实 smoke 和完整 fast/custom 均通过，没有改变输入协议。
2. 前端编译发现 V1 展示 UnitSpec 的必需字段以及 availability 词汇不同。投影明确提供 unit id/quantity，科学 UNAVAILABLE 映射到展示 MISSING，实际 value 保持 null。
3. 第一轮 V2 定向回归中 P1 测试仍断言全部 OUTPUT 未实现。保留 [首轮日志](p4_v2_tests.log)，更新为验证四项已交付 OUTPUT capability，继续断言 unsupported 不可执行；完整回归随后通过。未删除能力断言。
4. 首次手机检查发现长 detector 定义撑宽页面；在 V2 结果组件内调整换行和指标布局，最终 fast/custom/Evidence/legacy 在390px视口均无溢出。区域请求失败也与已有字段加载分开处理。
5. Playwright CLI 全局 npm cache 出现 rename 错误，改用工作区 `.cache/npm-p4` 和 CLI 入口，不修改用户全局 runtime；检查产物保存在 `output/playwright/`。初始 favicon404 与主动非法区域400是预期 HTTP 记录，没有观察到应用 JS 异常。

## 使用和复查

PowerShell 7 启动既有 backend/frontend；新建实验确认后运行，完成即进入科学结果。可从工作台打开现有完成 Run。AI 和报告尚未开放。

```powershell
./.venv/Scripts/python.exe -B -m pytest tests/v2_p4 -q
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p4_live
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p4_finalize
```

真实验收脚本需要没有其他活跃 manager，启动自己的端口并实际创建两次完整 CFD及一次显式 smoke；原始产物保留在忽略的 runtime。浏览器 CLI 与本轮临时服务均已关闭。下一阶段是 P5：基于这些结果/evidence/context 的 AI 解读与科研助手。

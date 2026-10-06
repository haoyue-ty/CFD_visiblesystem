# V2-P0 验收记录

开始日期：2026-10-02，验收日期：2026-10-03（Asia/Shanghai）。阶段范围：能力审计、契约设计、transport 扩展、runtime 隔离基础、V1 回归。不包含 P1 创建实验、P2 求解或后续 UI。

| P0 任务 | 产物 / 验收依据 |
| --- | --- |
| HEAD、差异、V1 标签与实施分支 | [04_BASELINE_REPORT.md](04_BASELINE_REPORT.md)；annotated tag 解析，原 HEAD 保留，codex/shockpath-v2 |
| 基线测试与构建 | 原始日志及错误归因、当前回归汇总见基线报告 |
| 源模块、依赖、协议、诊断清单+hash | [source_manifest.json](source_manifest.json)；37 文件静态 import 闭包/协议/参考驱动；目标 flux hash 匹配 V1 |
| epsilon / Gate / Reconstruction | [01_CAPABILITY_AUDIT.md](01_CAPABILITY_AUDIT.md)；两种扰动明确，epsilon 歧义且不开放、Gate 未支持、一阶固定 |
| Case / Parameter Capability Registry | 能力报告第 5 节；validation readiness 与 execution readiness 分开，P0 两者都尚未上线 |
| 归一化、profile 分类、Run 状态、缺失及错误 | [02_CONTRACTS.md](02_CONTRACTS.md)；完整协议和模板 lineage、hash、独立身份/来源 |
| JSON POST / 202 / SSE / HTML OpenAPI | catalog/openapi 实现 + tests/v2_p0；兼容默认，text 不经 Pydantic JSON，test routes 仍受一致性检查 |
| 科研写隔离、runtime 策略 | [03_SOLVER_BINDING.md](03_SOLVER_BINDING.md)、paths.py、完整 source audit、Windows junction tests |

**验收状态：P0 通过。** 完整后端回归 1387 passed / 1 skipped，最终 P0 suite 38 passed / 1 skipped，最终 transport + V1 bootstrap 58 passed / 1 skipped，前端 220 passed，构建和 V1 契约一致性均通过；symlink 权限项 skip 已明确记录，两个 Windows junction 项通过。完整源核查 27,843 文件 path/size/mtime_ns/hash 一致。

通过条件已满足：每个拟开放输入有 source symbol 或待实现阶段；V1 OpenAPI 和 types byte-identical；没有新增默认写科研目录的 solver 入口（P0 无 solver 执行入口）。每轮实际计数、初次基线干扰和修正依据见 [04_BASELINE_REPORT.md](04_BASELINE_REPORT.md)。

已明确的后续障碍不冒充 P0 已实现能力：SciPy/Matplotlib 依赖准备、动态网格/步长验证、q 系数显式映射、fast benchmark、完整有效配置、observer 输出落盘、worker/scheduler/SSE/report 服务全部留在对应后续阶段。P1 可从能力和契约设计开始，运行按钮必须持续关闭直到 P2/P3 验收。

本阶段没有新增生产 V2 API、没有伪运行进度、没有调用 AI、没有覆盖 V1 freeze 文档。无远程 push/部署。

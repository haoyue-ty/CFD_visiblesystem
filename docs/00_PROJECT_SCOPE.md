# ShockPath — V1 项目范围冻结

| 项目字段 | 冻结值 |
| --- | --- |
| 项目名 | ShockPath |
| 中文名称 | 面向多维可压缩流动的熵稳定耗散路径数字实验与可视分析平台 |
| 英文名称 | ShockPath — An Interactive Visual Analytics Platform for Identifiable Dissipation Pathways in Multidimensional Compressible Flows |
| 冻结版本 / 状态 | `V1_SCOPE_FREEZE` / `FROZEN` |
| 项目根目录 | `D:\Paper\passage6\ShockPath` |
| 本阶段 | Phase 0 — Project Scope Freeze；本文件只冻结范围，不启动 Phase 1 |

## 1. 科学基础与主张边界

本项目以现有 JCP 论文工作、真实 CFD 求解器 `cross_mode_ec_unified_v1`、已有实验及冻结证据为基础。研究对象是 **identifiable entropy-stable dissipation pathways**。解释链为：

`Parameter → Dissipation Pathway → Entropy Production → Trajectory-level Entropy Budget → Spatial Allocation → Discrete Modal Response → Macroscopic Flow Response`。

显式参数为 `q_aa`、`q_at`；主要通道为 `Π_bg`、`Π_aa`、`Π_at`；轨迹累计诊断量为 `E_bg`、`E_aa`、`E_at`。cross-mode 的结构是 **acoustic trigger → tangential output**，即 trigger space 与 output space 不同；它不意味着算子必须具有非对角模态耦合。`δ_t` 不进入 acoustic gate `J`，实际切向耗散仍依赖切向模态含量。背景、声学—声学、声学—切向通道在适用的固定可容许界面分解下各自具有非负熵产；`q_aa` 与 `q_at` 是显式可辨识的参数方向，不是全局最优系数或对非线性宏观量的独立旋钮。

严格一维失活适用于切向速度相等、切向输出为零的严格一维状态。近一维 `Π_at` / `E_at` 的近 `O(ε²)` 激活解释须满足平滑、有界、可容许状态族及对应实验协议，不可外推为任意扰动的统一规律。周期 Case 7 审计中，实际有限体积 RHS 的熵变量收缩与通道观察器的**半离散**预算达到浮点精度闭合；SSP-RK3 的全离散剩余随时间步细化，不能宣称精确的全离散熵恒等式。matched-budget gate 实验支持“近似相同总预算可有不同空间分配”；Fourier-Jacobian 实验支持“正熵产不等于所有模态均增强阻尼”。同一 pathway 在 Case 8 和 Mach 3 cylinder 中的分配与宏观响应依赖流动、几何和观测指标。因此 `pathway budget ≠ pathway allocation ≠ macroscopic consequence`。

**禁止扩大的主张：** universal shock stabilizer、universal carbuncle cure、`q_at` 越大越好、所有 Fourier mode 都更强阻尼、`D_u` 对所有问题优于 `B_u`、所有 benchmark 优于经典 flux、Mach-unbounded PSD 等同任意 Mach 已证明鲁棒。也不得声称全局最优参数、普遍平滑流无干扰、零计算开销、精确全离散熵恒等式、高阶或 3D 普适结论。Mach 10 剖面未在冻结上限内稳定，圆柱 B/D 宽度接近检测器下限，Case 8 的响应随指标而变，外部 flux 对比只提供协议限定的背景，不构成通用排名。

## 2. 产品定位与用户

V1 是基于真实 solver、冻结实验及已核验分析结果的**交互式科研数字实验 + 科学可视分析 + 可复现实验证据平台**。核心问题是“数值耗散从哪里来、作用到哪里、发生在哪里、如何影响模态和宏观流动”。

- **Explore Mode：** 面向竞赛评委、非 CFD 用户与科学传播。用短路径、可解释交互和明确的示意/真实数据标签理解机制；交互不得暗示未计算的参数结果。
- **Lab Mode：** 面向 CFD、数值计算用户及计算机设计大赛技术展示。选择真实实验、参数与配置，查看可追溯的熵预算、空间分配、谱分析及流动响应；只允许选择有证据支撑的组合。

V1 区分 **Replay Mode**（读取已完成的真实冻结实验）与 **Live Demo Mode**（后期经单独批准的小网格、短时、低成本演示）。大型生产实验不在网页现场重跑；本次冻结不运行任何求解任务。

## 3. 七个 V1 主模块

| 编号 | 模块 | V1 范围与必要约束 |
| --- | --- | --- |
| 01 | Mechanism Explorer | 从 interface state、background PSD kernel、acoustic gate `J`、acoustic/tangential output、entropy-scaled combination 到物理熵变量耗散的交互解释；显示 trigger/output 分离、`δ_t` 不入 gate、切向内容影响输出、strict 1D 失活及条件性 near-1D 激活。与论文机制 Fig. 1/2 对应；结构图标记 schematic。 |
| 02 | CFD Experiment Lab | 统一浏览已有真实 Case 8、Mach 3 Cylinder、Isentropic Vortex、Near-1D Mach 6 perturbation、Common Mach 6 discrete shock/Fourier 实验；可用参数视证据列出 `q_aa`、`q_at`、gate、CFL、`ε`、reconstruction；显式标注 Replay / Live、运行协议与数据可用性。Case 8 Replay 为 V1 核心，其他场景按七模块所需证据逐步接入。 |
| 03 | Entropy Ledger | 展示 `Π_bg/Π_aa/Π_at` 与 `E_bg(t)/E_aa(t)/E_at(t)`，同步真实 CFD field、瞬时熵产与轨迹累计量。显示半离散 `G(U)+D(U)≈0` 的协议、残差与精度，以及时间离散 `R(T)=ΔS(T)+E_obs(T)`；分清 stage-weighted observer、真实状态熵变、半离散与全离散，不做无数据支撑的装饰性 Sankey。 |
| 04 | Allocation Explorer | matched-budget gate 对比 Acoustic、Pressure、Ungated；呈现真实 `Π_at` 累计单元分配场、固定 shock window、归一化累计分配和窗内/窗外份额。现有冻结数据显示窗内约 99.8307%、99.1687%、89.2300%；这些只是来源提示，产品须从冻结数据加载并复核，不得把百分数硬编码为数据源。“matched”指近似匹配，三组 `E_at` 并非严格相等。 |
| 05 | Spectral Lab | 对共同 Mach 6 离散激波，展示 `ℓ=0…16`、`q_at=0/0.132/0.264/0.396` 的 spectral abscissa `α(ℓ,q_at)`；重点模式 `ℓ=1/4/8/12`，证据允许时显示 leading eigenmode、shock-localization fraction、线性/RK3 预测及短时非线性 CFD 增长率。必须展示方向不一致的模态位移，禁止宣称普遍阻尼或普遍稳定。 |
| 06 | Cross-flow Compare | 以 Case 8 与 Mach 3 Cylinder 比较相对 `E_at` budget、各自空间分配、shock/front region allocation、shock width、front RMS、高频指标。同图仅在定义、单位、网格、时间及掩膜可比时使用共同尺度；两例 front-region 定义不同，localization percentage 不作严格统一测度的直接排名。呈现同一 pathway 在不同流动中的不同分配和响应。 |
| 07 | Reproducibility Center | 展示 method name/hash、experiment config、grid、time integrator、原始证据索引、entropy logs、postprocess config、FREEZE 信息、SHA-256 与验证状态。每条正式结果可反向追溯到冻结输入；缺失项显示“待核验/不可用”，不得编造。 |

## 4. 优先级冻结

**P0 — V1 必须完成（10 项）：** ① Mechanism Explorer；② Case 8 Replay；③ Entropy Ledger；④ Gate Allocation Explorer；⑤ Spectral Lab；⑥ Case 8 / Cylinder Cross-flow Compare；⑦ Reproducibility Center；⑧ 基于真实实验数据的数据加载机制；⑨ Explore Mode 基本演示流程；⑩ Lab Mode 基本实验浏览流程。七个主模块是产品结构，P0 的十项是验收工作项，两者计数不可混同。

**P1 — 有时间再完成（7 项）：** 小网格 Live CFD、完整 Experiment Manager、自动参数扫描、数据导出、自动实验报告、更完整的 MUSCL transfer 页面、更完整的 external flux context。

**P2 — 计算机设计大赛 V2（10 项）：** 用户系统、数据库、后台任务队列、多实验并行计算、Solver plugin architecture、云端运行、自动生成分析报告、高阶格式扩展、更多 trigger-output pathway、更系统的参数设计功能。

P1/P2 不阻塞 V1，不能借 P1/P2 增加 P0 验收门槛。

## 5. Non-goals

V1 不建设通用 CFD 商业软件、通用网格生成器、任意 PDE 求解器、任意 CFD case 上传运行、大规模集群计算、任意 Riemann solver 自动生成、AI 自动发明 CFD 算法、在线训练模型、自动参数全局优化、3D CFD、全部实验实时在线重跑；不新增未经论文验证的大规模 scientific claim，不为比赛伪造结果。

## 6. 数据真实性与来源规则

**REAL DATA FIRST。** 正式结果按以下优先级取证：① frozen production data；② existing verified postprocessed data；③ 从已有 raw data 按可追溯协议重算的结果；④ 单独界定的小型 live solver demo；⑤ illustrative schematic。第⑤类必须显著标记 `schematic`，绝不可作为数值证据。任何展示应保留方法身份、运行配置、网格/时间、变量单位、掩膜/窗口定义、处理规则与 SHA-256；缺失来源时不显示未经核定的数值。不得从论文文字补造数据、由图像像素反推所谓原始数据、平滑原始科学场以制造结论，或把探索性/旧方法数据与最终修正方法混用。

已有 solver、`cross_mode_ec_unified_v1`、生产 CSV/JSON/NPY/NPZ、冻结实验和所有 FREEZE 目录均为 **READ-ONLY**。本次只新增 ShockPath 的范围与冻结记录；不修改、移动、重命名、删除科研资产，不重新标定 `q_aa/q_at`，不启动大型 CFD。

## 7. 比赛叙事与视觉原则

- **数媒大赛：** 科学数据可视化、交互式科研叙事、真实 CFD 数据驱动；“让复杂科研机制被看见。”重点为视觉、动画、交互、科学故事、机制理解和真实实验。
- **计算机设计大赛：** 同一底层项目，未来叙事为可复现实验、耗散归因与模态分析的软件平台；“让科研实验能够执行、分析与复现。”重点为软件工程、数据管理、solver 接口、实验管理、分析模块和 reproducibility。本阶段不按尚未公布的下一届赛制指定小类。

本阶段不设计正式 UI。视觉原则：白底、干净的科学界面、克制的学术语言和 CFD/科学计算风格；避免通用 SaaS 仪表盘、游戏化、赛博朋克、过量玻璃拟态和商业信息图。继承论文主色 `#F4F4F4`、`#C0E8F2`、`#81BBE0`、`#FFD6D6`、`#FF8887`。科学图优先清晰字体与坐标、可比较的共同尺度、准确的单位/图例；不得用误导动画或装饰性平滑改变科学含义。

## 8. 冻结的 Demo Story

1. 从 “How much dissipation?” 引出 “What triggers it?” 和 “Where does it act?”。
2. 通过已有证据中的 `q_at` 设置开启 cross-mode pathway，查看可测的 `E_at`。
3. 切换 matched-budget gate，理解近似相同 budget 可有不同 allocation。
4. 查看 Fourier spectrum，理解正熵产不保证所有 mode 更强阻尼。
5. 比较 Case 8 与 Cylinder，理解同一 pathway 在不同流动中的宏观响应并不相同。
6. 在 Reproducibility Center 追溯真实 solver、配置与冻结证据。

最终表达：**Dissipation magnitude alone is insufficient; trigger, output, allocation and dynamics must be distinguished.**

## 9. 开发顺序冻结

`Phase 0 Project Scope Freeze → Phase 1 Data Asset Inventory → Phase 2 PRD → Phase 3 User Flow + Information Architecture → Phase 4 Data Schema + API Contract → Phase 5 Low-fidelity Wireframes → Phase 6 Case 8 Vertical Slice → Phase 7 Design System + High-fidelity UI → Phase 8 Frontend / Backend Parallel Development → Phase 9 Live CFD Demo → Phase 10 Reproducibility Center → Phase 11 Competition Demo / Video / PPT / Documentation`。

Phase 6 必须先端到端跑通真实 Case 8 数据 → loader → backend API → frontend → entropy → allocation → metrics。禁止先完成全部 UI 再考虑数据和后端。上述顺序是后续规划；本次仅执行 Phase 0，**不开始 Phase 1**。

## 10. MVP 验收定义

V1 MVP 通过条件：P0 十项均有可演示的最小闭环；Explore 与 Lab 各有一条完整流程；Case 8 Replay 从真实冻结数据加载，能追溯输入与处理；Ledger 清楚区分瞬时、累计、半离散闭合和时间残差；Gate 对比使用同一冻结协议与可核定窗口，展示非同一空间分配；Spectral Lab 保留正反方向模态结果；Case 8/Cylinder 比较明确口径差异；Reproducibility Center 对所展示正式结果提供可检查的身份、配置和 hash。所有科学图保留单位、尺度、掩膜、协议及来源；缺证据时显示限制，而非生成替代结果。P1/P2 均不是 MVP 阻断项。

## 11. Change Control

冻结后不得无理由增加 P0。任何 P0 范围变更须先在 `CHANGELOG.md` 记录 `old scope`、`new scope`、`reason`、`impact`、`date`，并形成新版本冻结记录；不得静默修改本版文档。科学主张边界的扩展须有新的真实实验或理论证据及可追溯来源；文案、动画或评赛需要本身不构成证据。若要更新本文件，须重算 SHA-256、重建 manifest、保留旧版 hash/变更记录，并同步镜像副本。

## 12. 已核对的边界来源与 OPEN_QUESTIONS

本次仅做快速边界确认，未开展数据资产盘点。已只读参考 `README.md`、`final_corrected_evidence_freeze_v1/FINAL_CLAIM_HIERARCHY.md` 与 `FINAL_LIMITATIONS.md`、`final_corrected_evidence_freeze_v1/FINAL_METHOD_IDENTITY.md`、`manuscript_v1/M1_evidence_architecture/FIGURE_PLAN.md`、`experiments/entropy_budget_closure/experiment_report.md`、`experiments/gate_ablation/FREEZE/gate_ablation_analysis.csv`（并与现有分析 CSV/图审计说明核对）、`experiments/linear_perturbation_analysis/FREEZE/experiment_report.md`。这些路径均相对科研主目录 `D:\Paper\passage6`；完整逐文件可信性与可加载性留给 Phase 1。

**OPEN_QUESTIONS（不影响本次范围冻结）：**

1. Phase 1 需逐项核定七模块所需字段、原始数据粒度、冻结 hash、许可与可加载路径；当前文档不保证每个展示字段已具备生产级数据。
2. Near-1D Mach 6 与 Cross-flow Compare 的最终产品数据口径、可用时序场和对应证据入口需在 Phase 1 确认；不得据本范围文档补造缺失场。
3. Gate 消融使用 cell-center 累计分配窗口，早期 Case 8 J2 原生 face-based 定位另有定义；Phase 1 应明确并分别映射，不能混成同一百分比。
4. `Π_at` 空间图在 gate 消融中来自已累计、阶段加权的 `Pi_at.npy`，不是未经积分的瞬时场；界面标题和数据模式需在 PRD/Schema 阶段精确定义。
5. 目标镜像目录 `D:\code_project\CFD_visiblesystem` 仅保存本版冻结文件副本；后续是继续镜像文档还是成为软件工作目录，留待单独决定。

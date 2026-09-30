# ShockPath V1 产品需求文档（PRD）

## 0. 文档信息

- **项目名称**：ShockPath
- **中文名称**：面向多维可压缩流动的熵稳定耗散路径数字实验与可视分析平台
- **英文名称**：ShockPath — An Interactive Visual Analytics Platform for Identifiable Dissipation Pathways in Multidimensional Compressible Flows
- **文档版本**：V1.0
- **阶段**：Phase 2 — PRD
- **上游依据**：`V1_SCOPE_FREEZE` + `Phase 1 DATA_ASSET_INVENTORY`
- **开发策略**：Functionality First
- **前后端策略**：前端与后端同步开发，先做粗糙但可用的功能版，再进行视觉优化

---

# 1. 文档目的

本 PRD 用于定义 ShockPath V1 的产品目标、目标用户、模块功能、用户操作、数据约束、前端功能、后端能力、科学边界、错误状态与 MVP 验收标准。

本阶段不负责：

- 高保真 UI 设计；
- 最终 Design System；
- 精确 API 路径冻结；
- 数据库设计；
- 大型 Live CFD 运行；
- 新增科研结论。

后续开发顺序：

`PRD → User Flow + IA → Data Schema + API Contract → Functional Prototype → Case8 Vertical Slice → P0 Integration → Scientific Audit → UI/UX Polish`

---

# 2. 产品定义

ShockPath 不是论文网页，也不是通用 CFD 商业求解器。

它是：

> **以真实 CFD Solver 和冻结实验数据为内核，以科学可视分析为产品外壳的 CFD 数字实验、耗散归因、熵预算、空间分配、模态分析和可复现实验证据平台。**

核心机制链：

`Parameter → Dissipation Pathway → Entropy Production → Trajectory Budget → Spatial Allocation → Modal Response → Macroscopic Response`

核心价值不是只回答“流场是什么”，而是进一步回答：

- 数值耗散由什么触发；
- 作用到什么输出模态；
- 产生多少熵；
- 分配在哪里；
- 不同 Fourier 模态如何响应；
- 宏观流动为何产生不同结果。

---

# 3. V1 产品目标

V1 必须支持：

1. 理解 cross-mode pathway 的 trigger/output 分离；
2. 浏览真实 Case8 A/B/C/D；
3. 查看真实通道级 entropy history；
4. 比较 matched-budget gate 的空间分配；
5. 查看 Fourier spectral response；
6. 查看 Fig13 的线性/RK3/CFD 短时增长率验证；
7. 比较 Case8 与 Mach3 Cylinder；
8. 追溯方法、配置、数据来源和 hash；
9. 完成 Explore Mode 的竞赛展示流程；
10. 完成 Lab Mode 的实验浏览流程。

成功标准按优先级排序：

1. Scientific Correctness
2. Scientific Traceability
3. Data Integrity
4. Frontend–Backend Integration
5. Functional Completeness
6. Usability
7. Visual Polish

---

# 4. 开发策略

## 4.1 Functionality First

第一阶段优先：

- 数据正确；
- adapter 正确；
- 后端读取正确；
- 前端状态正确；
- 图表正确；
- 参数切换正确；
- 错误状态正确；
- 来源可追溯。

第一阶段不优先：

- 高级动画；
- 精致 Hero；
- 大量转场；
- Glassmorphism；
- 复杂 3D；
- 装饰性图形。

视觉优化统一放到 P0 功能完成后。

## 4.2 纵向切片开发

采用：

`一个模块的真实数据 → adapter → backend → frontend → 验收`

不采用：

`全前端做完 → 全后端做完 → 最后联调`

推荐顺序：

1. Case8 Replay
2. Entropy Ledger
3. Gate Allocation
4. Spectral Lab
5. Fig13 Validation
6. Cylinder / Cross-flow
7. Reproducibility
8. Mechanism
9. Explore Mode
10. Lab Mode

---

# 5. 用户类型

## 5.1 Explore Mode

面向：

- 数媒竞赛评委；
- 非 CFD 用户；
- 科学传播场景；
- 初学者。

目标：

> 快速理解“耗散从哪里来、作用到哪里、发生在哪里、如何改变模态和宏观响应”。

强调：

- 少公式负担；
- 机制清楚；
- 视觉叙事；
- 真实数据；
- 不隐藏限制。

## 5.2 Lab Mode

面向：

- CFD 用户；
- 数值计算学生；
- 科研评委；
- 计算机设计类评审。

用户可以：

- 选择已有实验；
- 查看合法配置；
- 查看数据可用性；
- 浏览真实 snapshot；
- 查看 entropy / allocation / spectrum；
- 查看 provenance。

不允许用户选择不存在的实验组合。

---

# 6. V1 产品结构

七个主模块：

1. Mechanism Explorer
2. CFD Experiment Lab
3. Entropy Ledger
4. Allocation Explorer
5. Spectral Lab
6. Cross-flow Compare
7. Reproducibility Center

两个入口：

- Explore Mode
- Lab Mode

---

# 7. 全局科学与数据规则

## 7.1 REAL DATA FIRST

正式结果优先级：

1. Frozen production data
2. Existing verified postprocessed data
3. Existing raw data + verified postprocess
4. Approved small Live Demo
5. Schematic illustration

Schematic 必须显式标记，不得作为数值证据。

## 7.2 禁止伪造参数结果

如果只有：

`q_at = 0 / 0.132 / 0.264 / 0.396`

UI 只能选择这四档。

禁止通过连续 slider 插值出 `q_at=0.2` 并伪装为真实科研结果。

## 7.3 时间播放必须忠于真实采样

Case8：

- 1912 accepted-step scalar history；
- A/B/C/D 每组 6 个真实空间 snapshot；
- 没有 1912 步 full state；
- 没有完整 RK stage spatial field。

因此：

- scalar timeline 可以细；
- flow field 只能显示 6 个真实帧；
- 不能生成假中间帧。

Cylinder：

- 9757-step scalar histories；
- 5 个真实 instantaneous-face snapshot；
- 无完整 trajectory cumulative spatial map。

## 7.4 科学语义必须分开

不得混用：

- instantaneous Pi_at
- stage-weighted contribution
- trajectory-integrated Pi_at
- E_at
- gate shock-window fraction
- Case8 face localization
- Cylinder front-band fraction
- Cylinder angular allocation
- spectral abscissa
- modal growth rate
- front RMS
- HF / HF-RMS
- Case8 width
- Cylinder width

不同 mask、不同 detector、不同 scope 的数值不得统一排名。

---

# 8. Module 01 — Mechanism Explorer

## 8.1 目标

解释：

- acoustic trigger；
- normal acoustic output；
- tangential output；
- trigger/output separation；
- strict 1D inactivity；
- weakly multidimensional activation。

## 8.2 前端功能

第一版至少包含：

- Interface State；
- Background PSD；
- Acoustic Gate J；
- Acoustic Output；
- Tangential Output；
- Entropy-scaled Combiner；
- Physical Entropy Variable Output。

用户可以：

- 切换 `q_at = 0 / enabled`；
- 切换 `Strict 1D / Weakly 2D`；
- 查看 pathway active/inactive。

第一版允许普通框图，不要求高级动画。

## 8.3 数据限制

Near-1D 五档 epsilon raw evidence 缺失。

因此允许：

- 理论机制；
- strict-1D schematic；
- weakly-2D schematic。

禁止：

- 五档 epsilon 数值交互；
- 使用论文抄录数值作为正式后端数据。

## 8.4 验收

- 用户可以理解 trigger ≠ output；
- strict 1D 时 tangential output 明确为零；
- schematic 标签明确；
- 不使用 unsupported near-1D scan。

---

# 9. Module 02 — CFD Experiment Lab

## 9.1 目标

建立真实实验统一浏览入口。

## 9.2 V1 正式支持优先级

### Tier A

- Case8 A_u
- Case8 B_u
- Case8 C_u
- Case8 D_u
- Gate ablation
- Entropy closure
- Spectrum
- Fig13 modal validation

### Tier B

- Mach3 Cylinder
- MUSCL final-state context
- External flux context

### 暂不正式开放

- Near-1D five-epsilon numerical scan

## 9.3 Case8 配置

| Config | q_aa | q_at |
| --- | ---: | ---: |
| A_u | 13.2 | 0 |
| B_u | 3.96 | 0 |
| C_u | 13.2 | 0.396 |
| D_u | 3.96 | 0.396 |

## 9.4 Case8 Replay

必须支持：

- 4 个 configuration；
- 每组 6 个真实 snapshot；
- density；
- pressure；
- front；
- actual snapshot time；
- width / RMS / HF 等可用 metric。

UI 必须写：

`Snapshot 1/6 ... 6/6`

允许播放 6 个保存帧，但应标记：

> Discrete recorded snapshots

## 9.5 后端能力

需要：

- experiment registry；
- config loader；
- snapshot loader；
- metric loader；
- availability metadata。

前端不得直接访问科研目录。

## 9.6 验收

- A/B/C/D 均正确加载；
- 时间取真实 NPZ；
- 不出现不存在参数组合；
- 缺失值显示 unavailable，不填 0。

---

# 10. Module 03 — Entropy Ledger

## 10.1 目标

把 numerical dissipation 表达为可追踪的通道级熵预算。

核心量：

- Pi_bg
- Pi_aa
- Pi_at
- E_bg(t)
- E_aa(t)
- E_at(t)

并展示：

- Semi-discrete closure
- Fully-discrete residual

## 10.2 Case8 功能

真实支持：

- 1912-step scalar history；
- E_bg/E_aa/E_at；
- stage aggregate；
- 6 个 endpoint spatial snapshot；
- D_u trajectory-integrated spatial map；
- 无 per-step full flow field；
- 无全 RK-stage spatial fields。

## 10.3 前端功能

第一版：

- Case/Config selector；
- CFD Snapshot；
- Entropy Summary；
- E_bg/E_aa/E_at 曲线；
- time cursor。

规则：

- scalar time cursor 可以按真实 step；
- field 自动吸附到最近真实 snapshot；
- 同时显示：
  - selected scalar time
  - displayed snapshot time

不得伪装为 dense synchronized trajectory。

## 10.4 Entropy Closure

支持：

- CFL selector；
- G(U)；
- D(U)；
- R_SD；
- eps_SD；
- R(T)。

必须明确区分：

- Semi-discrete closure
- Fully-discrete residual

## 10.5 禁止

- 假 spatial-stage movie；
- 把 E_*_step 直接称 cumulative；
- 宣称 exact fully-discrete entropy identity；
- 用其他实验的空间场补缺失 trajectory。

## 10.6 验收

- B_u zero-channel 正确；
- D_u channel 正确；
- stage/step 不混淆；
- snapshot mapping 正确；
- closure 数量级与冻结证据一致。

---

# 11. Module 04 — Allocation Explorer

## 11.1 目标

核心信息：

> **Same budget ≠ Same spatial allocation**

## 11.2 支持 Gate

只允许：

- Acoustic
- Pressure
- Ungated

matched q_at 从冻结 metadata 加载。

## 11.3 数据语义

Pi_at.npy：

- 32×128；
- trajectory-integrated；
- cell-centered；
- 已包含正确积分约定；
- `sum(array) = E_at`；
- 不再额外乘 dt 或面积。

## 11.4 前端功能

必须支持：

- Gate selector；
- three-map compare；
- single-map focus；
- shared spatial extent；
- shared color scale；
- shock window overlay；
- inside/outside fraction；
- cumulative allocation curve；
- E_at summary。

## 11.5 标签

必须写：

> Trajectory-integrated allocation

matched budget 写：

> approximately matched total E_at

## 11.6 禁止

- 连续 q_at slider；
- gate 间插值；
- 把 99.83/99.17/89.23 做性能排名；
- 不同 color scale；
- 混用 cell mask 与 face mask。

## 11.7 验收

- 三 map 正确；
- map sum 与 E_at 对应；
- shock window 正确；
- fraction 正确；
- shared scale；
- 不出现 winner 文案。

---

# 12. Module 05 — Spectral Lab

## 12.1 目标

核心信息：

> **Positive entropy production ≠ Uniform modal damping**

## 12.2 数据支持

真实支持：

- q_at = 0 / 0.132 / 0.264 / 0.396；
- ell = 0...16；
- 68 spectral records；
- 每 block 512 eigenvalues；
- 32 left/right eigenvectors；
- fixed shock mask；
- 24×33 Fig13 histories。

## 12.3 Spectral Overview

主图：

`ell → spectral abscissa alpha`

用户可以：

- 切换 q_at；
- 比较四条曲线；
- 点击 mode；
- 查看 alpha；
- 查看 delta alpha；
- 查看 mode detail。

## 12.4 Mode Detail

至少支持：

- ell=1
- ell=4
- ell=8
- ell=12

显示：

- alpha；
- eigenvalue info；
- right eigenmode；
- shock mask；
- localization fraction；
- q_at comparison。

必须保留：

- left shift；
- right shift；
- near-zero shift。

不得给所有 mode 打“improved”标签。

## 12.5 Eigenmode Viewer

第一版可显示：

- real part；
- magnitude；
- primitive profile；
- fixed normalization。

如提供 phase 动画，必须标注：

> Eigenmode phase visualization

不得称为真实 CFD evolution。

## 12.6 Fig13 Validation

支持：

- mode 1/4/8/12；
- q_at 0/0.396；
- epsilon 1e-4/1e-5/1e-6；
- 24 runs；
- 每组 33 points。

显示：

- modal amplitude；
- log amplitude；
- sigma_LIN；
- sigma_RK3；
- sigma_CFD；
- relative discrepancy；
- fit window；
- R²。

可播放真实 33-point amplitude，但不能伪造 spatial movie。

## 12.7 验收

- 68 spectra 完整；
- 四档 q_at 仅使用真实数据；
- mixed-sign response 保留；
- mode16 等不改善结果仍可见；
- 24 histories 正确；
- relative error 按 fraction 语义正确。

---

# 13. Module 06 — Cross-flow Compare

## 13.1 目标

核心信息：

> Same pathway + Different flow → Different allocation + Different response

## 13.2 比较对象

- Case8
- Mach3 Cylinder

## 13.3 数据不对称原则

Case8 可展示：

- D_u trajectory-integrated spatial Pi_at；
- shock-window localization；
- budget；
- width；
- RMS；
- HF。

Cylinder 可展示：

- 5 instantaneous face snapshots；
- 16 cumulative angular sectors；
- fixed front-band cumulative fraction；
- budget；
- width；
- RMS/HF-RMS。

Cylinder 不存在 full-trajectory cumulative 2D Pi_at heatmap。

因此 V1 不做伪对称热图。

## 13.4 推荐页面结构

### Case8

- cumulative spatial allocation；
- window overlay；
- budget；
- width/RMS/HF。

### Cylinder

- curved shock snapshot；
- 16-sector allocation；
- front-band scalar；
- budget；
- width/RMS/HF-RMS。

### Shared Summary

`Pathway budget ≠ allocation ≠ macroscopic consequence`

## 13.5 禁止比较

不得直接统一排名：

- Case8 shock-window fraction vs Cylinder front-band fraction；
- Case8 HF vs Cylinder HF-RMS；
- detector-floor 附近 width；
- 不同 scope 的 raw E_at。

## 13.6 验收

- 两类数据定义清楚；
- 不伪造 Cylinder heatmap；
- 16 sector 正确；
- band 标记 cumulative；
- scope metadata 可见。

---

# 14. Module 07 — Reproducibility Center

## 14.1 目标

证明每项正式结果都有真实科研证据链。

## 14.2 前端内容

每个实验可查看：

- method；
- method hash；
- case；
- config；
- q_aa；
- q_at；
- gate；
- grid；
- CFL；
- final time；
- integrator；
- source file；
- data status；
- freeze status；
- SHA-256；
- limitations。

## 14.3 状态

使用：

- FROZEN_VERIFIED
- VERIFIED_NOT_FROZEN
- DERIVED_VERIFIED
- AVAILABLE_UNVERIFIED
- PARTIAL
- LEGACY
- SUPERSEDED
- MISSING
- NOT_APPLICABLE

## 14.4 禁止

- AVAILABLE_UNVERIFIED 显示成 verified；
- 隐藏 source drift；
- legacy 混入 production；
- 仅凭文件名判断 method identity。

## 14.5 验收

任意正式结果至少能追溯到：

`method + config + source + verification state`

---

# 15. Explore Mode

## 15.1 固定故事

1. How much dissipation?
2. What triggers it?
3. Where does it act?
4. Trigger ≠ Output
5. Same budget ≠ Same allocation
6. Positive entropy production ≠ Uniform modal damping
7. Same pathway ≠ Same macroscopic response
8. Real solver / config / hash / freeze

## 15.2 要求

- 每屏一个主结论；
- 可以顺序点击“继续”；
- 可跳转 Lab；
- 不隐藏限制；
- 不需要理解全部公式即可完成体验。

---

# 16. Lab Mode

用户流程：

`Experiment → Config → Data availability → Analysis → Provenance`

参数控件必须来自真实 registry。

不支持组合：

- disabled；
- 显示原因；
- 不调用假结果。

---

# 17. 数据适配层

科研源：

`D:\Paper\passage6`

前端不得直接读取。

Adapter 负责：

- 读取科研格式；
- 转换 schema；
- 坐标映射；
- complex serialization；
- 保留 method；
- 保留 source；
- 保留 unit；
- 保留 mask；
- 保留 status；
- 保留 hash。

Adapter 不得：

- 修改原科研数据；
- 插值出新实验；
- 自动修复证据；
- 猜测缺失字段。

---

# 18. 功能与错误状态

## Loading

显示明确 loading 状态。

## Missing

例如：

> Full trajectory spatial map is not available for this experiment.

## Unsupported

例如：

> This parameter combination was not part of the verified experiment set.

## Partial

例如 Cylinder：

> Spatial cumulative field unavailable. Sector-level cumulative allocation is shown instead.

## Legacy

例如：

> Historical / superseded evidence. Not used for current production claims.

不得用空白图代替这些状态。

---

# 19. 非功能需求

## 19.1 科学正确性

正式数值必须来自 backend data source。

禁止在前端把正式科研结果作为唯一硬编码常量。

## 19.2 可追溯性

每个正式 visualization 必须能取得：

- asset；
- experiment；
- method；
- config；
- status。

## 19.3 性能

V1 要求：

- metadata 秒级；
- scalar chart 秒级；
- 2D field 不应长时间卡死；
- 大 NPZ 经 adapter 转换；
- 浏览器不直接加载全部 2337 资产。

## 19.4 科研目录安全

科研源只读。

禁止 delete / rename / overwrite / modify FREEZE。

---

# 20. 数据发布策略

不把 2337 个资产全部打包到前端。

后续 Data Schema 阶段建立 curated release bundle，例如：

```text
release_data/
  registry/
  case8/
  gate/
  entropy/
  spectral/
  validation/
  cylinder/
  provenance/
```

本 Phase 2 不生成 bundle。

---

# 21. Live Demo 策略

Live Demo 属于 P1。

候选：

- small periodic vortex；
- small Case8；
- short selected modal validation。

不建议：

- matched gate live；
- full Fourier eigensystem live；
- Mach3 Cylinder live；
- MUSCL production live。

Live 结果必须标记：

> Demo run, not the frozen production evidence.

---

# 22. P0 验收

## P0-01 Mechanism Explorer

- trigger/output separation 正确；
- strict-1D inactivity 正确；
- schematic 标记明确；
- 不使用 unsupported near-1D raw scan。

## P0-02 Case8 Replay

- A/B/C/D 可加载；
- 每组 6 个真实 snapshot；
- actual time 正确；
- 不生成中间假帧。

## P0-03 Entropy Ledger

- E_bg/E_aa/E_at history 正确；
- scalar 与 snapshot timeline 区分；
- closure stage/step 正确；
- 不承诺 dense spatial stage replay。

## P0-04 Allocation Explorer

- 三 Gate 正确；
- frozen maps 正确；
- shared scale；
- window 正确；
- fraction 正确；
- 不做 winner ranking。

## P0-05 Spectral Lab

- 68 spectra；
- mode selection；
- mixed-sign response；
- eigenmode；
- 24×33 validation。

## P0-06 Cross-flow

- Case8/Cylinder 真实数据；
- sector/band 正确；
- 无伪造 Cylinder heatmap；
- 不统一排名不兼容指标。

## P0-07 Reproducibility

- method/config/hash/status 可追溯；
- missing/legacy/source drift 可见。

## P0-08 Real Data Loading

- frontend 不直接读科研目录；
- backend adapter 加载 canonical evidence；
- formal values 不在前端硬编码。

## P0-09 Explore Mode

完整跑通：

`Mechanism → Allocation → Spectrum → Cross-flow → Reproducibility`

## P0-10 Lab Mode

完整跑通：

`Experiment → Config → Data → Analysis → Provenance`

---

# 23. Functional Alpha

满足以下条件后定义为：

**ShockPath Functional Alpha**

- Case8 registry；
- A/B/C/D；
- 6 snapshot replay；
- Entropy history；
- Gate Allocation；
- Spectrum；
- Modal Validation；
- Cylinder sector comparison；
- Provenance；
- 前后端真实联动。

视觉可以粗糙。

---

# 24. Beta

满足：

- P0 全部通过；
- 关键数据交叉核验；
- 错误状态；
- Explore flow；
- Lab flow；
- 基础 usability。

定义为：

**ShockPath Beta**

---

# 25. Competition Release

Beta 后才做：

- Design System；
- 高保真 UI；
- 动画；
- Hero；
- transition；
- responsive；
- Demo Mode；
- 比赛视频；
- PPT；
- 技术说明书。

---

# 26. 数据缺口与产品决策

| 数据缺口 | V1 决策 |
|---|---|
| Near-1D five-epsilon raw evidence missing | 不进入正式 numerical interaction |
| Cylinder cumulative 2D Pi_at missing | 使用 sector + band |
| Case8 per-step full fields missing | 使用 6-frame snapshot replay |
| Case8 all-config accumulated maps missing | D_u 可展示，其余不伪造 |
| persisted Jacobian/Fourier matrices missing | 使用 frozen spectra/eigenpairs |
| MUSCL spatial Pi_at missing | P1，仅终态/summary |

---

# 27. 禁止扩大科研主张

V1 不得宣传：

- universal shock stabilizer；
- universal carbuncle cure；
- q_at 越大越好；
- D_u 对所有问题更优；
- 所有 Fourier mode 更强阻尼；
- 正熵产等价于稳定；
- 某 matched gate 普遍最优；
- Case8 与 Cylinder localization percentage 可严格统一排名；
- Mach-unbounded PSD 已证明任意 Mach 鲁棒；
- MUSCL transfer 等于普适高阶证明；
- exact fully-discrete entropy identity。

---

# 28. 第一开发切片

## Case8 Functional Slice V0.1

必须跑通：

```text
Scientific Source
→ Case8 Adapter
→ Backend
→ Frontend
→ Config Selector
→ 6 Snapshot Replay
→ Entropy History
→ Metrics
```

第一版不要求漂亮。

验收重点：

- data 对；
- config 对；
- time 对；
- metric 对；
- source 对；
- frontend/backend 联通。

---

# 29. 下一阶段

Phase 3：

`03_USER_FLOW_AND_IA.md`

定义：

- route tree；
- Explore flow；
- Lab flow；
- page hierarchy；
- navigation；
- state transitions。

Phase 4：

- `04_DATA_SCHEMA.md`
- `05_API_CONTRACT.md`

之后进入：

**Frontend + Backend Functional Prototype**

---

# 30. PRD 冻结建议

本 PRD 经确认后可冻结为：

`V1_PRD_FREEZE`

建议冻结字段：

```text
PRD_VERSION=V1.0
PROJECT=ShockPath
SCOPE_SOURCE=V1_SCOPE_FREEZE
DATA_SOURCE=PHASE1_DATA_ASSET_INVENTORY
DEVELOPMENT_STRATEGY=FUNCTIONALITY_FIRST
FRONTEND_BACKEND=PARALLEL_BY_VERTICAL_SLICE
P0_MODULES=7
P0_WORK_ITEMS=10
NEW_SCIENTIFIC_RUNS_REQUIRED=NO
UNSUPPORTED_DATA_INTERPOLATION=FORBIDDEN
FRONTEND_FORMAL_VALUES_HARDCODED=FORBIDDEN
NEXT_PHASE=USER_FLOW_AND_INFORMATION_ARCHITECTURE
```

---

# 31. 最终产品定义

ShockPath V1 最终定义：

> **以科学可视分析为产品外壳、以真实 CFD Solver 和冻结实验为计算与证据内核的科研数字实验平台。**

开发原则：

> **功能优先、科学正确性优先、前后端同步、视觉优化后置。**

V1 不依赖新增大型 CFD 实验才能成立。

# ShockPath — Phase 1 DATA ASSET INVENTORY

审计时间：2026-09-30T21:53:25+08:00（Asia/Shanghai）。冻结范围：`V1_SCOPE_FREEZE`。

## 1. Executive Summary

本阶段完成 inventory + evidence mapping，不开展PRD、UI/API、前后端、数据库或CFD。按用户最新指定，所有产物保存在 `D:\比赛\数媒\data`，取代粘贴任务中的默认docs输出位置。科研证据根 `D:\Paper\passage6` 全程只读；Phase0四份文件保持原hash。

**DATA_ASSET_INVENTORY=PASS** 表示盘点与缺口审计通过，不表示产品已实现或所有科研证据齐全。P0的数据支持结果为 **8项支持（含adapter）、2项部分支持、0项整体阻塞**。Ledger与Cross-flow仍有明确的空间/时间功能缺口；V1可降级表达，不静默扩充或修改冻结范围。累计Cylinder heatmap及每步同步流场若被要求为强制验收功能，需先解决缺口/范围变更。

既有文件资产2329个，MISSING逻辑资产8项；一个文件是一项资产，NPZ成员逐个记录shape/dtype，冻结与工作副本可能分别计数。包含配置、科学定义、分析、图形和历史记录，**资产数不等于运行数或可发布数据数**。机器文件列出全部记录和精确路径；本报告突出权威入口与产品约束。

重要发现：Gate累计cell图真实、hash匹配且积分一致；谱68组合及Fig13的24×33真实时序完整；Case8每配置六帧流场且终态与J2B逐值一致。近期已有D_u累计空间场冻结（DIAGNOSTIC_RERUN）可用，本阶段没有重跑。Near1D五档ε图表源自论文抄录，应暂不作为产品数值来源。Cylinder `spatial_cumulative.npz` 是16角向累计箱+band标量，不是full spatial map。

## 2. Source Roots

| Root | Role | Treatment |
| --- | --- | --- |
| D:\Paper\passage6 | 科研证据源 | READ-ONLY |
| D:\code_project\CFD_visiblesystem | 软件主目录和Phase0镜像 | 只读核验本阶段；未创建软件工程 |
| D:\Paper\passage6\ShockPath | Phase0原始冻结位置 | 未修改 |
| D:\比赛\数媒\data | Phase1 inventory输出 | 仅新增盘点文档、索引、审计/冻结记录与只读检查脚本 |


优先根：`experiments/entropy_budget_closure`、`experiments/gate_ablation/FREEZE`、`experiments/linear_perturbation_analysis/FREEZE`、J2B Case8、J2C-v2 Cylinder、J2D-v3 Case7、J3/J4/J12、corrected production、MUSCL freeze、外部baseline canonical/raw。历史版本只用于身份排除与追溯，不承接正式主线。

## 3. Scientific Identity Rules

最终方法 `cross_mode_ec_unified_v1` 的当前source SHA256为 `98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0`，与要求的身份hash一致。A_u=(13.2,0)、B_u=(3.96,0)、C_u=(13.2,.396)、D_u=(3.96,.396)，是工作参数，不是全局最优。Gate Acoustic=.4、Pressure=.31018332312583474、Ungated=.03483470441226932属于另行冻结的matched gate协议，不能替换D_u=.396。

身份须以配置/来源/协议/hash联合确认。文件名、尺寸、`method_id='D_u'`字符串、论文图号都不足以证明方法一致。外部baseline的`original/proposed`行是历史内部架构，不替换最终A_u/B_u/D_u。源码hash漂移与冻结数值文件hash一致必须分别记录。

状态仅使用任务指定九类。`FROZEN_VERIFIED`表示至少一条既有freeze/result-hash记录与本次逐字节hash一致、格式可读；不等同重新证明全部科学结论。`VERIFIED_NOT_FROZEN`可表示明确字节相同的冻结副本或具体轻量审计通过但未找到上游逐文件冻结记录。Case8 checkpoint另行验证有限density/pressure、时间表和终态逐值相等，不宣称重算验证中间轨迹。`AVAILABLE_UNVERIFIED`默认不列入正式产品可用数据，图像只属figure-only。

## 4. Inventory Method

递归枚举16567个文件（排除环境、cache、Git、Superpowers等目录），选取2329个相关文件逐项SHA256、文本/JSON和CSV检查。未选中的大量历史镜像保留在source_tree索引，不宣称逐项审计。NPY使用header；NPZ用ZIP流逐成员读取header，仅读取小标量和选定小型核验数组，未全量解压或复制大型数组。CSV流式获取header、rows、字段类型、时间/参数范围、首末行；不会执行科学实现。所有UNKNOWN显式保留，单位无SI映射不猜。

Phase0 manifest三条hash通过；method source hash通过。既有hash引用审计结果：{'MATCH': 1874, 'MISMATCH': 18, 'UNRESOLVED_REFERENCE': 1}。hash引用数含不同manifest对同一文件的重复引用，不等于资产数。详见 `hash_verification.json`；function-level hash只记录为不可用whole-file验证。本阶段不修复任何hash或数据。

轻量核验见 `evidence_validation.json`：3 Gate map sum vs E_at均<1e-10；谱恰为17×4=68组合；Fig13 24条history各33点且时间递增；Case8 4×6 checkpoint时间/有限场及终态相等。外部四方法width和独立canonical表精确相等见 `external_context_validation.json`。

## 5. Module-by-module Inventory

### 01 Mechanism Explorer

REQUIRED_ASSETS：Final flux/operator identity；J/gate and output decomposition；Strict-1D/near-1D conditions。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`solver/fluxes/cross_mode_ec_unified_v1.py`](<D:\Paper\passage6\solver\fluxes\cross_mode_ec_unified_v1.py>) | asset_a0548b71ae83 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`jcp_extension_v1/J1_entropy_channel_theory/J1_IMPLEMENTATION_AUDIT.md`](<D:\Paper\passage6\jcp_extension_v1\J1_entropy_channel_theory\J1_IMPLEMENTATION_AUDIT.md>) | asset_8fe8e8d14264 | VERIFIED_NOT_FROZEN | SUMMARY_ONLY |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2A_DIAGNOSTIC_DESIGN.md`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2A_DIAGNOSTIC_DESIGN.md>) | asset_321c7aa318c8 | AVAILABLE_UNVERIFIED | NOT_USABLE |

MISSING_ASSETS：missing_near1d_raw_epsilon_scan。

OPTIONAL_ASSETS：Verified small interface-state table; illustrative schematic must be labelled。

### 02 CFD Experiment Lab

REQUIRED_ASSETS：Case8 configurations + field snapshots + temporal metadata；Available real case/configuration registry。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\J2B_PROTOCOL_LOCK.json>) | asset_8d15c3f16f95 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/final_state.npz`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs\case8_D_u\final_state.npz>) | asset_6ff7edcc7de2 | FROZEN_VERIFIED | POSTPROCESS_REQUIRED |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/J2C_V2_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\J2C_V2_PROTOCOL_LOCK.json>) | asset_20d838d92e6a | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`experiments/entropy_budget_closure/config.json`](<D:\Paper\passage6\experiments\entropy_budget_closure\config.json>) | asset_5c4aeaba111b | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`experiments/linear_perturbation_analysis/FREEZE/config.json`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\config.json>) | asset_99701f5ec82d | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`corrected_physics_reproduction_v1/case8/03_case8_A_u/checkpoints/step_000000.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints\step_000000.npz>) | asset_f661621c298c | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/03_case8_A_u/checkpoints/step_000382.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints\step_000382.npz>) | asset_0d9e3b382a3d | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/03_case8_A_u/checkpoints/step_000765.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints\step_000765.npz>) | asset_e311ebcc6ca5 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/03_case8_A_u/checkpoints/step_001147.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints\step_001147.npz>) | asset_b1cdee2d84cf | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/03_case8_A_u/checkpoints/step_001530.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints\step_001530.npz>) | asset_b1bfc6f87f56 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/03_case8_A_u/checkpoints/step_001912.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\03_case8_A_u\checkpoints\step_001912.npz>) | asset_3b7d903c22f8 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/04_case8_B_u/checkpoints/step_000000.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints\step_000000.npz>) | asset_8b4f30579573 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/04_case8_B_u/checkpoints/step_000382.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints\step_000382.npz>) | asset_5e3098898c99 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/04_case8_B_u/checkpoints/step_000765.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints\step_000765.npz>) | asset_e894deed7c59 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/04_case8_B_u/checkpoints/step_001147.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints\step_001147.npz>) | asset_0741bf5f547c | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/04_case8_B_u/checkpoints/step_001530.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints\step_001530.npz>) | asset_67de9e154164 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/04_case8_B_u/checkpoints/step_001912.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\04_case8_B_u\checkpoints\step_001912.npz>) | asset_cf255d76e818 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/06_case8_C_u/checkpoints/step_000000.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints\step_000000.npz>) | asset_701f2a4c8e26 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/06_case8_C_u/checkpoints/step_000382.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints\step_000382.npz>) | asset_4ca5907c1463 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/06_case8_C_u/checkpoints/step_000765.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints\step_000765.npz>) | asset_ac0331cdafd2 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/06_case8_C_u/checkpoints/step_001147.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints\step_001147.npz>) | asset_c5fb8726078c | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/06_case8_C_u/checkpoints/step_001530.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints\step_001530.npz>) | asset_1541b96d3943 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/06_case8_C_u/checkpoints/step_001912.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\06_case8_C_u\checkpoints\step_001912.npz>) | asset_ff68c9d21b50 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_000000.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints\step_000000.npz>) | asset_6e5faf0f34c7 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_000382.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints\step_000382.npz>) | asset_77fd98155a34 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_000765.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints\step_000765.npz>) | asset_c04e3aff0866 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_001147.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints\step_001147.npz>) | asset_cf7e7f4878bb | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_001530.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints\step_001530.npz>) | asset_831e53c374b6 | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |
| [`corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_001912.npz`](<D:\Paper\passage6\corrected_physics_reproduction_v1\case8\05_case8_D_u\checkpoints\step_001912.npz>) | asset_f4323c28384b | VERIFIED_NOT_FROZEN | ADAPTER_REQUIRED |

MISSING_ASSETS：missing_near1d_raw_epsilon_scan、missing_case8_per_step_state。

OPTIONAL_ASSETS：MUSCL transfer；external reference fields after identity audit；future small Live demo。

### 03 Entropy Ledger

REQUIRED_ASSETS：E_bg/E_aa/E_at per accepted step；Instantaneous spatial rates at saved times；Case7 G+D and fully-discrete residual。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/stage_weighted_history.csv`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs\case8_D_u\stage_weighted_history.csv>) | asset_0a3f2155fa2b | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/snapshots/native_faces_step_001912.npz`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs\case8_D_u\snapshots\native_faces_step_001912.npz>) | asset_4866864395cc | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`experiments/entropy_budget_closure/outputs/Du_cfl_005/stage_closure.csv`](<D:\Paper\passage6\experiments\entropy_budget_closure\outputs\Du_cfl_005\stage_closure.csv>) | asset_b3904064f3d6 | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`experiments/entropy_budget_closure/outputs/Du_cfl_005/step_closure.csv`](<D:\Paper\passage6\experiments\entropy_budget_closure\outputs\Du_cfl_005\step_closure.csv>) | asset_b8418588583c | FROZEN_VERIFIED | ADAPTER_REQUIRED |

MISSING_ASSETS：missing_case8_per_stage_spatial_fields、missing_cylinder_trajectory_spatial_pi_at。

OPTIONAL_ASSETS：D_u frozen accumulated spatial map；B_u zero-channel and D_u CFL sequence。

### 04 Allocation Explorer

REQUIRED_ASSETS：Matched gate q_at and summary；Cumulative cell maps；Exact fixed cell window and sum convention。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`experiments/gate_ablation/FREEZE/gate_ablation_analysis.csv`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\gate_ablation_analysis.csv>) | asset_513157e8d9c4 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`experiments/gate_ablation/FREEZE/calibration_snapshot/matched_qat.json`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\calibration_snapshot\matched_qat.json>) | asset_aef55f8d1d5a | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`experiments/gate_ablation/FREEZE/results_snapshot/Acoustic/Pi_at.npy`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\results_snapshot\Acoustic\Pi_at.npy>) | asset_a11ef6fc4e6e | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`experiments/gate_ablation/FREEZE/results_snapshot/Pressure/Pi_at.npy`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\results_snapshot\Pressure\Pi_at.npy>) | asset_6850b4bab5cc | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`experiments/gate_ablation/FREEZE/results_snapshot/Ungated/Pi_at.npy`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\results_snapshot\Ungated\Pi_at.npy>) | asset_4dce11517608 | FROZEN_VERIFIED | ADAPTER_REQUIRED |

MISSING_ASSETS：核心已要求资产未发现缺项。

OPTIONAL_ASSETS：qat_sweep; not arbitrary interpolation。

### 05 Spectral Lab

REQUIRED_ASSETS：Common zero-residual base；68 alpha records；Selected leading modes and fixed mask；24 nonlinear validation histories。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`experiments/linear_perturbation_analysis/FREEZE/base_state/base_state.npz`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\base_state\base_state.npz>) | asset_6c6b9c35c1dc | FROZEN_VERIFIED | POSTPROCESS_REQUIRED |
| [`experiments/linear_perturbation_analysis/FREEZE/spectrum/spectral_summary.csv`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\spectrum\spectral_summary.csv>) | asset_e45cd83f9cbc | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`experiments/linear_perturbation_analysis/FREEZE/spectrum/right_eigenvectors.npz`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\spectrum\right_eigenvectors.npz>) | asset_8f3a3aa5c631 | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`experiments/linear_perturbation_analysis/FREEZE/spectrum/left_eigenvectors.npz`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\spectrum\left_eigenvectors.npz>) | asset_9e76bb48e872 | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`experiments/linear_perturbation_analysis/FREEZE/spectrum/shock_mask.json`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\spectrum\shock_mask.json>) | asset_3b8c484e13f4 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`experiments/linear_perturbation_analysis/FREEZE/cfd_validation/validation_summary.csv`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\cfd_validation\validation_summary.csv>) | asset_eef93c1945fd | FROZEN_VERIFIED | SUMMARY_ONLY |

MISSING_ASSETS：missing_persisted_jacobian_fourier_blocks。

OPTIONAL_ASSETS：Full 512 eigenvalues each block; top32 eigenvectors; early-time Fig13 amplitude playback。

### 06 Cross-flow Compare

REQUIRED_ASSETS：Case8/Cylinder budgets and metric provenance；Distinct spatial masks；Cylinder cumulative sectors and fixed-band scalar。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_CHANNEL_BUDGET.csv`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\J2B_CHANNEL_BUDGET.csv>) | asset_10c30fe6d6e0 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/J2C_V2_CHANNEL_BUDGET.csv`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\J2C_V2_CHANNEL_BUDGET.csv>) | asset_06b3fab66997 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/runs/cylinder_D_u/spatial_cumulative.npz`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\runs\cylinder_D_u\spatial_cumulative.npz>) | asset_77343b219f8b | FROZEN_VERIFIED | ADAPTER_REQUIRED |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/analysis/causal_values.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\analysis\causal_values.json>) | asset_1d0281537cf2 | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`Paper/fig/fig_14/Du_spatial_rerun/FREEZE/Pi_at_trajectory_integrated.npz`](<D:\Paper\passage6\Paper\fig\fig_14\Du_spatial_rerun\FREEZE\Pi_at_trajectory_integrated.npz>) | asset_1930484b4ef9 | FROZEN_VERIFIED | ADAPTER_REQUIRED |

MISSING_ASSETS：missing_cylinder_trajectory_spatial_pi_at。

OPTIONAL_ASSETS：Four-method external width context; no universal ranking。

### 07 Reproducibility Center

REQUIRED_ASSETS：Method SHA/config/grid/integrator；Source indices, recorded freeze hashes and observed verification status。

| FOUND_ASSETS | Asset ID | Status | Readiness |
| --- | --- | --- | --- |
| [`final_corrected_evidence_freeze_v1/FINAL_EVIDENCE_MANIFEST.json`](<D:\Paper\passage6\final_corrected_evidence_freeze_v1\FINAL_EVIDENCE_MANIFEST.json>) | asset_573959040f21 | FROZEN_VERIFIED | NOT_USABLE |
| [`experiments/linear_perturbation_analysis/FREEZE/SHA256_MANIFEST.json`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\SHA256_MANIFEST.json>) | asset_e1b9ba43e984 | AVAILABLE_UNVERIFIED | NOT_USABLE |
| [`experiments/gate_ablation/FREEZE/checksums.txt`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\checksums.txt>) | asset_a4ea26bba8cb | AVAILABLE_UNVERIFIED | NOT_USABLE |
| [`experiments/entropy_budget_closure/FREEZE/FREEZE_MANIFEST.json`](<D:\Paper\passage6\experiments\entropy_budget_closure\FREEZE\FREEZE_MANIFEST.json>) | asset_c50aaca8961b | FROZEN_VERIFIED | SUMMARY_ONLY |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/provenance/result_hashes.csv`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\provenance\result_hashes.csv>) | asset_bc9f2af0ad5f | VERIFIED_NOT_FROZEN | SUMMARY_ONLY |
| [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/provenance/result_hashes.csv`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\provenance\result_hashes.csv>) | asset_4325edb27f33 | VERIFIED_NOT_FROZEN | SUMMARY_ONLY |

MISSING_ASSETS：missing_near1d_raw_epsilon_scan、missing_persisted_jacobian_fourier_blocks。

OPTIONAL_ASSETS：Current-vs-historical source drift table; missing hashes remain visible。

### A–I 实验专项核验

**A. Case8主线。** [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\J2B_PROTOCOL_LOCK.json>)保存128×32、CFL=.05、T=.08、1912 steps及六快照时刻（0、.01598326359832636、.03200836820083682、.04799163179916318、.06401673640167364、.08）。A/B/C/D都有`final_state.npz`、1912×53的stage_weighted_history、六个native-face endpoint图；其中x-face32×129、y-face32×128。corrected production checkpoints有density/pressure32×128、primitive/conservative32×128×4、front/width32、17-mode谱，已做四组终态与hash-verified J2B逐值一致检查。stage history包含E_bg/E_aa/E_at、三stage dotE/max及scalar front积分，但不包含每步state或每stage空间场。shock width/front RMS/HF分别用已有detector/source定义。

[`Paper/fig/fig_14/Du_spatial_rerun/FREEZE/rerun_provenance.md`](<D:\Paper\passage6\Paper\fig\fig_14\Du_spatial_rerun\FREEZE\rerun_provenance.md>)明确近期D_u数据是**既有诊断重跑**；canonical native-face NPZ及structured NPY已freeze。它不改变production状态；terminal bitwise match、E_at=.0027771079325925934、face积分绝对误差4.337e-18。x/y累计数组需dy/dx积分；derived cell average不能用sum作为E_at。只有终端累计map，没有map时间轴。

**B. Entropy-budget closure。** [`experiments/entropy_budget_closure/FREEZE/FREEZE_MANIFEST.json`](<D:\Paper\passage6\experiments\entropy_budget_closure\FREEZE\FREEZE_MANIFEST.json>)引用真实raw stage和step文件（不是仅summary）。B_u CFL=.05 zero-channel；D_u CFL=.2/.1/.05/.025，steps为3451/6901/13802/27603，T10、128²、周期一阶。stage_closure shape分别10353/20703/41406/82809×14，B_u41406×14；step_closure rows等于accepted steps、26字段。G、D_bg/D_aa/D_at/D_total、R_SD、eps_SD、R_decomp是stage级；S_n/S_np1/DeltaS与各E_*_step/R_time是step级。报告max eps_SD=3.7427525702529528e-15，B_u D_at=0；R(T)随D_u CFL细化趋近零，全局斜率2.9999942283876795。已有报告的数值解释与raw可追溯，不宣称精确全离散恒等式。closure实验未存空间state trajectory，不能用其他涡实验不同CFL的场假装同步。

**C. Gate ablation。** [`experiments/gate_ablation/FREEZE/MANIFEST.md`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\MANIFEST.md>)、calibration_snapshot15行qat_sweep、matched_qat、三组entropy/metrics/Pi_at全部在freeze。Pi_at是float64、32×128、TRAJECTORY_INTEGRATED；entropy.csv/metrics.csv为terminal summary，不能播放其时间轨迹。三组E_at相对匹配误差约1.5216%，不是严格相等。窗口cell中心、固定initial front±.08，前沿内份额读已有analysis而非硬编码；native-face J2窗口另记录。当前积分复核通过，不能二次乘dt/面积。

**D. Near1D Mach6/ε scan。** [`Paper/fig/fig_7/README.md`](<D:\Paper\passage6\Paper\fig\fig_7\README.md>)明确五点E_at抄自DOCX，band百分比与A_D/A_B为约数；local_exponents来自这些印刷数值，global2.006015920不是本阶段核验的raw scan证据。所有fig7 numeric/rendered资产标记AVAILABLE_UNVERIFIED/figure-only/NOT_USABLE。全目录CSV header与路径检索未发现权威五档raw输出、method/config/hash或spatial Pi_at。Quirk单次弱扰动负对照单独列legacy；谱验证ε=1e-4/1e-5/1e-6也不是这五档非线性ε实验。

**E. MUSCL-MC。** [`results/high_order_transfer/experiment2_freeze/EXPERIMENT2_FREEZE_README.md`](<D:\Paper\passage6\results\high_order_transfer\experiment2_freeze\EXPERIMENT2_FREEZE_README.md>)确认一阶EC/PSD身份不变，primitive MUSCL-MC重构独立协议。Vortex64²/128²/256²，B/D各一组，CFL=.1、T10，6组终态density；Case8 128×32、CFL=.05、T.08，B/D两组终态density。raw CSV有rho L1、velocity L2、E_at、field difference frozen summary；Case8 width/RMS/HF/window fraction与max Pi_at只在summary，未存完整空间Pi_at。八组density可做终态比较；checkpoint/interruption/smoke不得替代final production。[`Figure8_local_run_archive/audit/fig8_data_audit.md`](<D:\Paper\passage6\Figure8_local_run_archive\audit\fig8_data_audit.md>)纠正旧“B–D field difference随网格单调消失”的叙述：冻结数组difference实际不单调。不能将旧图稿趋势混入主线。

**F. Linear/Fourier。** [`experiments/linear_perturbation_analysis/FREEZE/experiment_report.md`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\experiment_report.md>)确认common zero-residual discrete shock，不使用Case8 tanh初态作linearization。base NPZ Ubar128×4、Ubar_2d32×128×4、x128、y32；谱CSV68×9；eigenvalues complex array4×17×512；left/right eigenvectors4×17×512×32（仅top32 vectors）；leading primitive profiles见逐member metadata。q_at四档、ell0..16完备；ell1/4/8/12存在。shock mask fixed x-cell58..66（pressure-jump5% max、邻cell扩一层）。leakage5.889e-16、operator-linearity6.062e-12、eigen residual<=5.389e-11、colored action3.203e-08等记录在frozen audit。production FD epsilon1e-8，旧1e-6扫描已替换。Jacobian/Fourier构建代码和audit存在，但serialized矩阵未找到。mode4/8 leading localization低，不应称“shock-localized”；最大alpha在mode16几乎不变，其他mode左右移均存在。

**G. Fig13。** 真实24 runs=4 modes×2 q_at×3 ε，全部33-point physical_time/modal_amplitude/log_modal_amplitude等8字段CSV存在。summary24×18包含sigma_LIN、sigma_RK3、sigma_CFD、relative discrepancy、fit0..32、R²、history_path。此次只读取和检查完整性；已有summary按ε分组最大relative discrepancy：{'0.0001': 0.00014310436622350458, '1e-05': 1.4191439504558442e-05, '1e-06': 2.0991845492983838e-06}（fraction，不是百分数）。min fit R²=0.9999999999785093。可播放真实投影幅值时间序列；没有24组full spatial CFD state轨迹，不能从eigenmode伪造实际field movie。

**H. Mach3 Cylinder。** [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/J2C_V2_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\J2C_V2_PROTOCOL_LOCK.json>)固定stretched O-grid nr32×ntheta128、r=.5..8、stretch3、T2、dt=.00020498103925386903、9757 steps。A/B/D各有final state、9757-step history、五endpoint face NPZ（0/2439/4878/7318/9757）。snapshot instant rate有空间数据；`spatial_cumulative.npz`仅bins17、channel_bg/aa/at/total各16与shock_at/J/Pt scalar。[`jcp_extension_v1/J2_entropy_diagnostics/J2C_S0_localization_semantics/analysis/localization_values.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_S0_localization_semantics\analysis\localization_values.json>)明确既有固定band份额是**cumulative**，此前summary中的final-rate文字须按audit理解；数值约.007776872193，不据此补全空间map。E_at_int=.09142394966318078，primary budget interior-only；fixed A_u authoritative front radial ±.16与Case8不同。front widths B/D近检测器分辨下限，不能细分优劣。full-trajectory空间Pi_at正式MISSING，已存累计sector是可接受的最小替代。

**I. External flux context。** 四种指定通量Roe-HH/HLLE/HLLEMCC/Chandrashekar KEP-ES(Rus)在Case8 v2和Cylinder v1都有canonical width和完整raw终态/多个checkpoint，并非仅summary。raw路径是`raw/roe_hh`、`raw/hlle`、`raw/hllemcc`、`raw/chandrashekar_ec_ev_llf`。本次width与独立canonical表精确匹配；未经逐文件上游冻结核验的raw fields仍AVAILABLE_UNVERIFIED/NOT_USABLE，不能仅凭“full field存在”视为production-ready。图17审计中external与final internal采用两组分开来源，不使用original/proposed旧内组。不作universal flux排名。

## 6. V1_DATA_SUPPORT_MATRIX

| P0/Module | Feature / Required data | Asset references | Status | Frontend readiness | P0 blocker |
| --- | --- | --- | --- | --- | --- |
| P0-01/01 | Mechanism Explorer：Final flux/operator identity；J/gate and output decomposition；Strict-1D/near-1D conditions | asset_a0548b71ae83, asset_8fe8e8d14264, asset_321c7aa318c8 | SUPPORTED | SUMMARY_ONLY / schematic | NO |
| P0-02/02 | Case 8 Replay：Case8 configurations + field snapshots + temporal metadata；Available real case/configuration registry | asset_8d15c3f16f95, asset_6ff7edcc7de2, asset_20d838d92e6a, asset_5c4aeaba111b, asset_99701f5ec82d, asset_f661621c298c, asset_0d9e3b382a3d, asset_e311ebcc6ca5, asset_b1cdee2d84cf, asset_b1bfc6f87f56, asset_3b7d903c22f8, asset_8b4f30579573, asset_5e3098898c99, asset_e894deed7c59, asset_0741bf5f547c, asset_67de9e154164, asset_cf255d76e818, asset_701f2a4c8e26, asset_4ca5907c1463, asset_ac0331cdafd2, asset_c5fb8726078c, asset_1541b96d3943, asset_ff68c9d21b50, asset_6e5faf0f34c7, asset_77fd98155a34, asset_c04e3aff0866, asset_cf7e7f4878bb, asset_831e53c374b6, asset_f4323c28384b | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |
| P0-03/03 | Entropy Ledger：E_bg/E_aa/E_at per accepted step；Instantaneous spatial rates at saved times；Case7 G+D and fully-discrete residual | asset_0a3f2155fa2b, asset_4866864395cc, asset_b3904064f3d6, asset_b8418588583c | PARTIALLY_SUPPORTED | ADAPTER_REQUIRED / limited temporal/spatial support | NO; limited features recorded |
| P0-04/04 | Gate Allocation Explorer：Matched gate q_at and summary；Cumulative cell maps；Exact fixed cell window and sum convention | asset_513157e8d9c4, asset_aef55f8d1d5a, asset_a11ef6fc4e6e, asset_6850b4bab5cc, asset_4dce11517608 | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |
| P0-05/05 | Spectral Lab：Common zero-residual base；68 alpha records；Selected leading modes and fixed mask；24 nonlinear validation histories | asset_6c6b9c35c1dc, asset_e45cd83f9cbc, asset_8f3a3aa5c631, asset_9e76bb48e872, asset_3b8c484e13f4, asset_eef93c1945fd | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |
| P0-06/06 | Case 8 / Cylinder Cross-flow Compare：Case8/Cylinder budgets and metric provenance；Distinct spatial masks；Cylinder cumulative sectors and fixed-band scalar | asset_10c30fe6d6e0, asset_06b3fab66997, asset_77343b219f8b, asset_1d0281537cf2, asset_1930484b4ef9 | PARTIALLY_SUPPORTED | ADAPTER_REQUIRED / limited temporal/spatial support | NO; limited features recorded |
| P0-07/07 | Reproducibility Center：Method SHA/config/grid/integrator；Source indices, recorded freeze hashes and observed verification status | asset_573959040f21, asset_e1b9ba43e984, asset_a4ea26bba8cb, asset_c50aaca8961b, asset_bc9f2af0ad5f, asset_4325edb27f33 | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |
| P0-08/07 | Real experimental data loading：Final flux/operator identity；J/gate and output decomposition；Strict-1D/near-1D conditions；Case8 configurations + field snapshots + temporal metadata；Available real case/configuration registry；E_bg/E_aa/E_at per accepted step；Instantaneous spatial rates at saved times；Case7 G+D and fully-discrete residual；Matched gate q_at and summary；Cumulative cell maps；Exact fixed cell window and sum convention；Common zero-residual base；68 alpha records；Selected leading modes and fixed mask；24 nonlinear validation histories；Case8/Cylinder budgets and metric provenance；Distinct spatial masks；Cylinder cumulative sectors and fixed-band scalar；Method SHA/config/grid/integrator；Source indices, recorded freeze hashes and observed verification status | asset_a0548b71ae83, asset_8fe8e8d14264, asset_321c7aa318c8, asset_8d15c3f16f95, asset_6ff7edcc7de2, asset_20d838d92e6a, asset_5c4aeaba111b, asset_99701f5ec82d, asset_f661621c298c, asset_0d9e3b382a3d, asset_e311ebcc6ca5, asset_b1cdee2d84cf, asset_b1bfc6f87f56, asset_3b7d903c22f8, asset_8b4f30579573, asset_5e3098898c99, asset_e894deed7c59, asset_0741bf5f547c, asset_67de9e154164, asset_cf255d76e818, asset_701f2a4c8e26, asset_4ca5907c1463, asset_ac0331cdafd2, asset_c5fb8726078c, asset_1541b96d3943, asset_ff68c9d21b50, asset_6e5faf0f34c7, asset_77fd98155a34, asset_c04e3aff0866, asset_cf7e7f4878bb, asset_831e53c374b6, asset_f4323c28384b, asset_0a3f2155fa2b, asset_4866864395cc, asset_b3904064f3d6, asset_b8418588583c, asset_513157e8d9c4, asset_aef55f8d1d5a, asset_a11ef6fc4e6e, asset_6850b4bab5cc, asset_4dce11517608, asset_6c6b9c35c1dc, asset_e45cd83f9cbc, asset_8f3a3aa5c631, asset_9e76bb48e872, asset_3b8c484e13f4, asset_eef93c1945fd, asset_10c30fe6d6e0, asset_06b3fab66997, asset_77343b219f8b, asset_1d0281537cf2, asset_1930484b4ef9, asset_573959040f21, asset_e1b9ba43e984, asset_a4ea26bba8cb, asset_c50aaca8961b, asset_bc9f2af0ad5f, asset_4325edb27f33 | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |
| P0-09/01/04/05/06/07 | Explore Mode basic demo flow：Final flux/operator identity；J/gate and output decomposition；Strict-1D/near-1D conditions；Matched gate q_at and summary；Cumulative cell maps；Exact fixed cell window and sum convention；Common zero-residual base；68 alpha records；Selected leading modes and fixed mask；24 nonlinear validation histories；Case8/Cylinder budgets and metric provenance；Distinct spatial masks；Cylinder cumulative sectors and fixed-band scalar；Method SHA/config/grid/integrator；Source indices, recorded freeze hashes and observed verification status | asset_a0548b71ae83, asset_8fe8e8d14264, asset_321c7aa318c8, asset_513157e8d9c4, asset_aef55f8d1d5a, asset_a11ef6fc4e6e, asset_6850b4bab5cc, asset_4dce11517608, asset_6c6b9c35c1dc, asset_e45cd83f9cbc, asset_8f3a3aa5c631, asset_9e76bb48e872, asset_3b8c484e13f4, asset_eef93c1945fd, asset_10c30fe6d6e0, asset_06b3fab66997, asset_77343b219f8b, asset_1d0281537cf2, asset_1930484b4ef9, asset_573959040f21, asset_e1b9ba43e984, asset_a4ea26bba8cb, asset_c50aaca8961b, asset_bc9f2af0ad5f, asset_4325edb27f33 | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |
| P0-10/02/03/05/07 | Lab Mode basic experiment browsing flow：Case8 configurations + field snapshots + temporal metadata；Available real case/configuration registry；E_bg/E_aa/E_at per accepted step；Instantaneous spatial rates at saved times；Case7 G+D and fully-discrete residual；Common zero-residual base；68 alpha records；Selected leading modes and fixed mask；24 nonlinear validation histories；Method SHA/config/grid/integrator；Source indices, recorded freeze hashes and observed verification status | asset_8d15c3f16f95, asset_6ff7edcc7de2, asset_20d838d92e6a, asset_5c4aeaba111b, asset_99701f5ec82d, asset_f661621c298c, asset_0d9e3b382a3d, asset_e311ebcc6ca5, asset_b1cdee2d84cf, asset_b1bfc6f87f56, asset_3b7d903c22f8, asset_8b4f30579573, asset_5e3098898c99, asset_e894deed7c59, asset_0741bf5f547c, asset_67de9e154164, asset_cf255d76e818, asset_701f2a4c8e26, asset_4ca5907c1463, asset_ac0331cdafd2, asset_c5fb8726078c, asset_1541b96d3943, asset_ff68c9d21b50, asset_6e5faf0f34c7, asset_77fd98155a34, asset_c04e3aff0866, asset_cf7e7f4878bb, asset_831e53c374b6, asset_f4323c28384b, asset_0a3f2155fa2b, asset_4866864395cc, asset_b3904064f3d6, asset_b8418588583c, asset_6c6b9c35c1dc, asset_e45cd83f9cbc, asset_8f3a3aa5c631, asset_9e76bb48e872, asset_3b8c484e13f4, asset_eef93c1945fd, asset_573959040f21, asset_e1b9ba43e984, asset_a4ea26bba8cb, asset_c50aaca8961b, asset_bc9f2af0ad5f, asset_4325edb27f33 | SUPPORTED_WITH_ADAPTER | ADAPTER_REQUIRED | NO |


精确各asset数据status列在JSON的asset_statuses；P0支持状态与单个asset状态不能混同。不存在“后端已可运行”的结论。

## 7. SCIENTIFIC_SEMANTICS_MATRIX

| Metric ID / UI term | Definition and time/spatial scope | Units | Evidence / constraint |
| --- | --- | --- | --- |
| Pi_at_instantaneous / Pi_at instantaneous | 0.5*q_at*J*∣∣P_t z∣∣² at one face/state; unweighted rate；endpoint native-face maps; not actual stored RK-stage trajectories | instantaneous rate in model normalization; SI UNKNOWN | [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/snapshots/native_faces_step_001912.npz`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs\case8_D_u\snapshots\native_faces_step_001912.npz>)；Do not call accumulated maps instantaneous |
| Pi_at_stage_weighted / Pi_at stage-weighted | dt*(dotE_s0/6+dotE_s1/6+2*dotE_s2/3); may be domain/region aggregate；PER_STEP records with three stage aggregates | entropy-production increment in model normalization; SI UNKNOWN | [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/stage_weighted_history.csv`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs\case8_D_u\stage_weighted_history.csv>)；Stage-weighted CSV has one row per step; not raw spatial stage fields |
| Gate_cell_Pi_at_integrated / Gate trajectory-integrated Pi_at | Cell allocation already includes native face measure and RK/time integration; sum(array)=E_at；32x128 [y,x] cumulative cells | model integrated entropy; SI UNKNOWN | [`experiments/gate_ablation/FREEZE/README.md`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\README.md>)；No extra dx*dy or dt; pressure/ungated are recorded gate variants |
| Case8_face_Pi_at_integrated / Case8 D_u trajectory-integrated Pi_at | Sum of dt*RK weights of face rate; E_at=dy*sum(x_faces)+dx*sum(y_faces)；32x129 x-faces +32x128 y-faces | time-integrated face rate; SI UNKNOWN | [`Paper/fig/fig_14/Du_spatial_rerun/FREEZE/rerun_provenance.md`](<D:\Paper\passage6\Paper\fig\fig_14\Du_spatial_rerun\FREEZE\rerun_provenance.md>)；Existing DIAGNOSTIC_RERUN, not original production output; derived cell average is not authoritative integral |
| E_at / E_at | Sum of accepted-step channel increments over trajectory; fixed face/boundary scope；Scalar or PER_STEP cumulative | model integrated entropy; SI UNKNOWN | [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\J2B_PROTOCOL_LOCK.json>)；Cylinder primary budget is interior-only; compare scopes explicitly |
| allocation_fraction / Allocation fraction f_at | E_at/(E_bg+E_aa+E_at)；cumulative budget fraction | dimensionless | [`experiments/gate_ablation/FREEZE/gate_ablation_analysis.csv`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\gate_ablation_analysis.csv>)；Not shock localization; zero denominator must be handled explicitly |
| gate_shock_window_fraction / Gate cell-centered shock-window fraction | sum(saved cell allocation in ∣x_i-x_s(y_j)∣<=.08)/E_at; x_s=.5+.0125*sin(8*pi*y)；fixed prescribed initial-front window | dimensionless | [`experiments/gate_ablation/FREEZE/README.md`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\README.md>)；Cell mask; cannot merge with J2 native-face percentage |
| case8_J2_face_localization / Case8 J2 face-based shock localization | RK/time/face-measure weighted native x/y face production in prescribed +/- .08 front window / trajectory E_at；native-face fixed geometry; cumulative | dimensionless | [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\J2B_PROTOCOL_LOCK.json>)；Face coordinates and boundary scope differ from gate cells; follow enumerator, do not infer from labels |
| cylinder_front_band_fraction / Cylinder cumulative front-band fraction | shock_at / sum(channel_at) from spatial_cumulative.npz; fixed A_u authoritative anchors +/- .16 radial band；16 cumulative angular bins plus scalar band; interior-only | dimensionless | [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/J2C_V2_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\J2C_V2_PROTOCOL_LOCK.json>)；Audit corrected semantic label: cumulative, not final-rate; not directly ranked against Case8 |
| cylinder_angular_fraction / Cylinder angular allocation | channel_at[bin] / E_at_int; bins partition theta [-pi,pi] into16；cumulative stage/time/face weighting | dimensionless | [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/runs/cylinder_D_u/spatial_cumulative.npz`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\runs\cylinder_D_u\spatial_cumulative.npz>)；16 bins are not a full spatial Pi_at heatmap |
| spectral_abscissa / Spectral abscissa alpha | max(Re(lambda)) over 512 eigenvalues of each common-base Fourier block；STATIC; 4 q_at x17 modes | inverse model time | [`experiments/linear_perturbation_analysis/FREEZE/spectrum/spectral_summary.csv`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\spectrum\spectral_summary.csv>)；Alpha>0 is allowed; q_at shifts have mixed signs; m=16 max is essentially unchanged |
| growth_rate / Growth rate | sigma_LIN=Re(lambda); sigma_RK3=log∣R(dt*lambda)∣/dt; sigma_CFD=OLS slope(log projected amplitude)；33 endpoints, common steps0..32; 24 runs | inverse model time | [`experiments/linear_perturbation_analysis/FREEZE/cfd_validation/validation_summary.csv`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\cfd_validation\validation_summary.csv>)；Not interchangeable with envelope alpha; common early window only; relative error is a fraction |
| case8_front_RMS / Case8 front RMS | RMS of p50 detected front displacement about its mean；y-row front; checkpoint/terminal | model length; SI UNKNOWN | [`solver/diagnostics/flagship_cross_modal_case8.py`](<D:\Paper\passage6\solver\diagnostics\flagship_cross_modal_case8.py>)；Not transverse velocity RMS or growth rate |
| case8_HF / Case8 high-k metric | sum(∣rfft(signal)/N∣²) for k>seed mode4; fraction divides by sum(k>=1 energy)；front-displacement or transverse signal must be identified | signal amplitude squared; SI UNKNOWN | [`solver/diagnostics/flagship_cross_modal_case8.py`](<D:\Paper\passage6\solver\diagnostics\flagship_cross_modal_case8.py>)；front_high_k_energy, transverse_high_k_energy and fraction must remain separate |
| cylinder_HF / Cylinder HF-RMS/high angular energy | Saved cylinder front high-pass RMS and angular spectral energy from authoritative detector；curved-front angular samples | model length / length²; SI UNKNOWN | [`solver/diagnostics/cylinder.py`](<D:\Paper\passage6\solver\diagnostics\cylinder.py>)；Not the Case8 normalized k>4 statistic; no common colourbar without mapping |
| case8_width / Case8 shock width | Mean row-local pressure p10-p90 crossing distance anchored to expected p50 front；row widths and summary | model length; cells only when divided by declared dx | [`solver/diagnostics/flagship_cross_modal_case8.py`](<D:\Paper\passage6\solver\diagnostics\flagship_cross_modal_case8.py>)；physical vs cell-normalized labels must differ; MUSCL is a different protocol |
| cylinder_width / Cylinder centerline/front width | p10-p90 crossing distances along radial bow-front detector; centerline and front mean distinct；O-grid detector/terminal | model length; nominal cell normalization separate | [`Paper/fig/fig_17/data_audit.md`](<D:\Paper\passage6\Paper\fig\fig_17\data_audit.md>)；B/D and several external values detector limited; nominal dr=.234375 is not an error bar |
| closure_SD / Semi-discrete closure | G(U)=entropy-variable contraction of actual FV RHS; D(U)=unique-face observer production; R_SD=G+D；PER_STAGE | model entropy rate; eps_SD dimensionless | [`experiments/entropy_budget_closure/FREEZE/frozen_experiment_report.md`](<D:\Paper\passage6\experiments\entropy_budget_closure\FREEZE\frozen_experiment_report.md>)；Measured floating-point closure is not a fully-discrete identity |
| closure_time / Fully discrete residual R(T) | DeltaS(T)+E_obs(T); actual state entropy change plus weighted trajectory production；PER_STEP / terminal refinement | model entropy; SI UNKNOWN | [`experiments/entropy_budget_closure/outputs/Du_cfl_005/step_closure.csv`](<D:\Paper\passage6\experiments\entropy_budget_closure\outputs\Du_cfl_005\step_closure.csv>)；Sum E_*_step if drawing cumulative channels; E_*_step is not itself cumulative; no recalculation performed here |


## 8. DATA_DEPENDENCY_MAP

仅映射已存在流程，不在本阶段重新计算。

`actual accepted SSP-RK3 stage state → unchanged FV RHS + entropy-variable contraction G → unique-face channel observer D_bg/D_aa/D_at → raw stage_closure.csv → step RK weights(1/6,1/6,2/3) and dt → step_closure.csv and terminal R(T) → temporal refinement summary`

Evidence：asset_b3904064f3d6, asset_b8418588583c, asset_dad98df1a5ea。Missing：saved full stage state fields。

`Gate face observer at every stage → face-to-cell allocation with measure → dt/RK accumulation → Pi_at.npy → fixed cell shock window → gate_ablation_analysis.csv`

Evidence：asset_a11ef6fc4e6e, asset_513157e8d9c4。Missing：none。

`Case8 formal stage observer → aggregated step histories + six instantaneous face maps → existing D_u DIAGNOSTIC_RERUN adds accumulator → Pi_at_trajectory_integrated native-face arrays → fixed native-face localization`

Evidence：asset_0a3f2155fa2b, asset_1930484b4ef9, asset_0d36bf11a1df。Missing：original full trajectory spatial maps for other configurations。

`Cylinder native interior radial/angular faces at stages → time/RK/face-measure weighted bins and fixed-region sums → spatial_cumulative.npz → sector fractions and fixed-band localization`

Evidence：asset_77343b219f8b, asset_703dbef1b83c。Missing：full trajectory per-face/cell spatial accumulation map。

`common zero-residual base → central finite-difference numerical Jacobian construction → Fourier reduction → eigenvalues and left/right eigenvectors → spectral abscissa and selected branches → 24 pre-registered nonlinear runs → projected modal histories and fitted growth rates`

Evidence：asset_6c6b9c35c1dc, asset_707e6ecc89ed, asset_bf6eb2f08545, asset_8f3a3aa5c631, asset_eef93c1945fd。Missing：serialized Jacobian/Fourier matrices。

## 9. Replay Candidates

| Experiment | Class | True temporal support | Constraint |
| --- | --- | --- | --- |
| Case8 production | GOOD_CANDIDATE | 6 actual flow/instantaneous-face snapshots per configuration; 1912 accepted-step scalar histories | Discrete snapshot slider; no per-step spatial trajectory; snapshots are VERIFIED_NOT_FROZEN with exact terminal match |
| Gate ablation | GOOD_CANDIDATE | STATIC trajectory-integrated maps + terminal metrics; no saved map time series | Gate/config selection; do not animate cumulative map as instantaneous evolution |
| Entropy closure | GOOD_CANDIDATE | PER_STAGE and PER_STEP scalar logs for five runs | Stage-level diagnostic timeline, not full spatial-stage CFD replay |
| Spectrum | GOOD_CANDIDATE | STATIC 68 combinations | Only four recorded q_at; no continuous predicted spectrum |
| Eigenmodes | GOOD_CANDIDATE | STATIC complex modes and leading primitive profiles | Any phase sweep is eigenmode illustration, not stored time evolution; 32 eigenvectors per block |
| Fig13 validation | GOOD_CANDIDATE | 24 time-series of33 points each | Projected amplitude playback over common early window, no spatial field movie |
| Cylinder | POSSIBLE | 5 instantaneous-face checkpoints per A/B/D; 9757-step scalar histories; 16 cumulative sectors | Full cumulative spatial heatmap missing; use sectors/band/metrics and label interior-only |

## 10. Live Demo Candidates

只基于已读源码/配置/规模/历史耗时初筛，不保证现场可运行。没有启动任何候选。

| Candidate | Class | Reason/source |
| --- | --- | --- |
| small periodic vortex / entropy observer | POSSIBLE | Existing Cartesian periodic first-order path and observer; production128² T10 has3451..27603 steps. Small grid/short time may fit after independent runtime/identity qualification. No run started. [`experiments/entropy_budget_closure/run_entropy_budget_closure.py`](<D:\Paper\passage6\experiments\entropy_budget_closure\run_entropy_budget_closure.py>) |
| small Case8 | POSSIBLE | Existing128x32 Cartesian driver; original1912 steps, saved D_u observer run wall time~378s. Smaller grid/shorter T needs separate protocol approval and performance measurement; not scientifically equivalent production. [`jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/run_result.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2B_case8_formal\runs\case8_D_u\run_result.json>) |
| three matched-budget gates | NOT_RECOMMENDED | Frozen matched q_at values depend on128x32,T=.08 and1912 steps; changing grid/time invalidates matched-budget calibration. Use Replay. [`experiments/gate_ablation/FREEZE/MANIFEST.md`](<D:\Paper\passage6\experiments\gate_ablation\FREEZE\MANIFEST.md>) |
| common-base Jacobian + Fourier spectrum | NOT_RECOMMENDED | Base Newton solve, finite-difference columns and68 complex512x512 eigensystems; unsuitable live browser generation. Use frozen eigensystem. [`experiments/linear_perturbation_analysis/FREEZE/config.json`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\config.json>) |
| short nonlinear selected modal validation | POSSIBLE | Only32 accepted steps but requires exact common base, selected complex left/right modes, perturbation normalization and positive states; timing/packaging unverified. [`experiments/linear_perturbation_analysis/FREEZE/scripts/cfd_validation.py`](<D:\Paper\passage6\experiments\linear_perturbation_analysis\FREEZE\scripts\cfd_validation.py>) |
| Mach3 Cylinder | NOT_RECOMMENDED | Stretched curvilinear32x128 O-grid and9757 steps; interior-face/boundary scope and detector limitations require protocol control; Replay has sufficient summaries. [`jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/J2C_V2_PROTOCOL_LOCK.json`](<D:\Paper\passage6\jcp_extension_v1\J2_entropy_diagnostics\J2C_cylinder_formal_v2\J2C_V2_PROTOCOL_LOCK.json>) |
| Near1D epsilon scan | UNKNOWN | Five-amplitude raw protocol and source identity not proven. Quirk single weak perturbation cannot replace it. [`Paper/fig/fig_7/README.md`](<D:\Paper\passage6\Paper\fig\fig_7\README.md>) |
| MUSCL smooth/shock transfer | NOT_RECOMMENDED | Limiter/reconstruction/positivity protocol; vortex64²..256² with3448..13805 steps and prior interrupted256² attempts; production scale costly. [`results/high_order_transfer/experiment2_freeze/EXPERIMENT2_FREEZE_README.md`](<D:\Paper\passage6\results\high_order_transfer\experiment2_freeze\EXPERIMENT2_FREEZE_README.md>) |

## 11. P0 Blocker Audit

| P0 | Status | Specific gap or supported degradation |
| --- | --- | --- |
| P0-01 Mechanism Explorer | SUPPORTED | Final mechanism identity/theory source present; explanation and schematic supported. Formal near-1D numerical scan withheld. |
| P0-02 Case 8 Replay | SUPPORTED_WITH_ADAPTER | A/B/C/D configs, six genuine density/pressure/front checkpoints each and1912-step scalar histories; loader schema conversion required. |
| P0-03 Entropy Ledger | PARTIALLY_SUPPORTED | Budget logs and Case7 raw-stage closure are complete; spatial synchronization limited to saved endpoints. Dense per-stage/step flow fields missing. |
| P0-04 Gate Allocation Explorer | SUPPORTED_WITH_ADAPTER | Three hash-matched cumulative cell arrays and matched parameters/metrics/window definitions; adapter required. |
| P0-05 Spectral Lab | SUPPORTED_WITH_ADAPTER | 68 alpha rows,512 eigenvalues each,32 left/right eigenvectors per block, fixed mask and24x33 histories; adapter/complex mode decoding required. |
| P0-06 Case 8 / Cylinder Cross-flow Compare | PARTIALLY_SUPPORTED | Budgets, widths, RMS, instantaneous faces and16 cumulative sectors exist. Cylinder full-trajectory spatial Pi_at map unavailable; use labelled sector/fixed-band comparison. |
| P0-07 Reproducibility Center | SUPPORTED_WITH_ADAPTER | Scope/method freeze hashes and key experiment manifests checked. Source drift and unavailable hashes must remain visible; archived code required for exact replay execution. |
| P0-08 Real experimental data loading | SUPPORTED_WITH_ADAPTER | Real sources indexed with independent shape/header/time/hash metadata. No loader is implemented in Phase1; frozen/default release asset list can be chosen from evidence. |
| P0-09 Explore Mode basic demo flow | SUPPORTED_WITH_ADAPTER | Frozen mechanism→gate→spectrum→cross-flow→reproducibility story has minimal real-data support; near-1D/cumulative-cylinder map excluded. |
| P0-10 Lab Mode basic experiment browsing flow | SUPPORTED_WITH_ADAPTER | Case/config/time availability can be browsed from explicit metadata; unsupported choices must remain unavailable. |

## 12. Missing Assets

| Asset ID | Required asset | Evidence / limitation | P0 impact |
| --- | --- | --- | --- |
| missing_near1d_raw_epsilon_scan | Five epsilon runs 1e-2..1e-6: authoritative raw outputs/configuration/hash/trajectory | No raw five-amplitude production set found; Figure7 CSV explicitly transcribed from manuscript | NO; remove formal numerical near-1D scan from V1 experiment choices until proven |
| missing_near1d_spatial_pi_at | Authoritative instantaneous/spatial Pi_at and exact shock-band/amplitude data | Only approximate manuscript-transcribed percentages and amplitude ratios found | NO; optional near-1D evidence extension |
| missing_cylinder_trajectory_spatial_pi_at | Full-trajectory native-face/cell spatial Pi_at map | Five instantaneous faces and 16 cumulative angular bins are present; full spatial trajectory accumulation unavailable | PARTIAL; budget/sector/fixed-band comparison works; full cumulative heatmap cannot be delivered |
| missing_case8_per_step_state | 1912-step full flow-state time series | Six saved flow snapshots per A/B/C/D, not 1912 full states | NO for discrete Replay; cannot promise continuous/per-step field playback |
| missing_case8_per_stage_spatial_fields | Saved instantaneous spatial fields at all actual SSP-RK3 stages | Only six endpoint native-face snapshots; stage rates are aggregated in logs | PARTIAL; synchronized ledger/field allowed only at saved endpoints |
| missing_case8_AC_trajectory_maps | Persisted A_u/C_u full-trajectory spatial channel maps comparable to D_u diagnostic rerun | Only D_u accumulated spatial field located; original A/B/C/D have scalar cumulative histories | NO; A/B q_at-zero identities are proven by logs, C spatial cumulative map cannot be invented |
| missing_persisted_jacobian_fourier_blocks | Serialized numerical Jacobian and four-by-17 Fourier matrices | Spectrum/eigenpairs/base/verification and construction code exist; no stored full matrices found | NO; frozen spectra/modes suffice; matrix inspection/reproduction remains unavailable |
| missing_muscl_spatial_pi_at | Persisted spatial Pi_at and dense trajectory flow fields | Eight final density arrays and summaries exist; shock-window scalar/max production exist without saved Pi map | NO; MUSCL transfer is P1 context, summary and final-density views only |


TOP_5_DATA_GAPS：

1. Near1D Mach6五档ε的权威raw输出、配置、method/hash与精确空间/振幅指标未找到；Figure7表来自论文抄录，不能当正式数据。
2. Cylinder full-trajectory空间Pi_at累计场缺失；已有16角向累计分箱及固定band标量，不是完整场。
3. Case8只有6个真实流场/瞬时face快照；缺1912步完整空间轨迹与全部RK stage场，Ledger同步受限。
4. 原始Case8其他配置的完整轨迹累计空间通道图未找到；近期冻结诊断重跑仅覆盖D_u。
5. Serialized Jacobian/Fourier blocks未找到；MUSCL只存终态密度和summary，缺空间Pi_at；当前部分driver/observer历史hash漂移需保留。

## 13. Legacy/Superseded Assets

LEGACY=52；SUPERSEDED=609，验收LEGACY_COUNT合计661。CSV/JSON逐文件列出，均NOT_USABLE。Case8 baseline v1、旧results flagship/Quirk、J2C失败formal、J2D旧formal/v2不得混进最终方法。MUSCL旧Figure8的趋势问题是图稿叙述被纠正，当前冻结MUSCL生产数组并非legacy。所有fig7图表属来源不足，而不伪称已冻结raw。

## 14. Risks

- 18条historical source-hash引用与current source不同（含多个manifest重复引用），涉及baseline_case7/cylinder production driver、Case7-v3 extension driver及channel observer；最终flux SHA不变。`hash_verification.json`保留expected/current/path，不能据旧hash承诺用当前source完全复现。未修改任何source或FREEZE。
- Metadata verification和部分sum/endpoint检查不能替代全部科学认证；科学认证采用既有报告，缺失字段UNKNOWN。尚未建立SI单位映射、数据分发许可与来源外复制授权清单。
- Snapshot时间不一定等于请求的round checkpoint time；使用NPZ实际time。stage与step不能混称；stage-weighted_cumulative不是fully-discrete entropy identity。
- Different masks/boundary scopes、高频定义及detector floor禁止统一百分比排名；同名Pi_at有不同measure conventions。
- Freeze与工作副本保留重复物理文件资产；正式loader需显式选canonical evidence，不按文件名字自动去重。Phase1只是metadata索引，未生成Web数据包。

## 15. Recommendations for PRD

本节只列数据约束与进入下一阶段的建议，不撰写PRD或设计页面/API。

TOP_5_PRD_CONSTRAINTS：

1. Time slider只在真实已存时间点播放：Case8六帧，Cylinder五个瞬时face；Gate累计图和谱数据STATIC，不能暗示实时轨迹。
2. 严格分开Gate cell累计分配、Case8 native-face累计率积分、Cylinder interior-only sector/band口径；不得重复乘dt/面积或统一排名。
3. Near1D五档scan论文抄录数值不进入正式展示；Quirk单次弱扰动和Fourier验证epsilon不能替代该scan。
4. 参数只选已运行组合：A/B/C/D、三种校准gate、四档q_at、既存CFL/ε；谱位移与宏观响应非单调，不能插值成新科研结果。
5. 保留method/hash/config/掩膜/模型单位与验证状态；D_u不是通用更优解，Cylinder宽度受检测器限制；Live仅候选，本阶段未运行。

优先承接Gate冻结map、谱/validation、Case8六checkpoint及step ledger。缺项展示不可用；Cylinder采用累计sector和固定band scalar，累计heatmap在缺口解决前不作承诺。正式发布前检查adapter保留变量、坐标、时间、单位、mask、source/hash、诊断重跑标签，并只加载已确认身份的资产。P1/P2不得追加到P0。

## 16. OPEN_QUESTIONS

1. Near1D五档raw结果是否存在于本科研根之外？本根只有明确论文抄录来源，本阶段不访问其他盘猜补。
2. Cylinder full-trajectory空间map是否另有授权冻结资产？现有16箱与五instant maps不足以重构。任何新增CFD或科学后处理均留待另行任务。
3. Ledger在固定快照同步表达、Cross-flow在sector/band表达的降级是否可作为冻结P0最小闭环？若坚持dense spatial/累计Cylinder heatmap，缺口成为相应功能阻断，应按Phase0 change control处理。
4. 当前driver/observer source drift与freeze source版本如何由后续Reproducibility审计处理？使用exact archived copies前需逐项确认，不静默更新旧manifest。
5. 模型单位与SI尺度、数据许可/竞赛分发权限尚未确定；保持UNKNOWN，不把无量纲坐标任意写成m/s或Pa。
6. PSD与正熵产解释限于已认证fixed-interface分解；不要以图形/交互扩大到universal damping、高阶/3D或任意Mach鲁棒性。

## Acceptance Record

```text
DATA_ASSET_INVENTORY=PASS
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
ASSET_COUNT=2337
FROZEN_VERIFIED_COUNT=416
LEGACY_COUNT=661
MISSING_ASSET_COUNT=8
P0_SUPPORTED_COUNT=8
P0_PARTIAL_COUNT=2
P0_BLOCKED_COUNT=0
TIME_SERIES_ASSET_COUNT=66
REPLAY_CANDIDATE_COUNT=7
LIVE_DEMO_CANDIDATE_COUNT=3
INVENTORY_DOC=D:\比赛\数媒\data\01_DATA_ASSET_INVENTORY.md
INVENTORY_JSON=D:\比赛\数媒\data\data_asset_inventory.json
NEXT_PHASE=PRD
```

TIME_SERIES_ASSET_COUNT只计已有可用CSV时间序列文件（含工作/冻结副本），不把每个单帧NPZ算一条时间序列；6帧/5帧场组另列Replay。Replay候选数为7个实验家族；Live候选数为GOOD_CANDIDATE或POSSIBLE的3个初筛家族，不表示已经运行。NEXT_PHASE=PRD只是允许下一阶段，本阶段未开始。

完整逐asset字段/shape/header/hash/source、状态与模块关联见data_asset_inventory.json和CSV。DATA_INVENTORY_FREEZE.json只冻结本次盘点产物，不将未经核验的数据升级为科学冻结。

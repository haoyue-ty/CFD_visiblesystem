# V2-P0 Case 8 能力核查

日期：2026-10-02（Asia/Shanghai）。本阶段做静态源码审计、V1 回归和契约基础扩展，不运行 CFD。实施依据是用户明确要求执行实施计划 P0；计划中此前“本次只规划”的历史描述不限制这次开发授权。

## 1. 唯一科学依赖

唯一根目录为 `D:/Paper/passage6`。不使用归档、交付副本或按搜索顺序导入。
机器清单：[source_manifest.json](source_manifest.json)，含 37 个文件的相对路径、模块名、直接 imports、大小、mtime_ns 和 SHA-256。闭包通过 AST 收集，包含包初始化文件；收集函数内部 import 是保守策略，不等于这些模块都在最小执行路径被加载。

| 职责 | 根目录内来源 |
| --- | --- |
| 目标 flux | `solver/fluxes/cross_mode_ec_unified_v1.py` |
| EC 中心核、耗散 | `solver/fluxes/chandrashekar_es.py`、`unbounded_cross_mode.py` |
| Case 8 初始化、协议 | `solver/cases/flagship_cross_modal_case8.py`、`normal_shock.py` |
| Euler、网格、边界、RHS、stage guard | `solver/core/` 清单中对应模块 |
| 带 observer 的 SSP-RK3 | `jcp_extension_v1/J2_entropy_diagnostics/J2B0_case8_integration/code/case8_j2_driver.py` |
| 唯一 face observer | 同目录 `case8_entropy_observer.py` |
| 通道熵、聚合 | `jcp_extension_v1/J2_entropy_diagnostics/diagnostics/` |
| 前沿、宽度、谱、checkpoint metrics | `solver/diagnostics/flagship_cross_modal_case8.py`、`solver/experiments/baseline_case8_production.py` |
| 正式协议 | `jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json` |
| 正式驱动（仅参考） | 同目录 `analysis/case8_j2b_formal.py` |

flux SHA-256：`98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0`，与 V1 method hash 一致。其余哈希见清单，不用一个 flux hash 代表整个算法链。

复查命令（PowerShell 7，项目根目录）：

```powershell
./.venv/Scripts/python.exe -B -m scripts.verification.v2_source_manifest --verify
```

该工具不导入科学模块，不调用 formal CLI；`--verify` 不覆盖锁定清单。新增源依赖必须审查并更新清单，不能遇到 drift 就自动重新接受。

## 2. 输入能力与待实现项

**P0 没有 V2 配置验证 API，也没有启动求解能力。以下是供 P1/P2 实施的 capability 设计，不能用作“已可运行”的声明。**

| 字段 | 证据/已核实值 | P1 验证策略及 P2 前置 |
| --- | --- | --- |
| case_id | Case 8 模块完整存在 | 仅 `case8`；其他 V1 Case 保留回放 |
| q_aa / q_at | flux 接收显式 keyword；正式 A/B/C/D 为 13.2/3.96 和 0/0.396 | 优先登记离散标准值；连续范围待生效/稳定性与资源验证，不能宣称任意值支持 |
| Nx / Ny | `initial_setup(n, ny, gas)`；RHS 验证 `[ny,nx,4]` | 正式 128×32；fast 候选 64×16 待 benchmark。自定义范围尚未确定；谱 mode=4 限制须检查 |
| gamma / Mach | IdealGas 默认 γ=1.4，初始化 `MACH=6.0` | 首期固定 γ=1.4、Mach=6；Mach 不可通过修改源常量开放 |
| CFL / T | `locked_protocol()` 内使用固定 CFL=0.05、T=0.08 | 论文固定；fast T=0.04 是候选。其他值需包装层计算 dt，非现有 formal CLI 参数 |
| epsilon | 当前 Case 8 无此入参 | 不开放；含义未被需求唯一指定，返回 unsupported/clarification，禁止映射其他 Case epsilon |
| Gate | 目标 flux 无 gate 入参 | 不开放 V1 Acoustic/Pressure/Ungated 选项；固定已核实的 unified 方法路径 |
| Reconstruction | finite_volume_rhs 为一阶 Cartesian FV | 固定 `FIRST_ORDER`；MUSCL/WENO 等未支持 |
| integrator / dt strategy | SSP-RK3 stage guards；初态波速推导固定步长 | 固定 SSP_RK3；paper 固定正式协议；fast/custom 等待包装层 |
| snapshot_interval | source 只有既定 checkpoint fractions | 新驱动、数量/容量上限尚未实现，不开放自由间隔 |

Case 8 的物理扰动分为：

1. **前沿起伏**：`x_s = 0.5 + 0.0125 sin(8πy)`，幅值 0.0125（model length）、4 个波长、一网格宽 tanh 过渡。
2. **切向速度种子**：`a_v H_smooth exp(-((x-x_s)/0.04)^2) sin(8πy+0)`；`a_v = 0.01 sqrt(γ p_pre/ρ_pre)`。0.01 是相对上游声速的幅值因子，不是前沿位移。

因此 epsilon=0.0001 无法从本 Case 的源定义确定为上述哪一种；当前明确结论是“歧义且未支持”，而非遗漏默认值。未来如开放需使用不同的具名字段并验证初始化确实变化。

## 3. 正式模板协议

| template_id（拟登记） | q_aa | q_at |
| --- | ---: | ---: |
| case8.paper.A_u | 13.2 | 0 |
| case8.paper.B_u | 3.96 | 0 |
| case8.paper.C_u | 13.2 | 0.396 |
| case8.paper.D_u | 3.96 | 0.396 |

四者共同：128×32，domain x/y=[0,1]，Mach=6，γ=1.4，CFL=0.05，T=0.08，上述两种扰动，x 下界 pre-shock inflow、上界 outflow、y periodic，一阶 FV，SSP-RK3 无 positivity clipping/人工黏性，完整协议 ID `CANONICAL_STRONG_SHOCK_TRANSVERSE_PERTURBATION`。

原步长规则：初态 `rate=max(|u|/dx+|v|/dy+c/dx+c/dy)`，`raw_dt=CFL/rate`，`steps=ceil(T/raw_dt)`，`dt=T/steps`。正式记录 1912 步、dt=`4.184100418410042e-05`。fast/custom 必须重新计算，不能硬编码 1912。checkpoint rounding 也要保持源规则。

## 4. 输出能力与诊断定义

| 输出 | 来源/定义 | 新 Run 可用性 |
| --- | --- | --- |
| 保守状态、ρ、p、速度、Mach | state `[ny,nx,4]`；Euler gas 派生 | P2 落盘、P4 派生验证待实现 |
| dotE_bg/aa/at | observer 遍历 residual faces；每条 x-face 权重 dy、y-face dx | 算法存在，运行输出未接通 |
| E_bg/aa/at | 每步 dt×(s0/6+s1/6+2s2/3)，再按 accepted step 累计 | 不可用终态 Pi 替代全轨迹累计 |
| native Pi、J、pt_z_norm2 | x faces `[ny,nx+1]`；y faces `[ny,nx]` | periodic y seam 计一次，排除重复 ny slot；不得直接 reshape 到 cell |
| localization | 初始解析前沿 `abs(x-x_s(y))<=0.08`；domain/front face measure 积分及 RK 时间权重 | formal 实现可参考，包装层待复用 |
| front / width | pressure p50 最近预期前沿 crossing；p10/p90 最近该 p50，次序不合法时 NaN | 坐标和 model length；缺失不能回填 0 |
| Front RMS | `front_displacement = front - row mean` 后 RMS | 检测合法性检查待实现 |
| HF energy/fraction | `rfft(values)/N`，energy=abs²，high k>4；fraction 除非零模总能量 | 源函数会 nan_to_num，包装层须先登记无效前沿，不能悄悄把缺失谱当真实零 |

formal 验收容差：stage additivity abs ≤`3e-11`；q_at=0 时 abs(dotE_at)、abs(pi_at_max) ≤`3e-13`。参考终态比较源规则为 bitwise equality，并记录 max abs/rel difference。P2 必须明确环境差异与实际比较结果，不在 P0 宣称复现成功。

## 5. Case Registry / Parameter Capability Registry 设计

CaseRegistry 项：`case_id`、`label`、`capability_revision`、`source_manifest_revision`、`protocol_id`、`template_ids`、`input_validation_status`、`execution_status`、`limitations`。P0 对 Case 8 为 `PLANNED` / `NOT_IMPLEMENTED`，API 尚未注册。

ParameterCapability 项：`field_path`、`scope(INPUT/OUTPUT)`、`support(FIXED/CANDIDATE/UNSUPPORTED)`、`verified_values`、`candidate_values`、`unit`、`source_refs`（清单相对路径+symbol）、`required_stage`、`validation_ready`、`execution_verified`、`reason`。输入范围和输出能力各自登记；“可以验证配置”不得推出“可以启动求解”。

P1 GET /cases 从该 registry 生成表单；所有 capability 必须带版本。固定值可以展示但不可编辑；候选在完成对应阶段之前不可启动；未知字段拒绝。fast 候选不标已 benchmark，不提前设置看似精确的性能/资源上限。

## 6. 当前运行环境障碍

`.venv` Python 3.12.9，NumPy 2.5.3，PyYAML 6.0.3；SciPy 和 Matplotlib 未安装。诊断/production 模块导入链涉及通用实验和绘图辅助依赖，因此原封装无法直接视为可运行。P2 应明确最小 worker 导入链、锁定所需依赖，再在软件环境安装必要包或使用带来源哈希的受控镜像；P0 不安装科研包，不改科学源码。具体版本也保存在清单中。

静态依赖审计不能证明动态导入实际选中了这些文件。P2 必须在隔离子进程中核实每个被加载模块的 `__file__` 和哈希，且不接受 sys.path 从归档副本选中的同名模块。写入策略见 [03_SOLVER_BINDING.md](03_SOLVER_BINDING.md)。

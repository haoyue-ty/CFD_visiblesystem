# ShockPath V1 — Canonical Data Schema

版本：`1.0.1` · Phase 4 · 2026-10-01（Asia/Shanghai）。状态：**FROZEN**。人工审核：`PHASE4_REVIEW=PASS_WITH_MINOR_FIXES`。与 [04_SYSTEM_ARCHITECTURE.md](04_SYSTEM_ARCHITECTURE.md)、[06_API_CONTRACT.md](06_API_CONTRACT.md) 联合冻结。本文是字段和校验设计，不是已实现的 Pydantic 模型或数据库。

# 1. Scope and schema principles

完整继承 Scope、正式 Phase1 inventory、PRD 和已冻结 IA；正式 inventory 位于 `D:\比赛\数媒\data`。软件目录的副本不替代正式索引。用户追加账号注册设计单列第16节；不改上游、四导航、九模板、五页首切片，不把登录变成 Replay 前置条件。

唯一数值链：`Scientific Source Format → Scientific Adapter → Canonical Application Model → API DTO → Frontend`。原 CSV/NPY/NPZ 不直接成为 API schema。BACKEND_STACK=`Flask + Python`；规范实体和请求/响应均以 Pydantic 2 为后续唯一类型源。

模型必须保留 provenance、verification、time/spatial granularity、units、mask、scope、limitations、source hash。不插值、不补帧、不修原数据；UNKNOWN/MISSING/NOT_APPLICABLE 不等于零。没有核定 SI 映射，不标 Pa、m/s、J。

## 1.1 Field notation

表中 `name:Type` 是字段规范，非程序实现。无 `?` 的字段必填；`?` 仅用于结构性可选字段，不能省略未知科学事实。`List<T>`、`Dict<K,T>`、泛型只代表类型。所有未声明字段禁止；枚举为大小写敏感字符串。JSON 中科学数值必须有限；不接受 NaN/Infinity、bool 当整数、数字字符串自动变数字。时间戳为含时区 RFC3339，实际日志无日期时使用 UNKNOWN。

| Type | 精确定义 |
| --- | --- |
| ID | 受 registry 管理的稳定非空字符串；不是路径或请求方任意文本 |
| Number / Integer | finite JSON number / JSON integer；下限按字段校验 |
| Fact<T> | discriminated union：`{state:KNOWN,value:T}` 或 `{state:UNKNOWN\|MISSING\|NOT_APPLICABLE,reason:string}`；后者禁止 value；不使用裸 null |
| HashFact | `Fact<string>`；KNOWN 时为64位小写 SHA-256 hex |
| ScientificLimitation | `id:ID, code:string, description:string, affected_refs:List<ID>, severity:INFO\|WARNING\|BLOCKING` |
| UnitSpec | `id:ID, system:MODEL\|DIMENSIONLESS\|UNKNOWN, quantity:string, label:string, si_mapping:Fact<string>` |
| ComplexValue | `real:Number, imag:Number`；JSON 不用 complex literal |
| Availability | `AVAILABLE\|PARTIAL\|MISSING\|UNSUPPORTED\|ERROR`，运行时资源可用性 |
| DataOrigin | `FROZEN_PRODUCTION\|VERIFIED_PRODUCTION\|VERIFIED_POSTPROCESS\|DIAGNOSTIC_RERUN\|MOCK\|SCHEMATIC\|LIVE_DEMO`；来源类别，不是认证等级 |

UNKNOWN=尚未确定事实；MISSING=所需事实/资产已知缺失；NOT_APPLICABLE=协议不适用；真实数值0=`KNOWN,value:0`。MODEL 单位与 SI UNKNOWN 可同时成立。字段自身失败通常由 ResourceSlot 表达，不用 `Fact<...>` 遮盖整个失败请求。

# 2. Independent status models

## 2.1 VerificationStatus

`FROZEN_VERIFIED|VERIFIED_NOT_FROZEN|DERIVED_VERIFIED|AVAILABLE_UNVERIFIED|PARTIAL|MISSING|LEGACY|SUPERSEDED|NOT_APPLICABLE`，严格继承 Phase1。

`Verification = {status:VerificationStatus, basis:List<string>, verified_at:Fact<timestamp>, observation_at:Fact<timestamp>, evidence_refs:List<ID>}`。status 是证据状态；basis 说明 hash match、format check、已有专项审计等实际范围。FROZEN_VERIFIED 不等于所有主张被重证。多来源对象不能用一个子资产 frozen 覆盖全部；混合来源 aggregate 使用 PARTIAL 并保留子项 Verification，或使用已确立的整体审计记录，不能推断晋级。

正式数值入口只用有明确核验依据的 FROZEN_VERIFIED / VERIFIED_NOT_FROZEN / DERIVED_VERIFIED 子结果；PARTIAL composite 可包含这些子项。AVAILABLE_UNVERIFIED/LEGACY/SUPERSEDED 只在 Evidence 可查。MOCK/SCHEMATIC 必须 NOT_APPLICABLE，LIVE_DEMO 不自动 frozen。

## 2.2 CapabilityStatus and delivery

CapabilityStatus=`SUPPORTED|PARTIAL|MISSING|UNSUPPORTED`。支持程度与 Verification/Availability 独立。软件交付 `DeliveryStatus=PLANNED|IMPLEMENTED`，不把未写 adapter 标科学 MISSING。UI loading 不属于科学 schema。

## 2.3 ResourceSlot<T> and errors

| Variant | 必填字段 | 禁止/约束 |
| --- | --- | --- |
| AVAILABLE | `availability, value:T` | 无 error/缺失替代值 |
| PARTIAL | `availability, value:T, issues:List<ErrorBody>` | issues非空；value自身必须能表达已存子项 |
| MISSING / UNSUPPORTED / ERROR | `availability, error:ErrorBody` | 无 value；不得生成零数组 |

`ErrorBody = {domain:SYSTEM|SCIENTIFIC|ACCOUNT, code:string, message:string, target:ErrorTarget, retryable:boolean, details:List<ErrorDetail>, evidence_refs:List<ID>}`。

`ErrorTarget = {resource_type:string, identity:Fact<ID>}`。`ErrorDetail = {field:string, issue:string, allowed_values:List<string>}`。不返回 raw input、堆栈、绝对路径、密码、验证码或 SMTP 授权码。具体 code/HTTP 映射见06第5节；同模型也用于局部失败。

# 3. Stable identity and revisions

| Identity | 设计与例子 |
| --- | --- |
| experiment_id | 六个固定值：`case8, gate, entropy-closure, spectrum, modal-validation, cylinder`；Spectrum独立于Case8 |
| config_id | 在experiment内唯一，如 `D_u`、`Pressure`、`D_u-cfl-0.05`、`q-0.396`；不假设跨实验同名即同运行 |
| result_id | registry分配的稳定、带科学选择/语义的ID，例如 `case8.D_u.snapshot.6.density`；不是源路径、资产hash或显示名 |
| asset_id | 沿用 Phase1 `asset_*` 和 `missing_*`；物理副本不自动合并 |
| evidence_id | 应用registry分配稳定ID，如 `ev.case8.D_u.snapshot.6.density`；本文是拟定应用ID，不声称Phase1已有此ID |
| array_id | result内唯一，如 `density, pi_at_x_faces, pi_at_y_faces, eigenvector`；只能registry允许值 |
| registry_revision / data_revision | 显式选择清单版本 / 当前数据集指纹；不由前端猜文件mtime |
| release_id | `Fact<ID>`；未发布为NOT_APPLICABLE，不虚构bundle |

result ID固定到canonical source selection及semantic。换源/语义不得原位覆写同一结果；生成新result或明确新revision并保留历史关系。数据漂移不重新hash后冒充同一个 frozen result。公开 identity 和内部 locator 分离；path/hash只是provenance。

# 4. Project, experiments and capability registries

## 4.1 Core metadata entities

| Entity | 所有字段 |
| --- | --- |
| ProjectInfo | `schema_version:string, project_id:ID, name:string, architecture_style:string, api_version:string, registry_revision:ID, data_revision:ID, release_id:Fact<ID>, replay_primary:boolean, live_demo_priority:string, top_level_navigation:List<string>, page_template_ids:List<ID>, experiments:List<ExperimentRef>, account_extension:AccountFeatureInfo, limitations:List<ScientificLimitation>` |
| ExperimentRef | `experiment_id:ID, name:string, delivery_status:DeliveryStatus` |
| Experiment | `schema_version:string, id:ID, name:string, scientific_family:string, description:string, capabilities:List<ExperimentCapability>, available_configs:List<ExperimentConfig>, status:Availability, delivery_status:DeliveryStatus, limitations:List<ScientificLimitation>, evidence_refs:List<ID>, related_experiment_ids:List<ID>` |
| ExperimentConfig | `id:ID, experiment_id:ID, name:string, parameters:List<ParameterValue>, protocol:ProtocolSpec, verification:Verification, limitations:List<ScientificLimitation>, evidence_refs:List<ID>` |
| ParameterValue | `name:q_aa\|q_at\|gate\|CFL\|epsilon\|ell\|mode, value:Fact<Number\|string>, unit:UnitSpec`；数值和enum参数类型按name校验 |
| ProtocolSpec | `method_name:Fact<string>, method_hash:HashFact, grid:Fact<GridSpec>, integrator:Fact<string>, reconstruction:Fact<string>, final_time:Fact<Number>, boundary_scope:Fact<string>, protocol_asset_refs:List<ID>` |
| GridSpec | `coordinate_system:CARTESIAN\|CURVILINEAR_POLAR, dimensions:List<AxisSize>, extent:List<AxisExtent>` |
| AxisSize / AxisExtent | `{axis:string,size:Integer>0}` / `{axis:string,lower:Number,upper:Number}`；lower<upper |

数值experiment共有上表形状，配置只表达该协议实际参数；epsilon不适用的Case8不填近1D数值。Closure不能从文件夹名推CFL。Gate是matched配置，不复用Case8四config。Spectrum配置为四q；Modal Validation config为24个run ID，不引入Case8配置。

## 4.2 ExperimentCapability

所有字段：`id:ID, experiment_id:ID, task:string, status:CapabilityStatus, available_for_configs:List<ID>, config_support:List<ConfigCapability>, controls:List<ControlSpec>, tab_policy:TabPolicy, result_refs:List<ID>, limitations:List<ScientificLimitation>, evidence_refs:List<ID>`。

`ConfigCapability = {config_id:ID,status:CapabilityStatus,reason:string,result_refs:List<ID>}`。

`ControlSpec = {name:string,kind:ENUM|RECORDED_INDEX,allowed_values:List<string>,combination_registry_ref:Fact<ID>}`。不是连续区间自由生成；combination registry提供有限组合，不将各列任意笛卡尔相乘。

`TabPolicy = {tab_id:string,visible_for_family:boolean,disabled_for_configs:List<ID>,unsupported_deep_link_behavior:EXPLAIN}`。family无任务隐藏tab且Overview说明；配置缺失保留禁用tab；runtime错误不动态删tab。

| Experiment | 合法组合与capability要求 |
| --- | --- |
| Case8 | A/B/C/D；snapshot6、history1912；allocation family PARTIAL，D_u SUPPORTED，A/B/C MISSING |
| Gate | Acoustic/Pressure/Ungated；allocation SUPPORTED，history playback UNSUPPORTED |
| Closure | B_u .05；D_u .2/.1/.05/.025五个run；stage/step分别SUPPORTED，空间trajectory MISSING |
| Spectrum | q0/.132/.264/.396×ell0…16；spectrum/modes SUPPORTED；validation PARTIAL子集；serialized matrices MISSING |
| Modal Validation | mode1/4/8/12×q0/.396×eps1e-4/1e-5/1e-6；24run；full CFD spatial history MISSING |
| Cylinder | A/B/D；instantaneous5、scalar9757；allocation PARTIAL，sectors/band SUPPORTED，cumulative2D MISSING |

Near-1D五epsilon scan不注册为Experiment。机制示意是内容实体，非numerical schema registry。

# 5. ScientificResult and provenance

所有正式数值实体持有 `result:ScientificResult`；同一ID的header在metadata、array、Evidence中必须相同。

`ScientificResult = {schema_version:string,result_id:ID,experiment_id:ID,config_id:ID,semantic_id:ID,data_origin:DataOrigin,availability:AVAILABLE|PARTIAL,time:TimeSpec,scope:ScopeSpec,unit:UnitSpec,verification:Verification,provenance:ProvenanceRef,limitations:List<ScientificLimitation>}`。

`ProvenanceRef = {evidence_refs:List<ID>,source_asset_ids:List<ID>,registry_revision:ID,data_revision:ID,release_id:Fact<ID>,source_drift:Fact<boolean>}`。真实科学图evidence_refs非空；MOCK/schematic指自身说明依据，不能套正式数据证据。

`ScopeSpec = {id:ID,description:string,boundary_scope:Fact<string>,spatial_domain_ref:Fact<ID>,mask_refs:List<ID>,definition_refs:List<ID>}`。相同semantic_id但scope不同不能自动比较。source_drift仅描述源码/依赖漂移；数据漂移状态逐SourceAsset保留并阻止数值读取，见第14节。

# 6. Time schema and recorded selectors

`TimeSpec = {sampling:STATIC|TERMINAL|MULTI_SNAPSHOT|PER_STEP|PER_STAGE,accumulation:NONE|TRAJECTORY_INTEGRATED|STEP_INCREMENT|STAGE_WEIGHTED_INCREMENT,physical_time:Fact<Number>,interval:Fact<TimeInterval>,step_index:Fact<Integer>,stage_index:Fact<Integer>,snapshot_index:Fact<Integer>,index_convention:string}`。

`TimeInterval = {start:Number,end:Number}`，start≤end。本设计把“如何采样”和“积分覆盖范围”分两轴；TRAJECTORY_INTEGRATED作为accumulation明确保留，不伪装为另一时间播放轴。Gate sampling STATIC + accumulation TRAJECTORY_INTEGRATED；Case8 D_u map TERMINAL + TRAJECTORY_INTEGRATED；history PER_STEP + TRAJECTORY_INTEGRATED；instantaneous snapshot MULTI_SNAPSHOT + NONE。

| 编号 | 规范规则 |
| --- | --- |
| snapshot_index | USER_VISIBLE_1_BASED_RECORDED_INDEX；Case8 ∈ {1,2,3,4,5,6}，Cylinder ∈ {1,2,3,4,5}；永远不允许0，不按任意time插帧 |
| step_index | completed accepted steps；初始保存帧可为 snapshot_index=1、step_index=0；history endpoint第一条为1；ScalarPoint额外source_step_index保留原日志编号 |
| stage_index | canonical统一0/1/2；Closure原stage1/2/3在source_stage_index保留；Case8原s0/s1/s2不变 |
| scalar physical_time | Case8取time_end；Closure step取time_np1；stage取原t_stage_or_step_time并注明其含义，不猜SSP-RK3物理stage时刻 |

Case8历史CSV的首行 `step=0` 是step记录编号，对应完成第1步endpoint；snapshot首个非零checkpoint的step为已完成步数。因此 adapter explicit映射`step_index=source_step_index+1`，保留source index及time_start/time_end；后续必须检查每行时间/计数与协议，不在未核实Cylinder编号前套同一加一规则。

SNAPSHOT_INDEX_CONVENTION = USER_VISIBLE_1_BASED_RECORDED_INDEX。snapshot_index 与 step_index 是两套编号；第1张保存帧若对应初态，其 snapshot_index=1、step_index=0，永远不出现 snapshot_index=0。不修改已有数据或重新编号科研文件；/snapshots/{snapshot_index} 仍接受用户可见1-based编号。

`SnapshotAlignment = {experiment_id:ID,config_id:ID,selection_policy:NEAREST_RECORDED|PINNED,selected_scalar_step:Integer,selected_scalar_time:Number,displayed_snapshot_id:ID,displayed_snapshot_index:Integer,displayed_snapshot_time:Number,signed_time_delta:Number,limitations:List<ScientificLimitation>}`。

NEAREST_RECORDED=min绝对时间差；严格同距选早time，再选小snapshot_index。delta=displayed−selected。不增加epsilon容差制造同距。换config按新真实scalar endpoints匹配目标时间（同距早time/小step），再匹配新snapshot；显示重新匹配说明。PINNED只使用明确指定当前配置的真实帧。

# 7. Spatial, mask and array schemas

## 7.1 SpatialDomain

所有字段：`id:ID,coordinate_system:CARTESIAN|CURVILINEAR_POLAR|FOURIER_PROFILE|ANGULAR,location_type:CARTESIAN_CELL|CARTESIAN_X_FACE|CARTESIAN_Y_FACE|CARTESIAN_ROW|CYLINDER_RADIAL_FACE|CYLINDER_ANGULAR_FACE|CYLINDER_ANGULAR_SECTOR|CYLINDER_FRONT_BAND|PROFILE_CELL,shape:List<Integer>,axes:List<AxisDescriptor>,extent:List<AxisExtent>,measure_convention:MeasureConvention,boundary_scope:Fact<string>,geometry_ref:Fact<ArrayRef>,evidence_refs:List<ID>`。

`AxisDescriptor = {name:string,size:Integer,coordinate_values:Fact<List<Number>>,coordinate_array_ref:Fact<ArrayRef>,unit:UnitSpec}`。KNOWN坐标值/array_ref二选一；都未知时不得假称可绘真实几何。component/eigenvector length不冒充空间轴。

`MeasureConvention = {id:ID,description:string,integral_rule:string,measure_parameters:List<NamedFact>,includes_time_weights:boolean,includes_spatial_measure:boolean}`。`NamedFact = {name:string,value:Fact<Number|string>}`。

Cylinder原生曲面必须保留已存坐标/几何；缺几何显示MISSING，不能按均匀r坐标绘stretch O-grid。snapshot face shape由原member核定，不推32×129用于圆柱。

## 7.2 MaskSpec

所有字段：`id:ID,type:GATE_CELL_SHOCK_WINDOW|CASE8_NATIVE_FACE_SHOCK_WINDOW|SPECTRUM_FIXED_SHOCK_CELLS|CYLINDER_FIXED_FRONT_BAND,domain_refs:List<ID>,definition:string,parameters:List<NamedFact>,index_sets:List<MaskIndexSet>,mask_array_refs:List<ArrayRef>,scope:ScopeSpec,verification:Verification,evidence_refs:List<ID>`。

`MaskIndexSet = {axis:string,indices:List<Integer>,index_base:0|1}`。Case8 x/y masks分开，Gate cell mask独立；Spectrum固定x cell58…66、0-based；Cylinder固定A_u authoritative front径向±.16，仅原定义角域，禁止称全周front等价。

Gate fixed initial front `x_s(y)=.5+.0125*sin(8*pi*y)`、half width .08；Case8也可有±.08，但native-face enumerator和boundary_scope不同，mask ID不能共用。Cylinder band是cumulative。索引集、hash、source未知时Fact UNKNOWN，不臆测。

## 7.3 ArrayDescriptor / ArrayRef / ScientificArray

| Model | 字段 |
| --- | --- |
| ArrayDescriptor | `array_id:ID,dtype:float64\|int64\|bool\|complex128,shape:List<Integer>,order:C,axes:List<string>,encoding:FLAT_JSON,element_count:Integer` |
| ArrayRef | `result_id:ID,descriptor:ArrayDescriptor`；API URL由06唯一规则生成，不包含file path |
| ScientificArray | `result:ScientificResult,descriptor:ArrayDescriptor,values:List<Number\|Integer\|boolean\|ComplexValue>` |

element_count=各shape乘积；scalar shape=[]时count=1。values按C-order扁平化；complex128每元素={real,imag}；其余按dtype严格校验，不允许异构数组。二维shape [32,128]长度4096，xface[32,129]长度4128。字段metadata返回ArrayRef；选定数组才通过06数组endpoint加载全精度ScientificArray。数组的result/time/scope/verification与FieldDescriptor一致，不能靠数组文件名判断。

Mask bool array与coordinate array同样受控引用，分别有正确semantic_id/验证/来源，不在浏览器重新生成科学mask。显示overlay不改变值。API不给任意NPZ member浏览或download科研根。

# 8. Snapshots, scalar series and metrics

| Entity | 所有字段 |
| --- | --- |
| FieldSnapshot | `result:ScientificResult,snapshot_id:ID,snapshot_index:Integer,step_index:Integer,physical_time:Number,grid:GridSpec,fields:List<FieldDescriptor>` |
| FieldDescriptor | `field_id:ID,label:string,result:ScientificResult,domain:SpatialDomain,array_ref:ArrayRef,mask_refs:List<ID>` |
| SnapshotIndex | `experiment_id:ID,config_id:ID,snapshot_count:Integer,items:List<FieldSnapshot>`；只metadata/ref，无field values |
| ScalarPoint | `point_index:Integer,step_index:Fact<Integer>,stage_index:Fact<Integer>,source_step_index:Fact<Integer>,source_stage_index:Fact<Integer>,physical_time:Fact<Number>,interval:Fact<TimeInterval>,value:Fact<Number>` |
| ScalarSeries | `result:ScientificResult,series_id:ID,label:string,total_point_count:Integer,points:List<ScalarPoint>,page:PageWindow,aggregation:NONE\|CUMULATIVE\|STEP_INCREMENT\|STAGE_AGGREGATE,source_column:string,definition_id:ID` |
| PageWindow | `offset:Integer>=0,limit:Integer>0,returned_count:Integer>=0,total_count:Integer>=0,has_more:boolean`；total_count=total_point_count；returned_count=len(points) |
| EntropyHistory | `experiment_id:ID,config_id:ID,series:List<ScalarSeries>,stage_aggregate_refs:List<ID>,snapshot_alignment:Fact<SnapshotAlignment>,limitations:List<ScientificLimitation>,evidence_refs:List<ID>` |
| Metric | `result:ScientificResult,metric_id:ID,value:Fact<Number>,definition_id:ID,detector:Fact<DetectorSpec>,time_scope:TimeSpec,display_label:string,resolution_limit:Fact<Number>` |
| DetectorSpec | `id:ID,name:string,definition:string,parameters:List<NamedFact>,evidence_refs:List<ID>` |
| MetricCollection | `experiment_id:ID,config_id:ID,items:List<ResourceSlot<Metric>>,evidence_refs:List<ID>` |

ScientificResult已经提供unit/scope/source/verification；Metric.time_scope必须等于result.time，不制造第二时间口径。definition_id和detector均可查询，见第15节。Case8 Flow六density/pressure/front保证已存；其他字段由字段列表声明。native-face endpoint与corrected flow来源/核验不同：每field独立header；如果一个snapshot同时列两类字段，composite verification=PARTIAL并说明混合范围。API字段缺失返回typed error，不填0。

## 8.1 Semantic registry

| semantic_id / definition_id | 原字段或确立定义 | 采样、积分、单位和限制 |
| --- | --- | --- |
| `E_bg_cumulative`, `E_aa_cumulative`, `E_at_cumulative` | Case8/Cylinder已存E_*列；Phase1 E_at | PER_STEP、CUMULATIVE、model integrated entropy；fixed face/boundary scope |
| `E_bg_step`, `E_aa_step`, `E_at_step` | Case8 deltaE_*；Closure E_*_step | PER_STEP、STEP_INCREMENT；不是累计曲线本身 |
| `Pi_at_instantaneous` | 单状态face `0.5*q_at*J*norm(P_t z)^2` | endpoint MULTI_SNAPSHOT、NONE、model entropy rate；未存stage场 |
| `Pi_at_rate` | 原dotE_at_s*域积分率列 | PER_STEP已存stage aggregate，用stage_index辨别；不是空间场 |
| `Pi_at_stage_weighted` | dt*(dotE_s0/6+dotE_s1/6+2*dotE_s2/3) | PER_STEP、STAGE_WEIGHTED_INCREMENT；一个step一条，可追溯对应deltaE |
| `Gate_cell_Pi_at_integrated` | Gate Pi_at.npy | STATIC+TRAJECTORY_INTEGRATED，cell含测度，sum=E_at，不再乘dx/dy/dt |
| `Case8_face_Pi_at_integrated` | D_u冻诊断map | TERMINAL+TRAJECTORY_INTEGRATED；dy*sum(xfaces)+dx*sum(yfaces)=E_at；不是production原生输出 |
| `Cylinder_sector_E_at_integrated` | channel_at[16] | STATIC+TRAJECTORY_INTEGRATED，interior-only，sector和total budget口径相同 |
| `cylinder_front_band_fraction` | shock_at/sum(channel_at) | fixed A_u ±.16 cumulative band；不是final instantaneous rate |
| `allocation_fraction` | E_at/(E_bg+E_aa+E_at) | dimensionless FRACTION；分母0为NOT_APPLICABLE(reason=ZERO_DENOMINATOR) |
| `gate_shock_window_fraction` | sum(saved cell within fixed mask)/E_at | Gate cell mask，不等于Case8 face localization |
| `case8_J2_face_localization` | face/time/RK加权窗内份额 | native-face enumerator、原scope，不能用derived cell sum替代 |
| `cylinder_angular_fraction` | channel_at[bin]/E_at_int | 16bins，fraction，不是完整二维图 |
| `spectral_abscissa` | max(real(lambda))，512/block | STATIC、inverse model time；允许正值/左右移 |
| `delta_alpha_q0` | alpha(ell,q)−alpha(ell,0) | 显式baseline同base、同ell、q0；禁止frontend自己挑baseline |
| `case8_front_RMS` | p50 front displacement关于均值RMS | model length；非velocity RMS |
| `case8_front_high_k_energy` / `case8_transverse_high_k_energy` / 相应fraction | rfft(signal)/N、k>seed4；fraction分母k≥1能量 | signal必须标识，energy与fraction分开，非Cylinder HF-RMS |
| `cylinder_front_HF_RMS` / `cylinder_high_angular_energy` | 原圆柱detector统计 | model length / length²；阈值/检测器来自source，不猜与Case8相同 |
| `case8_width` | row p10-p90 crossing distance、expected p50 anchor | model length；cells-normalized另definition，不能只换label |
| `cylinder_centerline_width` / `cylinder_front_mean_width` | radial bow-front p10-p90 detector | 不互换，B/D detector floor limitation；nominal dr不是error bar |

以上引用 Phase1 §7 的19项科学语义及其原资产。后续新增semantic必须同时新增definition、scope/units、来源和回归依据。不得把这些量统一叫`pi_at`。step累加若后续确需派生，仅adapter按显式processing定义生成，不让frontend累加获得正式新证据状态。

# 9. Allocation model — discriminated representations

`AllocationResult`是以下四variant union，discriminator=`representation_type`。共同字段：`result:ScientificResult,representation_type,summary:AllocationSummary`。

| Variant / Entity | 额外字段及约束 |
| --- | --- |
| CELL_FIELD / AllocationField | `fields:List<FieldDescriptor>`；Gate一cell场shape[32,128]，积分测度已经包含 |
| FACE_FIELD / AllocationField | `fields:List<FieldDescriptor>`；Case8 D_u xface[32,129]与yface[32,128]，不能合成重叠cell当积分权威 |
| ANGULAR_SECTORS / SectorAllocation | `sector_count:16,bin_edges:ArrayRef,channel_arrays:List<ChannelArray>,sector_fractions:List<Fact<Number>>,front_band_summary_ref:ID`；edges17、每channel16 |
| REGION_SCALAR / RegionAllocation | `region_mask:MaskSpec,integrated_value:Fact<Number>,fraction:Fact<Number>,denominator_result_id:ID`；Cylinder band仅scalar，无2D数据 |

`ChannelArray = {channel:bg|aa|at|total,array_ref:ArrayRef}`。

`AllocationSummary = {total_budget:ResourceSlot<Metric>,inside:ResourceSlot<Metric>,outside:ResourceSlot<Metric>,fraction_format:FRACTION,mask_refs:List<ID>,measure:MeasureConvention,spatial_cumulative_curve:ResourceSlot<SpatialCurve>,evidence_refs:List<ID>}`。

`SpatialCurve = {result:ScientificResult,axis:string,coordinates:ArrayRef,cumulative_fraction:ArrayRef,definition_id:ID}`，是空间分配累积曲线，不是保存时间movie。Gate曲线按已确立的axis/protocol处理；如只存map、曲线需派生，必须显式processing与回归后生成，未完成时slot MISSING且绝不伪称已有verified curve。

summary inside/outside Metric可以是fraction或原integrated budget，须semantic/definition精确说明；UI不能从字段名自行推单位。Cylinder sectors没有对应二维inside/outside map；summary只引用band标量，sector visualization不能猜band几何。E_at=0时fraction Fact NOT_APPLICABLE，保留已存channel值0而非杜撰全零累计图。

`GateRegistry = {experiment_id:gate,configs:List<ExperimentConfig>,map_shape:[32,128],comparison_id:ID,evidence_refs:List<ID>}`。

`GateComparison = {comparison_id:ID,gate_ids:List<ID>,approximately_matched:boolean,allocations:List<ResourceSlot<AllocationResult>>,shared_extent:List<AxisExtent>,shared_color_scale:Fact<ColorScaleSpec>,budget_match_error:Fact<Number>,limitations:List<ScientificLimitation>,evidence_refs:List<ID>}`。

`ColorScaleSpec = {minimum:Number,maximum:Number,transform:LINEAR,scope:string}`；service仅用本次真实三map给共同渲染范围，此范围不是科学新验证；任一map失败scope写可用子集且comparison PARTIAL。budget_match_error的definition由Evidence说明，不把三组E_at写成完全相等。

# 10. Entropy closure

| Entity | 字段 |
| --- | --- |
| EntropyClosureRun | `run_id:ID,config:ExperimentConfig,stage_point_count:Integer,step_point_count:Integer,stage_series_refs:List<ID>,step_series_refs:List<ID>,terminal_summary:List<ResourceSlot<Metric>>,limitations:List<ScientificLimitation>,evidence_refs:List<ID>` |
| ClosureRunRegistry | `experiment_id:entropy-closure,runs:List<EntropyClosureRun>` |
| ClosureHistory | `run_id:ID,granularity:PER_STAGE\|PER_STEP,series:List<ScalarSeries>,evidence_refs:List<ID>` |
| RefinementSummary | `comparison_id:ID,run_ids:List<ID>,metrics_by_run:List<RunMetrics>,refinement_slope:ResourceSlot<Metric>,limitations:List<ScientificLimitation>,evidence_refs:List<ID>` |
| RunMetrics | `run_id:ID,metrics:List<ResourceSlot<Metric>>` |

PER_STAGE: G、D_bg、D_aa、D_at、D_total、R_SD、eps_SD、R_decomp。PER_STEP: S_n、S_np1、DeltaS、E_bg_step/E_aa_step/E_at_step/E_obs_step、R_time_step、R_time_cumulative。R_SD=G+D_total；eps_SD无量纲，原定义归一化由definition提供。R_time_step不等R_time_cumulative，不把DeltaS_step当全程ΔS(T)。

合法run五个，D_u steps3451/6901/13802/27603分别对应CFL .2/.1/.05/.025；B_u .05=13802；stage points=3*steps。部分 inventory资产从`Du_cfl_005`误解析出CFL .005；canonical依冻结报告/协议与`cfl_rule`核定为.05，保留metadata correction processing记录，**不修改inventory或科研源**。adapter必须检查原协议run配置，不能扩大为任意CFL组合。

Stage logs的`t_stage_or_step_time`不能在未核定含义时改名成真实stage-state time；Fact physical_time可KNOWN原报告值，同时index_convention明确原日志时标，并在definition描述。没有空间stage trajectory；不能与其他vortex图同步。

# 11. Spectrum, complex eigenmodes and modal validation

| Entity | 所有字段 |
| --- | --- |
| SpectrumDataset | `dataset_id:ID,experiment_id:spectrum,base_result_id:ID,q_at_values:List<Number>,ell_values:List<Integer>,record_count:68,eigenvalues_per_block:512,saved_vectors_per_side:32,records:List<SpectrumRecord>,matrix_availability:MISSING,mask:MaskSpec,evidence_refs:List<ID>,limitations:List<ScientificLimitation>` |
| SpectrumRecord | `result:ScientificResult,record_id:ID,q_at:Number,ell:Integer,spectral_abscissa:Fact<Number>,leading_eigenvalue:Fact<ComplexValue>,leading_eigenvalue_ref:EigenvalueRef,eigenvalues_ref:ArrayRef,delta_alpha:Fact<Number>,baseline:SpectralBaseline,eigenmode_refs:List<ID>` |
| EigenvalueRef | `spectrum_record_id:ID,rank:Integer>=0`；排序与原ranks一致，alpha对应real最大，不依浏览器重新sort |
| SpectralBaseline | `dataset_id:ID,base_result_id:ID,q_at:0,ell:Integer,record_id:ID,definition:ALPHA_MINUS_SAME_ELL_Q0` |
| SpectrumCurve | `dataset_id:ID,q_at:Number,records:List<SpectrumRecord>`；严格17个ell |
| Eigenmode | `result:ScientificResult,eigenmode_id:ID,spectrum_record_id:ID,ell:Integer,q_at:Number,side:LEFT\|RIGHT,rank:Integer,branch_id:Fact<Integer>,eigenvalue:ComplexValue,normalization:NormalizationSpec,component:string,representation:COMPLEX_VECTOR\|PRIMITIVE_PROFILE,domain:SpatialDomain,values_ref:ArrayRef,mask:MaskSpec,localization:ResourceSlot<Metric>` |
| NormalizationSpec | `id:ID,definition:Fact<string>,phase_convention:Fact<string>,component_order:Fact<List<string>>,processing_ref:Fact<ID>,evidence_refs:List<ID>` |
| ValidationCombination | `run_id:ID,mode:Integer,q_at:Number,epsilon:Number,spectrum_record_id:ID,eigenmode_id:ID` |
| ValidationRegistry | `experiment_id:modal-validation,run_count:24,combinations:List<ValidationCombination>` |
| ModalValidationRun | `result:ScientificResult,run_id:ID,mode:Integer,q_at:Number,epsilon:Number,spectrum_record_id:ID,eigenmode_id:ID,point_count:33,history_result_id:ID,summary:ModalValidationSummary,limitations:List<ScientificLimitation>` |
| ModalValidationSummary | `sigma_LIN:Fact<Number>,sigma_RK3:Fact<Number>,sigma_CFD:Fact<Number>,absolute_discrepancy:Fact<Number>,relative_discrepancy:Fact<Number>,relative_discrepancy_format:FRACTION,relative_discrepancy_definition_id:ID,R2:Fact<Number>,fit_start:Integer,fit_end:Integer,fit_point_count:Integer,growth_rate_unit:UnitSpec,evidence_refs:List<ID>` |
| ModalValidationHistory | `result:ScientificResult,run_id:ID,total_point_count:33,points:List<ModalPoint>,page:PageWindow,summary:ModalValidationSummary` |
| ModalPoint | `step_index:Integer,physical_time:Number,amplitude:Fact<Number>,log_amplitude:Fact<Number>` |

q四档、ell0…16=68，每block512 eigenvalues；vector rank0…31、LEFT/RIGHT top32（不是512个vectors）。leading primitive profile只有实际存成员/已核验可追溯转换才可显示；禁止猜primitive component order、相位或normalization。未知normalization保持UNKNOWN并限制“比较振幅”，已有source normalization由adapter读取说明；frontend不能任意重归一化当正式量。

`delta_alpha`始终针对同common zero-residual base、同ell、q0。结果允许负/正/近零delta和alpha>0；不强制所有mode improved。mask固定x-cell58…66，不因q改变；localization值来自原定义/已核验处理，mode4/8不能因标题称shock-localized。

Fig13只mode1/4/8/12、q0/.396、epsilon1e-4/1e-5/1e-6；run ID建议`fig13.m08.q-0.396.eps-1e-5`。历史step0…32、33点；只能播放projected amplitude。summary原`relative_discrepancy_CFD_RK3`映射relative_discrepancy，fraction，无百分比暗转换；definition使用第11.1节已只读核定的冻结fit公式。fit_start/end指step inclusive，固定0/32，fit_count33。log幅值为第11.1节确认的natural log。增长率不是全谱envelope alpha。

### 11.1 Frozen definition binding

已只读核查冻结`cfd_validation.py`（asset_9e69ab916a06）：relative_discrepancy=`abs(sigma_CFD-sigma_RK3)/max(abs(sigma_RK3),1.0)`，分母带模型规范化下限1，不能改成单纯相对sigma或百分数；log_amplitude为natural log `ln(abs(projected coefficient))`。以上是已核定定义，实施必须绑定此源证据，不保留未核定公式作为默认。

同一冻结脚本确定Fig13扰动normalization：将right mode最大state-scaled分量旋转为实正，再令max(abs(r_ic)/S_c)=1；left vector保留原值，projection除以left/right inner product。此normalization仅用于该validation协议，不能冒充所有stored raw eigenvectors都按同一规则规范化。shape512为128×4保守分量向量；leading primitive amplitude profiles另有冻结asset_f53235bc1bf3（4×17×32×128×4），显示时按所选q/ell/rank取已有profile，不从图或未知component order猜值。本文只读源码解释，未运行脚本。

# 12. Cylinder and cross-flow

Cylinder A/B/D、O-grid nr32×ntheta128、r .5…8、stretch3、T2、9757标量；五instantaneous face checkpoints completed-step 0/2439/4878/7318/9757。times取原NPZ；不以round T/4替代。只承诺已存face字段、终态；不得声称五帧density/pressure全场齐全。

sector bins17edges、channel arrays16；front-band result是REGION_SCALAR，primary interior-only。没有 full trajectory 2D cumulative Pi_at，capability明确MISSING。sector/band与Case8 cumulative map不强制用一种Field。

`CylinderAllocationOverview = {experiment_id:cylinder,config_id:ID,sectors:ResourceSlot<AllocationResult>,front_band:ResourceSlot<AllocationResult>,cumulative_2d:ResourceSlot<AllocationResult>,limitations:List<ScientificLimitation>,evidence_refs:List<ID>}`，cumulative_2d固定MISSING、无value。

`CrossFlowComparison = {comparison_id:ID,left:CrossFlowSide,right:CrossFlowSide,comparability:List<ComparabilityRule>,ranking_policy:NO_UNIFIED_RANKING,limitations:List<ScientificLimitation>,evidence_refs:List<ID>}`。

`CrossFlowSide = {experiment_id:case8|cylinder,config_id:ID,protocol:ProtocolSpec,budget:ResourceSlot<MetricCollection>,metrics:ResourceSlot<MetricCollection>,allocation:ResourceSlot<AllocationResult>,front_band:ResourceSlot<AllocationResult>,snapshot_refs:List<ID>,history_refs:List<ID>,evidence_refs:List<ID>}`。

`ComparabilityRule = {left_definition_id:ID,right_definition_id:ID,status:DESCRIPTIVE_ONLY|COMPATIBLE_WITH_DECLARED_MAPPING,reason:string,mapping_ref:Fact<ID>}`。

V1服务端composite只组合真实typed子结果；两侧原定义/单位/mask/time/boundary_scope完整保留。默认descriptive-only；Case8 HF vs Cylinder HF-RMS、face-window vs radial-band、different-scope budget、detector-floor width无统一ranking。left front_band无此概念为NOT_APPLICABLE事实？由于slot没有N/A availability，此处用UNSUPPORTED error明确Case8没有Cylinder band任务；不把它写MISSING。A/B/C Case8累计map=MISSING，仍显示预算与metrics，外层200 PARTIAL。

# 13. EvidenceRecord and SourceAsset

| Entity | 所有字段 |
| --- | --- |
| EvidenceRecord | `schema_version:string,evidence_id:ID,result_ids:List<ID>,result_contexts:List<ScientificResult>,experiment_id:Fact<ID>,config_id:Fact<ID>,config:Fact<ExperimentConfig>,definitions:List<ScientificDefinition>,masks:List<MaskSpec>,method_name:Fact<string>,method_hash:HashFact,recorded_source_hash:HashFact,current_source_hash:HashFact,source_observations:List<SourceObservation>,source_assets:List<SourceAsset>,data_hash:HashFact,freeze_reference:Fact<FreezeReference>,processing:List<ProcessingRecord>,verification:Verification,limitations:List<ScientificLimitation>,source_drift:Fact<boolean>,created_at:Fact<timestamp>,verified_at:Fact<timestamp>,related_evidence_refs:List<ID>,superseded_by:Fact<ID>` |
| SourceAsset | `asset_id:ID,source_id:ID,source_display:string,relative_origin:Fact<string>,role:DATA\|CONFIG\|METHOD\|MASK\|ANALYSIS\|FREEZE\|MISSING_REFERENCE,format:string,recorded_data_hash:HashFact,current_data_hash:HashFact,data_drift:Fact<boolean>,verification:Verification,canonical_selected:boolean,limitations:List<ScientificLimitation>` |
| SourceObservation | `asset_id:ID,recorded_hash:HashFact,current_hash:HashFact,drift:Fact<boolean>,observation_at:Fact<timestamp>` |
| FreezeReference | `freeze_id:ID,manifest_asset_id:ID,recorded_at:Fact<timestamp>,hash:HashFact` |
| ProcessingRecord | `id:ID,kind:FORMAT_MAPPING\|METADATA_CORRECTION\|VERIFIED_DERIVATION\|DISPLAY_ONLY,description:string,input_asset_ids:List<ID>,definition_refs:List<ID>,processing_hash:HashFact,verification:Verification` |
| EvidenceIndexItem | `evidence_id:ID,result_ids:List<ID>,experiment_id:Fact<ID>,title:string,verification:Verification,source_drift:Fact<boolean>,limitations:List<ScientificLimitation>` |
| EvidenceIndex | `items:List<EvidenceIndexItem>,page:PageWindow` |
| ResultProvenance | `result_id:ID,provenance:ProvenanceRef,evidence_records:List<EvidenceRecord>` |

内部canonical SourceAsset另可持有`absolute_source_path:string`，只用于guarded locator；**公共DTO不含该字段**，表中公共字段用Pydantic allow-list投影，不依赖随意删除dict键。data_hash在单data资产时等原字节SHA；多资产Evidence若无已确立composite hash则UNKNOWN，不拿payload ETag、method hash或拼接资产hash冒充data hash。

recorded/current_source_hash只代表主method源；dependency漂移逐source_observations，source_drift对全部源依赖聚合，任何已确认drift为true、未确认为UNKNOWN而非false。SOURCE_DATA_DRIFT阻止数值API；Evidence仍能读取记录并显示原/current数据hash。源码drift且原数据hash一致可展示原结果及复现限制，不能宣称当前代码精确重跑。

created_at/verified_at只有已有日志/审计真实时间才KNOWN；本轮文档日期不是科学运行或验证日期。冻目录文件名不证明全部字段齐全。Missing Evidence可没有result_ids，config/experiment按实际Facts区分；来源不足图稿可供Evidence阅读，但不生成正式numeric result。

Evidence Detail的result_contexts仅header、无科学大数组；与result_ids一一对应，并内嵌config、definitions、masks以供P09独立深链显示grid/time/unit/scope/detector/处理依据。缺口/方法解释Evidence无数值result时列表空，config为适用的Fact；不强行创建numerical result。EvidenceService从同registry解析这些metadata，避免P09依赖用户先访问某plot；不得因呈现Evidence触发solver或加载所有科学数组。

# 14. API DTO / envelope binding

`ApiEnvelope<T> = {schema_version:string,request_id:ID,registry_revision:Fact<ID>,data_revision:Fact<ID>,availability:Availability,data?:T,error?:ErrorBody,issues:List<ErrorBody>}`。

AVAILABLE→data必填、无error、issues空；PARTIAL→data必填、无error、issues非空且嵌套slot可定位；MISSING/UNSUPPORTED/ERROR→error必填、无data、issues空。无registered revision的routing/account错误用Fact NOT_APPLICABLE或UNKNOWN，不能杜撰。Account成功不要求科学revision；请求ID服务端生成，不回显未校验header。

所有表中数值/metadata模型是public DTO，只有SourceAsset内部locator投影和账户存储模型需要另type。ScientificResult不是任意union替代，数组返回ScientificArray、列表返回专门模型，不把原始dict当schema。

| API DTO | 数据结构 |
| --- | --- |
| ExperimentList | `items:List<Experiment>`（仅六轻量metadata，不含科学数组） |
| ConfigList / CapabilityList | `{experiment_id:ID,items:List<ExperimentConfig>}` / `{experiment_id:ID,items:List<ExperimentCapability>}` |
| FieldResponse | `{snapshot:FieldSnapshot,field:FieldDescriptor}`；array按ref单独取 |
| AllocationResponse | AllocationResult；用户再请求具体array_ref，不在metadata启动加载全图 |
| RunList | ClosureRunRegistry或ValidationRegistry；API operation固定类型，不运行时猜 |

# 15. Shared content and definition APIs

为Home、Explore七Scene、Mechanism及科学注释闭环，定义如下轻量metadata，不增加numerical experiments。

| Entity | 字段 |
| --- | --- |
| ScientificDefinition | `id:ID,semantic_id:ID,title:string,definition:string,time_rule:string,spatial_rule:string,unit:UnitSpec,mask_refs:List<ID>,detector:Fact<DetectorSpec>,evidence_refs:List<ID>,limitations:List<ScientificLimitation>` |
| DefinitionList | `items:List<ScientificDefinition>` |
| ScenePreset | `scene_id:Integer,title:string,conclusion:string,view_kind:MECHANISM\|ENTROPY\|ALLOCATION\|SPECTRUM\|CROSS_FLOW\|EVIDENCE,targets:List<ScientificTarget>,allowed_controls:List<ControlSpec>,evidence_refs:List<ID>,limitations:List<ScientificLimitation>` |
| ScientificTarget | `experiment_id:ID,config_id:Fact<ID>,result_ids:List<ID>`；Evidence/机制scene可targets空 |
| SceneList | `items:List<ScenePreset>`；scene1…7，curated state不复制科学数据 |
| MechanismContent | `content_id:ID,data_origin:SCHEMATIC,nodes:List<MechanismNode>,edges:List<MechanismEdge>,supported_states:List<string>,evidence_refs:List<ID>,limitations:List<ScientificLimitation>` |
| MechanismNode / Edge | `{id:ID,label:string,explanation:string}` / `{from_node:ID,to_node:ID,label:string}` |

Mechanism允许STRICT_1D/WEAKLY_2D、q_at off/enabled示意，显示trigger/output分开、δ_t不入gate和有条件near1D解释；没有五epsilon数值服务。mask/definition接口通过受控ID取已定义对象，不提供客户端公式执行。

# 16. Account extension — MySQL + QQ email

Account Extension 已设计并保留 MySQL、QQ email、OTP、session、CSRF、Account Blueprint 和 AUTH 契约；交付优先级正式冻结：

```text
ACCOUNT_EXTENSION_PRIORITY=P1_NON_BLOCKING
ACCOUNT_EXTENSION_BLOCKS_P0=NO
ACCOUNT_EXTENSION_BLOCKS_CASE8_SLICE=NO
ENABLE_ACCOUNTS_DEFAULT=false
```

账号不属于 P0 scientific core 或 Case8 Functional Vertical Slice DoD，Account DB/API 不作为 Phase 5 首批必做项。MySQL、QQ SMTP 或 Account Service 不可用时，Entry、Home、Lab、Case8 Replay、Scientific API、Evidence、Explore 与核心 Replay 仍支持 Anonymous Replay。首阶段不优先实现 registration/email code/login/session；后续账号切片仍遵守本文现有安全模型。

账号是用户在Phase4明确追加的设计；关闭账号/数据库/SMTP故障仍可用公共Replay。Flask Account Blueprint/AccountService/AccountRepository/MailService遵循04，科学adapter不管理账户。DATABASE_URL模板：`mysql+pymysql://<user>:<password>@127.0.0.1:3308/<database>`；密码、发件账号、SMTP授权码由环境提供，不写文档或fixture。库名未提供，未连接验证。

## 16.1 MySQL storage entities (never API DTO)

InnoDB、utf8mb4；UUID以ascii CHAR(36)，UTC DATETIME(6)。未来migration才建表；本轮不DDL。

| Table | 字段、索引与约束 |
| --- | --- |
| users | `user_id UUID PK, email_normalized VARCHAR(254) UNIQUE NOT NULL, display_name VARCHAR(64) NOT NULL, password_hash VARCHAR(255) NOT NULL, email_verified_at DATETIME NOT NULL, status ACTIVE\|DISABLED NOT NULL, created_at DATETIME NOT NULL`；email唯一比较用规范化ascii/bin语义 |
| email_verification_challenges | `challenge_id UUID PK, email_normalized VARCHAR(254), purpose REGISTER, code_digest CHAR(64), state PENDING_SEND\|ACTIVE\|SEND_FAILED\|LOCKED\|CONSUMED\|EXPIRED\|SUPERSEDED, generation BIGINT, attempt_count INT, created_at DATETIME, expires_at DATETIME, activated_at DATETIME nullable, consumed_at DATETIME nullable`；index(email,purpose,state,created_at)，attempt≤5 |
| auth_sessions | `session_id UUID PK, user_id UUID FK users, token_digest CHAR(64) UNIQUE, created_at DATETIME, expires_at DATETIME, revoked_at DATETIME nullable`；index(user_id,expires_at)，不存raw token |
| account_rate_limits | `bucket_key CHAR(64) PK, window_start DATETIME, attempt_count INT, last_attempt_at DATETIME, next_generation BIGINT`；按purpose/email/IP的摘要key；锁行原子预留发送配额/每邮箱generation，不放密码/OTP明文 |

存储nullable日期是数据库状态设计；公共响应只用公开Account DTO，不把SQL NULL当科学UNKNOWN。disabled用户不能建立会话。password=12…128字符，不截断，Werkzeug scrypt带salt；科学数值数据不进入数据库。

## 16.2 Request and public models

| Entity | 全部字段/校验 |
| --- | --- |
| AccountFeatureInfo | `enabled:boolean,status:AVAILABLE\|UNSUPPORTED\|ERROR,registration_method:QQ_EMAIL_CODE`；健康信息不泄漏配置secret |
| CsrfTokenResponse | `csrf_token:string,expires_in_seconds:Integer`；同源表单使用，不放URL |
| VerificationCodeRequest | `email:string,purpose:REGISTER`；校验ASCII邮箱格式且域名仅qq.com，trim、域名lowercase；local part原样保留；拒绝display-address、CR/LF、quoted local part；必须验证码确认，不只凭地址格式 |
| VerificationChallengeResponse | `challenge_id:ID,email:string,purpose:REGISTER,expires_in_seconds:Integer>0,resend_after_seconds:Integer>=0,delivery_status:SMTP_ACCEPTED`；默认600/60，来自服务策略；不是保证收件箱送达 |
| RegistrationRequest | `email:string,challenge_id:ID,code:string,password:string,display_name:string`；code六位ASCII数字字符串，保留前导0；display_name1…64字符且去首尾空白 |
| AccountUser | `user_id:ID,email:string,display_name:string,email_verified:boolean,created_at:timestamp`；无password_hash/code_digest/token_digest |
| RegistrationResponse | `user:AccountUser,login_required:true`；不注册即自动登录 |
| LoginRequest | `email:string,password:string`；错误账号/密码共同INVALID_CREDENTIALS |
| SessionResponse | `user:AccountUser,expires_at:timestamp`；opaque token只在Set-Cookie，响应JSON无token |
| LogoutResponse | `logged_out:true`；已登出仍幂等成功，需同源/CSRF |

TTL600s，ACTIVE后开始计时；5次wrong code；send cooldown60s、每email每小时5、每IP每小时20；login每IP15分钟20次。用可配置服务策略和注入clock，响应中的有效期/冷却时长由策略配置导出，不把600/60固化为Literal类型。code采用CSPRNG六位，只存HMAC-SHA256(challenge,email,purpose,code) with OTP_HASH_KEY；constant-time比较；密钥环境配置不得写日志。

SMTP_SSL smtp.qq.com:465、SSL=true、MAIL_DEFAULT_SENDER=MAIL_USERNAME；发件账号配置独立于注册收件邮箱。先DB短事务PENDING_SEND/预留配额、再限时SMTP、再短事务ACTIVE，不持行锁等网络。按generation保证后到的旧发送响应不能替换较新成功请求；新challenge只在成功激活时SUPERSEDE旧ACTIVE；失败新请求保留旧有效码。重复PENDING/冷却由同邮箱锁保护，避免并发发送穿透。

注册challenge锁定→purpose/email/state/expiry/attempt核对→创建唯一email user→consume，同事务提交；错误尝试必须单独commit，到5 LOCKED；user insert失败不得consume。请求响应丢失后重试可返回ACCOUNT_ALREADY_EXISTS，不重复账号。不设计复杂幂等任务系统。

24小时随机opaque session；DB仅token摘要；cookie HttpOnly/SameSite=Lax，网络部署HTTPS+Secure；loopback本机HTTP有明确local配置例外。所有账户POST包括未登录表单同源Origin+CSRF，CSRF bootstrap和cookie绑定会话/匿名浏览器状态；login后旋转CSRF，logout清会话。COOKIE/CSRF内部秘密不可用科学Fact/evidence认证。

官方依据：[SQLAlchemy PyMySQL](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)、[Werkzeug hashing](https://werkzeug.palletsprojects.com/en/stable/utils/)、[Python SMTP_SSL](https://docs.python.org/3/library/smtplib.html)。这是后续实现要求，本轮未建库/发送邮件/注册用户。

SMTP_SSL显式使用`ssl.create_default_context()`以验证证书/主机名，并设置有限连接/读超时；SECRET_KEY用于Flask会话/CSRF签名，OTP_HASH_KEY用于code摘要，均环境读取。QQ邮箱格式限制@qq.com域，local part不擅自做点/加号消除或大小写合并；身份按已验证的规范化地址，不推测多个地址属于同一邮箱。

# 17. Validation and schema versioning

后续 Pydantic：canonical strict + extra forbid + discriminated unions + finite数值；adapter显式解析CSV字符串、NumPy类型并校验；Blueprint显式将合法路径/query字符串解析为typed请求，再strict validate。不使用全局隐式coerce。serialization mode导出响应schema，validation mode导出请求schema；自定义NumPy/complex转换的schema必须与实际JSON一致。[Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)、[JSON Schema generation](https://docs.pydantic.dev/latest/concepts/json_schema/)。

| Rule | 拒绝或必须证明的行为 |
| --- | --- |
| S01 | schema_version=1.0.0，未知额外字段、非finite、invalid Fact variant拒绝 |
| S02 | config与experiment identity匹配；Cylinder C_u拒绝；Spectrum不隶Case8 |
| S03 | Case8六真实帧；snapshot实际step/time/fields与canonical source精确一致；不能PER_STEP全场 |
| S04 | history source_step_index映射与endpoint独立；累计/增量/stage aggregate不互换；source numbering保留 |
| S05 | Case8 Allocation仅D_u；A/B/C=MISSING，不能zero-fill或从日志反推数组 |
| S06 | Gate三枚举；无free q/time map；sum原array=budget，不二次乘测度 |
| S07 | native-face x/y shape/measure/mask分开；integral按dy/dx；derived cell不是权威积分 |
| S08 | Closure五run；stage3*steps；stage/step分别semantic；CFL metadata discrepancy可追溯核定 |
| S09 | Spectrum恰68唯一组合、每block512、top32/side；q四档、ell0…16、baseline同base/ell/q0 |
| S10 | ComplexValue real/imag均finite；vector order/normalization/mask来源；不补矩阵 |
| S11 | Validation恰24×33；mode/q/epsilon合法；fit0…32 inclusive；relative fraction；不制造spatial movie |
| S12 | Cylinder3config×5snapshot/9757history；16sector+17edges；band cumulative/interior-only；无2D累积 |
| S13 | len(values)=product(shape)，axes/location/geometry匹配；dtype不得混；原值精度不下采样 |
| S14 | 每科学result evidence_refs非空且source asset已注册；hash不得用method/data/ETag互替 |
| S15 | data drift阻止值API；dependency source drift可见；verification不因缓存/显示转换升级 |
| S16 | metric有definition/scope/detector/time/unit；HF/width/localization不统一ranking |
| S17 | partial envelope有issues和可定位slots；MISSING/UNSUPPORTED slot没有value |
| S18 | MOCK显著data_origin/NOT_APPLICABLE并独立mock namespace；不得进入production cache/registry |
| S19 | 所有公开DTO无absolute_source_path、credentials、raw ORM；账号密码/验证码错误不回显input |

版本策略：`schema_version`遵循semver，`/api/v1`是HTTP major；breaking字段/semantic/enum改变升major并同步架构与OpenAPI/types；向后兼容新可选metadata升minor，文案/示例修订升patch。strict模型不接受未来新增字段，客户端和服务端必须同锁contract版本，不能只因HTTP major不变宣称任意新字段兼容。源数据revision与schema版本独立；未生成正式release/OpenAPI/TS types，仅设计。

Contract-first：审核后三份文档驱动单一Pydantic + operation catalog；导出OpenAPI3.1与TS；frontend mock fixture必须通过同serialization JSON Schema，并标MOCK；backend真实response通过同DTO。Python validator的跨字段科学约束不能仅靠JSON Schema替代，须科学回归和contract tests。本文placeholder示例不允许成为schema-valid fixture。

# 18. Canonical examples

下面例子是**完整字段结构的文档模板**。`<from canonical source>`及`<...>`是待绑定占位符，不是真实数值、真实应用ID/时间或合法生产DTO；schema测试必须先由真实已核验来源替换占位符。为避免重复，规定模板展开语法：`@R(id,semantic,origin,time,scope,unit,verification,assets)`展开第5节ScientificResult全部字段（schema_version1.0.0、registry/data_revision取当前registry、release_id=N/A、evidence_refs取对应ev、limitations按scope）；`@U(id,quantity)`展开UnitSpec全部字段，MODEL且si_mapping UNKNOWN；`@V(status)`展开Verification全部字段，basis从Phase1相关记录、verified_at/observation_at未知则Fact UNKNOWN。`@Scope(id,mask)`展开ScopeSpec全部字段，从定义注册表绑定description/boundary/domain/definitions。这些是文档缩写，**JSON API绝不能发送@字符串**。每例下面列出所有专属字段；共用header按本节展开，实体无省略字段。API实例沿用同一展开规则，避免制造另一套schema。

## EX01 — Case8 experiment with D_u configuration

```json
{
  "schema_version": "1.0.0",
  "id": "case8",
  "name": "Case8 Mach6",
  "scientific_family": "CARTESIAN_SHOCK_REPLAY",
  "description": "Four recorded configurations; six snapshots and 1912 scalar records per configuration",
  "capabilities": "<complete ExperimentCapability objects from section 4.2: Flow/Entropy/Allocation/Metrics/Evidence>",
  "available_configs": "<complete ExperimentConfig list A_u/B_u/C_u/D_u; D_u parameters q_aa=3.96, q_at=0.396, CFL=.05, gate=Acoustic; protocol128x32, SSP-RK3, T=.08>",
  "status": "PARTIAL",
  "delivery_status": "PLANNED",
  "limitations": [{"id":"lim.case8.dense-fields","code":"DISCRETE_RECORDED_ONLY","description":"No per-step full state or all-stage spatial fields","affected_refs":["case8"],"severity":"WARNING"}],
  "evidence_refs": ["ev.case8.protocol"],
  "related_experiment_ids": ["gate","spectrum","cylinder"]
}
```

EX01的capability必须展开为含config_support的完整列表；以下给出Allocation和D_u配置的完整专属结构，其他能力按同结构由registry读取；available_configs仍须列A/B/C/D。不能仅写allocation=true。

```json
{
  "id":"case8.allocation",
  "experiment_id":"case8",
  "task":"trajectory-integrated native-face allocation",
  "status":"PARTIAL",
  "available_for_configs":["D_u"],
  "config_support":[
    {"config_id":"A_u","status":"MISSING","reason":"No saved cumulative native-face map; scalar zero-channel does not create a spatial asset","result_refs":[]},
    {"config_id":"B_u","status":"MISSING","reason":"No saved cumulative native-face map","result_refs":[]},
    {"config_id":"C_u","status":"MISSING","reason":"No saved cumulative native-face map","result_refs":[]},
    {"config_id":"D_u","status":"SUPPORTED","reason":"Existing frozen diagnostic rerun","result_refs":["case8.D_u.allocation"]}
  ],
  "controls":[{"name":"config","kind":"ENUM","allowed_values":["A_u","B_u","C_u","D_u"],"combination_registry_ref":{"state":"KNOWN","value":"case8.configs"}}],
  "tab_policy":{"tab_id":"allocation","visible_for_family":true,"disabled_for_configs":["A_u","B_u","C_u"],"unsupported_deep_link_behavior":"EXPLAIN"},
  "result_refs":["case8.D_u.allocation"],
  "limitations":[{"id":"lim.case8.allocation-configs","code":"D_U_ONLY_DIAGNOSTIC_RERUN","description":"Only D_u has saved cumulative native-face maps","affected_refs":["case8.allocation"],"severity":"WARNING"}],
  "evidence_refs":["ev.case8.D_u.allocation"]
}
```

```json
{
  "id":"D_u",
  "experiment_id":"case8",
  "name":"Case8 D_u",
  "parameters":[
    {"name":"q_aa","value":{"state":"KNOWN","value":3.96},"unit":{"id":"dimensionless","system":"DIMENSIONLESS","quantity":"coefficient","label":"dimensionless","si_mapping":{"state":"NOT_APPLICABLE","reason":"Dimensionless coefficient"}}},
    {"name":"q_at","value":{"state":"KNOWN","value":0.396},"unit":{"id":"dimensionless","system":"DIMENSIONLESS","quantity":"coefficient","label":"dimensionless","si_mapping":{"state":"NOT_APPLICABLE","reason":"Dimensionless coefficient"}}},
    {"name":"CFL","value":{"state":"KNOWN","value":0.05},"unit":{"id":"dimensionless","system":"DIMENSIONLESS","quantity":"CFL","label":"dimensionless","si_mapping":{"state":"NOT_APPLICABLE","reason":"Dimensionless ratio"}}},
    {"name":"gate","value":{"state":"KNOWN","value":"Acoustic"},"unit":{"id":"categorical","system":"UNKNOWN","quantity":"gate category","label":"category","si_mapping":{"state":"NOT_APPLICABLE","reason":"Categorical parameter"}}}
  ],
  "protocol":{
    "method_name":{"state":"KNOWN","value":"cross_mode_ec_unified_v1"},
    "method_hash":{"state":"KNOWN","value":"98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"},
    "grid":{"state":"KNOWN","value":{"coordinate_system":"CARTESIAN","dimensions":[{"axis":"y","size":32},{"axis":"x","size":128}],"extent":[{"axis":"x","lower":0,"upper":1},{"axis":"y","lower":0,"upper":1}]}},
    "integrator":{"state":"KNOWN","value":"SSP-RK3"},
    "reconstruction":{"state":"KNOWN","value":"first-order / none"},
    "final_time":{"state":"KNOWN","value":0.08},
    "boundary_scope":{"state":"KNOWN","value":"<exact native-face enumerator/boundary scope from protocol>"},
    "protocol_asset_refs":["asset_8d15c3f16f95"]
  },
  "verification":{"status":"FROZEN_VERIFIED","basis":["Phase1 protocol asset recorded hash match; does not certify every checkpoint"],"verified_at":{"state":"UNKNOWN","reason":"No bound per-configuration verification event"},"observation_at":{"state":"UNKNOWN","reason":"Runtime observation not performed"},"evidence_refs":["ev.case8.protocol"]},
  "limitations":[],
  "evidence_refs":["ev.case8.protocol"]
}
```

## EX02 — Case8 D_u snapshot 6, density

```json
{
  "result":"@R(case8.D_u.snapshot.6,snapshot_metadata,VERIFIED_PRODUCTION,MULTI_SNAPSHOT/NONE@.08,case8.grid,model_state,VERIFIED_NOT_FROZEN,[asset_f4323c28384b])",
  "snapshot_id":"case8.D_u.snapshot.6",
  "snapshot_index":6,
  "step_index":1912,
  "physical_time":0.08,
  "grid":{"coordinate_system":"CARTESIAN","dimensions":[{"axis":"y","size":32},{"axis":"x","size":128}],"extent":[{"axis":"x","lower":0,"upper":1},{"axis":"y","lower":0,"upper":1}]},
  "fields":[{
    "field_id":"density",
    "label":"Density (model units)",
    "result":"@R(case8.D_u.snapshot.6.density,density,VERIFIED_PRODUCTION,MULTI_SNAPSHOT/NONE@.08,case8.cells,model_density,VERIFIED_NOT_FROZEN,[asset_f4323c28384b])",
    "domain":{"id":"case8.cells","coordinate_system":"CARTESIAN","location_type":"CARTESIAN_CELL","shape":[32,128],"axes":"<AxisDescriptor y32/x128 with source coordinates>","extent":[{"axis":"x","lower":0,"upper":1},{"axis":"y","lower":0,"upper":1}],"measure_convention":"<MeasureConvention from cell display definition; not entropy integral>","boundary_scope":{"state":"KNOWN","value":"<from canonical protocol>"},"geometry_ref":{"state":"NOT_APPLICABLE","reason":"Cartesian coordinate axes"},"evidence_refs":["ev.case8.protocol"]},
    "array_ref":{"result_id":"case8.D_u.snapshot.6.density","descriptor":{"array_id":"density","dtype":"float64","shape":[32,128],"order":"C","axes":["y","x"],"encoding":"FLAT_JSON","element_count":4096}},
    "mask_refs":[]
  }]
}
```

本例是只选density的FieldSnapshot投影；完整SnapshotIndex还列pressure/front与实际已存字段，每field正确asset/verification。1912/.08来自Phase1实际末帧，并非编造；中间帧time一律读原NPZ。

为明确所有科学响应共同header，EX02 density.result完整展开如下；这里UNKNOWN不被文档写作日期填补，unit不擅自换SI。

```json
{
  "schema_version":"1.0.0",
  "result_id":"case8.D_u.snapshot.6.density",
  "experiment_id":"case8",
  "config_id":"D_u",
  "semantic_id":"density",
  "data_origin":"VERIFIED_PRODUCTION",
  "availability":"AVAILABLE",
  "time":{"sampling":"MULTI_SNAPSHOT","accumulation":"NONE","physical_time":{"state":"KNOWN","value":0.08},"interval":{"state":"NOT_APPLICABLE","reason":"Instantaneous state"},"step_index":{"state":"KNOWN","value":1912},"stage_index":{"state":"NOT_APPLICABLE","reason":"Accepted-step endpoint snapshot"},"snapshot_index":{"state":"KNOWN","value":6},"index_convention":"snapshot_index1-based; step_index=completed accepted steps"},
  "scope":{"id":"case8.cells","description":"Corrected Case8 D_u cell density at recorded endpoint","boundary_scope":{"state":"UNKNOWN","reason":"Bind exact saved field scope during adapter implementation"},"spatial_domain_ref":{"state":"KNOWN","value":"case8.cells"},"mask_refs":[],"definition_refs":["density"]},
  "unit":{"id":"model_density","system":"MODEL","quantity":"density","label":"model density","si_mapping":{"state":"UNKNOWN","reason":"No established SI mapping"}},
  "verification":{"status":"VERIFIED_NOT_FROZEN","basis":["Phase1 finite fields, actual checkpoint schedule and bitwise terminal comparison; no upstream per-checkpoint freeze"],"verified_at":{"state":"UNKNOWN","reason":"No per-result event timestamp bound"},"observation_at":{"state":"UNKNOWN","reason":"Runtime current hash observation not performed"},"evidence_refs":["ev.case8.D_u.snapshot.6.density"]},
  "provenance":{"evidence_refs":["ev.case8.D_u.snapshot.6.density"],"source_asset_ids":["asset_f4323c28384b"],"registry_revision":"<actual canonical selection revision>","data_revision":"<actual data fingerprint>","release_id":{"state":"NOT_APPLICABLE","reason":"No release bundle created"},"source_drift":{"state":"UNKNOWN","reason":"Observe all source dependencies before asserting false"}},
  "limitations":[{"id":"lim.density.model-units","code":"SI_MAPPING_UNKNOWN","description":"Model density has no confirmed SI mapping","affected_refs":["case8.D_u.snapshot.6.density"],"severity":"INFO"}]
}
```

## EX03 — Case8 D_u E_at scalar series, first real endpoint

```json
{
  "result":"@R(case8.D_u.E_at_cumulative,E_at_cumulative,FROZEN_PRODUCTION,PER_STEP/TRAJECTORY_INTEGRATED[0,.08],case8.native-face-budget,model_integrated_entropy,FROZEN_VERIFIED,[asset_0a3f2155fa2b])",
  "series_id":"case8.D_u.E_at_cumulative",
  "label":"E_at cumulative",
  "total_point_count":1912,
  "points":[{"point_index":0,"step_index":{"state":"KNOWN","value":1},"stage_index":{"state":"NOT_APPLICABLE","reason":"Accepted-step endpoint"},"source_step_index":{"state":"KNOWN","value":0},"source_stage_index":{"state":"NOT_APPLICABLE","reason":"No single stage"},"physical_time":{"state":"KNOWN","value":0.00004184100418410042},"interval":{"state":"KNOWN","value":{"start":0,"end":0.00004184100418410042}},"value":{"state":"KNOWN","value":0.00001696563880973865}}],
  "page":{"offset":0,"limit":1,"returned_count":1,"total_count":1912,"has_more":true},
  "aggregation":"CUMULATIVE",
  "source_column":"E_at",
  "definition_id":"E_at_cumulative"
}
```

point time/value来自Phase1该asset inspection.first_row，作为来源映射示例；不重新认证数值或硬编码到产品。

## EX04 — Gate Acoustic cell allocation

```json
{
  "result":"@R(gate.Acoustic.allocation,Gate_cell_Pi_at_integrated,FROZEN_PRODUCTION,STATIC/TRAJECTORY_INTEGRATED[0,.08],gate.cell-window,model_integrated_entropy,FROZEN_VERIFIED,[asset_a11ef6fc4e6e,asset_aef55f8d1d5a,asset_513157e8d9c4])",
  "representation_type":"CELL_FIELD",
  "fields":[{"field_id":"allocation_at","label":"Trajectory-integrated cell allocation","result":"<same result header>","domain":"<SpatialDomain CARTESIAN_CELL [32,128], y/x coordinates, Gate measure sum(array)=E_at>","array_ref":{"result_id":"gate.Acoustic.allocation","descriptor":{"array_id":"allocation_at","dtype":"float64","shape":[32,128],"order":"C","axes":["y","x"],"encoding":"FLAT_JSON","element_count":4096}},"mask_refs":["mask.gate.cell-window"]}],
  "summary":{"total_budget":"<AVAILABLE Metric E_at from Gate terminal summary>","inside":"<AVAILABLE Metric gate_shock_window_fraction from frozen analysis>","outside":"<AVAILABLE Metric gate_outside_window_fraction>","fraction_format":"FRACTION","mask_refs":["mask.gate.cell-window"],"measure":{"id":"gate.integrated-cell-sum","description":"Array includes time/RK and native face measure","integral_rule":"sum(values)=E_at","measure_parameters":[],"includes_time_weights":true,"includes_spatial_measure":true},"spatial_cumulative_curve":"<ResourceSlot SpatialCurve; MISSING until explicitly verified derivation if not stored>","evidence_refs":["ev.gate.Acoustic.allocation"]}
}
```

Acoustic matched q=.4由配置资产加载，与Case8 D_u=.396分开；Pressure=.31018332312583474、Ungated=.03483470441226932也不是任意slider值。summary数值占位，不抄百分数。

## EX05 — Spectrum q_at=.396 ell=8

```json
{
  "result":"@R(spectrum.q-0.396.ell-8,spectral_abscissa,FROZEN_PRODUCTION,STATIC/NONE,spectrum.common-base,model_inverse_time,FROZEN_VERIFIED,[asset_e45cd83f9cbc])",
  "record_id":"spectrum.q-0.396.ell-8",
  "q_at":0.396,
  "ell":8,
  "spectral_abscissa":{"state":"KNOWN","value":"<from canonical source>"},
  "leading_eigenvalue":{"state":"KNOWN","value":{"real":"<from canonical source>","imag":"<from canonical source>"}},
  "leading_eigenvalue_ref":{"spectrum_record_id":"spectrum.q-0.396.ell-8","rank":0},
  "eigenvalues_ref":{"result_id":"spectrum.q-0.396.ell-8.eigenvalues","descriptor":{"array_id":"eigenvalues","dtype":"complex128","shape":[512],"order":"C","axes":["rank"],"encoding":"FLAT_JSON","element_count":512}},
  "delta_alpha":{"state":"KNOWN","value":"<from canonical source>"},
  "baseline":{"dataset_id":"spectrum.common-mach6.v1","base_result_id":"spectrum.common-base","q_at":0,"ell":8,"record_id":"spectrum.q-0.000.ell-8","definition":"ALPHA_MINUS_SAME_ELL_Q0"},
  "eigenmode_refs":["spectrum.q-0.396.ell-8.right.rank-0","spectrum.q-0.396.ell-8.left.rank-0"]
}
```

eigenmode_refs在实际DTO列该block所有已注册vectors，示例是选leading两个的metadata投影；完整谱dataset仍68records，rank0…31原排序必须source核定。

## EX06 — Fig13 mode8 q=.396 epsilon=1e-5

```json
{
  "result":"@R(fig13.m08.q-0.396.eps-1e-5,modal_validation,FROZEN_PRODUCTION,PER_STEP/NONE,spectrum.common-base,model_inverse_time,FROZEN_VERIFIED,[<actual run history asset_id>,asset_eef93c1945fd])",
  "run_id":"fig13.m08.q-0.396.eps-1e-5",
  "mode":8,
  "q_at":0.396,
  "epsilon":0.00001,
  "spectrum_record_id":"spectrum.q-0.396.ell-8",
  "eigenmode_id":"<selected eigenpair from frozen summary; do not guess rank/branch>",
  "point_count":33,
  "history_result_id":"fig13.m08.q-0.396.eps-1e-5.history",
  "summary":{"sigma_LIN":{"state":"KNOWN","value":"<from canonical source>"},"sigma_RK3":{"state":"KNOWN","value":"<from canonical source>"},"sigma_CFD":{"state":"KNOWN","value":"<from canonical source>"},"absolute_discrepancy":{"state":"KNOWN","value":"<from canonical source>"},"relative_discrepancy":{"state":"KNOWN","value":"<from canonical source>"},"relative_discrepancy_format":"FRACTION","relative_discrepancy_definition_id":"fig13.relative-discrepancy-CFD-RK3","R2":{"state":"KNOWN","value":"<from canonical source>"},"fit_start":0,"fit_end":32,"fit_point_count":33,"growth_rate_unit":"@U(model_inverse_time,inverse model time)","evidence_refs":["ev.fig13.m08.q-0.396.eps-1e-5"]},
  "limitations":[{"id":"lim.fig13.amplitude-only","code":"NO_SPATIAL_MOVIE","description":"Only projected amplitude history is saved","affected_refs":["fig13.m08.q-0.396.eps-1e-5"],"severity":"WARNING"}]
}
```

## EX07 — Cylinder D_u sector allocation

```json
{
  "result":"@R(cylinder.D_u.sectors,Cylinder_sector_E_at_integrated,FROZEN_PRODUCTION,STATIC/TRAJECTORY_INTEGRATED[0,2],cylinder.interior-sectors,model_integrated_entropy,FROZEN_VERIFIED,[asset_77343b219f8b])",
  "representation_type":"ANGULAR_SECTORS",
  "sector_count":16,
  "bin_edges":{"result_id":"cylinder.D_u.sectors.geometry","descriptor":{"array_id":"bin_edges","dtype":"float64","shape":[17],"order":"C","axes":["theta_edge"],"encoding":"FLAT_JSON","element_count":17}},
  "channel_arrays":"<four ChannelArray objects bg/aa/at/total, float64 shape[16], axes[theta_sector], actual array IDs>",
  "sector_fractions":"<16 Fact<Number> entries from channel_at/E_at_int; zero denominator N/A>",
  "front_band_summary_ref":"cylinder.D_u.front-band",
  "summary":{"total_budget":"<AVAILABLE Metric E_at_int>","inside":"<AVAILABLE Metric cylinder_front_band_fraction>","outside":"<AVAILABLE Metric outside-band fraction with same denominator>","fraction_format":"FRACTION","mask_refs":["mask.cylinder.fixed-front-band"],"measure":{"id":"cylinder.interior-sector-sum","description":"Cumulative RK/time/native interior face-weighted bins","integral_rule":"sum(channel_at)=E_at_int","measure_parameters":[],"includes_time_weights":true,"includes_spatial_measure":true},"spatial_cumulative_curve":{"availability":"UNSUPPORTED","error":{"domain":"SCIENTIFIC","code":"UNSUPPORTED_COMBINATION","message":"Gate Cartesian cumulative curve does not apply to cylinder sectors","target":{"resource_type":"spatial_curve","identity":{"state":"KNOWN","value":"cylinder.D_u.sectors"}},"retryable":false,"details":[],"evidence_refs":["ev.cylinder.D_u.sectors"]}},"evidence_refs":["ev.cylinder.D_u.sectors"]}
}
```

bins的角单位是dimensionless angle/radian；channel的model entropy不同，bin_edges使用专属result_id cylinder.D_u.sectors.geometry及正确角单位header，见06 ARRAY01。

## EX08 — Evidence for Case8 D_u density snapshot 6

```json
{
  "schema_version":"1.0.0",
  "evidence_id":"ev.case8.D_u.snapshot.6.density",
  "result_ids":["case8.D_u.snapshot.6.density"],
  "result_contexts":["<EX02 density.result full header, with current runtime observations>"],
  "experiment_id":{"state":"KNOWN","value":"case8"},
  "config_id":{"state":"KNOWN","value":"D_u"},
  "config":{"state":"KNOWN","value":"<EX01 D_u ExperimentConfig full object>"},
  "definitions":[{"id":"density","semantic_id":"density","title":"Cell density","definition":"Saved primitive density member on the recorded Cartesian grid","time_rule":"Recorded accepted-step endpoint; six snapshots only","spatial_rule":"Cell-centered [y,x],32x128","unit":"@U(model_density,density)","mask_refs":[],"detector":{"state":"NOT_APPLICABLE","reason":"Stored state variable, not detector metric"},"evidence_refs":["ev.case8.protocol"],"limitations":[]}],
  "masks":[],
  "method_name":{"state":"KNOWN","value":"cross_mode_ec_unified_v1"},
  "method_hash":{"state":"KNOWN","value":"98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0"},
  "recorded_source_hash":"<HashFact from method freeze; not copy current hash to unknown dependencies>",
  "current_source_hash":"<HashFact from runtime read-only observation>",
  "source_observations":"<all source dependencies with recorded/current hashes and individual drift>",
  "source_assets":[{"asset_id":"asset_f4323c28384b","source_id":"scientific-root-v1","source_display":"Case8 D_u corrected checkpoint step_001912.npz","relative_origin":{"state":"KNOWN","value":"corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_001912.npz"},"role":"DATA","format":"NPZ","recorded_data_hash":{"state":"KNOWN","value":"3ab44eb9febe7fbe5d8f76e00ef0b31afd4b01bceb2676ed609f4f9860d62093"},"current_data_hash":"<runtime HashFact>","data_drift":"<runtime Fact<boolean>>","verification":"@V(VERIFIED_NOT_FROZEN)","canonical_selected":true,"limitations":[{"id":"lim.checkpoint.freeze","code":"NO_UPSTREAM_CHECKPOINT_HASH","description":"Phase1 verified finite fields, schedule and bitwise terminal equality; no upstream per-checkpoint freeze record","affected_refs":["asset_f4323c28384b"],"severity":"INFO"}]}],
  "data_hash":{"state":"KNOWN","value":"3ab44eb9febe7fbe5d8f76e00ef0b31afd4b01bceb2676ed609f4f9860d62093"},
  "freeze_reference":{"state":"NOT_APPLICABLE","reason":"No upstream per-checkpoint freeze record"},
  "processing":[{"id":"processing.case8.density-json","kind":"FORMAT_MAPPING","description":"Read density member; preserve float64 values/shape/time; serialize C-order","input_asset_ids":["asset_f4323c28384b"],"definition_refs":["density"],"processing_hash":{"state":"UNKNOWN","reason":"Adapter not implemented in Phase4"},"verification":"@V(NOT_APPLICABLE)"}],
  "verification":"@V(VERIFIED_NOT_FROZEN)",
  "limitations":[],
  "source_drift":{"state":"UNKNOWN","reason":"Runtime dependency observation has not occurred"},
  "created_at":{"state":"UNKNOWN","reason":"No authoritative per-result timestamp"},
  "verified_at":{"state":"UNKNOWN","reason":"No authoritative per-result timestamp is bound; do not infer from inventory audit date"},
  "related_evidence_refs":["ev.case8.protocol"],
  "superseded_by":{"state":"NOT_APPLICABLE","reason":"No known replacement"}
}
```

EX08不借全局inventory日期虚构逐结果核验事件；有真实specific audit observation才绑定verification.observation_at。该例不保证当前源码无漂移。

# 19. Document acceptance boundary

全部模型均有04 owner与06获取/组合路径，映射见06末尾CROSS_DOCUMENT_CONSISTENCY_MATRIX。Full V1 canonical schema 设计已正式冻结；schema模型未实现，placeholder仅文档。本轮仅冻结，等待人工确认，不进入Case8实现、不创建数据库、不连接SMTP、不改变科研源或上游。

```text
SCHEMA_DESIGN_SCOPE=FULL_V1
SCHEMA_IMPLEMENTATION_STRATEGY=BY_VERTICAL_SLICE
```

文档版本1.0.1是本次澄清补丁；既有 application/API payload 的 schema_version=1.0.0 与 /api/v1 保持不变，不批量改写示例或重新设计模型。

## CASE8_SLICE_SCHEMA_SUBSET

Phase 5 首个 Case8 切片只实现以下模型及其实际使用的依赖；全 V1 设计已冻结，不要求 Day 1 一次性实现全部模型。

| Group | First-slice models |
| --- | --- |
| Core | Fact, HashFact, UnitSpec, ScientificLimitation, Verification, ProvenanceRef, ScientificResult, Availability, CapabilityStatus, ResourceSlot, ErrorBody |
| Experiment | ProjectInfo, ExperimentRef, Experiment, ExperimentConfig, ExperimentCapability, ConfigCapability, ControlSpec, ProtocolSpec, GridSpec |
| Case8 snapshots / arrays | FieldSnapshot, FieldDescriptor, SnapshotIndex, ArrayDescriptor, ArrayRef, ScientificArray |
| Case8 histories / alignment / metrics | ScalarPoint, ScalarSeries, EntropyHistory, SnapshotAlignment, Metric, MetricCollection, DetectorSpec |
| Evidence | EvidenceRecord, EvidenceIndexItem, ResultProvenance, SourceAsset, SourceObservation, FreezeReference, ProcessingRecord |
| Transport / used scientific context | ApiEnvelope, ScopeSpec, TimeSpec, SpatialDomain, ScientificDefinition |

辅助 DTO、分页/坐标结构、错误目标和静态功能开关等仅按首切片实际依赖实现；ProjectInfo 中账号开关固定关闭不要求账号 DB/API 实现。Gate、Entropy Closure、SpectrumDataset/SpectrumRecord/Eigenmode/complex spectrum、ModalValidationRun/History、Cylinder、CrossFlowComparison/GateComparison、Account DB/API、完整 Explore Scene models 均保留设计，随对应切片实现，不作为 Case8 首切片 DoD。DEFER IMPLEMENTATION 不等于删除设计、降级科学能力或修改 P0。

# ShockPath V1 — API Contract

版本：`1.0.1` · Phase 4 · 2026-10-01（Asia/Shanghai）。状态：**FROZEN**。人工审核：`PHASE4_REVIEW=PASS_WITH_MINOR_FIXES`。与 [04_SYSTEM_ARCHITECTURE.md](04_SYSTEM_ARCHITECTURE.md)、[05_DATA_SCHEMA.md](05_DATA_SCHEMA.md) 联合冻结；以下仍是下一阶段实施契约，未创建服务器、OpenAPI文件、mock fixture、数据库或邮件连接。

# 1. Contract principles and namespace

BACKEND_STACK=`Flask + Python`，采用Blueprint → Service → Scientific Adapter → controlled registry → READ_ONLY scientific source。Flask能够完整承载V1。OpenAPI便利性不构成切回FastAPI的理由。

前缀固定 `/api/v1`；public Replay以GET为主，无solver POST。账号是用户追加的独立POST扩展，无科学写权限。Live Solver=P1，仅预留独立workspace边界，本轮无计算任务API。API从九模板和05 typed实体推导；Explore/Lab共享同一结果请求。public Replay匿名可用，账户服务故障不能阻止其启动/读取。

canonical source只由registry选择；任何请求不能提供path、formula、NPZ member、arbitrary file下载或solver参数自由生成。浏览器不访问`D:\Paper\passage6`，后端只读。全2337资产索引不作为浏览器启动payload。

## 1.1 Common protocol

| 事项 | 冻结决定 |
| --- | --- |
| Response format | `application/json; charset=utf-8`，05 ApiEnvelope<T>；docs exception见2.2 |
| Success | 200 AVAILABLE/PARTIAL；账号register=201；partial不使用206；GET不存在科学空结果假成功 |
| Request IDs | server生成request_id，JSON与X-Request-ID相同；不信任未经校验客户端header |
| Identity | URL ID必须registry exact match；path segment按URL编码；实验/config大小写敏感 |
| Parameters | scalar finite numbers或枚举；query未知键/重复单值键400；多series采用重复series参数；不隐式丢非法参数 |
| Version pin | 科学/registry/content GET可带`registry_revision=<ID>`；省略=当前；不存在revision409 REVISION_UNAVAILABLE，提供已知选项，不静默换release |
| Public paths | 只提供ID/source_display/受控relative_origin说明；无absolute path/file://或根挂static |
| Cache | scientific GET可ETag+If-None-Match；304无body，是唯一GET envelope例外之一；ETag绑定revision/source hashes/verification/selectors/encoding，无认证意义 |
| Compression | 科学JSON支持gzip，Vary:Accept-Encoding；所有值全精度，无隐藏采样 |
| Accounts | no-store；cookie同源，不在query/JSON传session token；POST Origin+CSRF；账户错误统一ErrorBody |
| Delivery | registry delivery_status独立于真实capability；首切片只Case8 implemented，其余planned；planned operation返回503 FEATURE_NOT_ENABLED，不能伪称科学missing |

数值query如q_at接受合法十进制/科学记数finite写法，并规范化到明确枚举；0、0.0对应同一个q0 identity。0.3960000000000001不容差映射为.396。epsilon1e-5与.00001同值；未知数字0.2不是近邻插值。schema生成时request number与Wire query string parsing步骤明确分开，见17节。

# 2. Flask ownership and maintainable OpenAPI

## 2.1 Blueprint and operation catalog

| Blueprint | Service owner | 接口组 |
| --- | --- | --- |
| system_registry | RegistryService / ContentService | SYS / REG / CONTENT / DEF / MASK / DOC |
| case8 | Case8Service → Case8Adapter | C8 |
| gate | GateService → GateAdapter | GATE |
| closure | ClosureService → EntropyClosureAdapter | CLO |
| spectrum | SpectrumService → SpectrumAdapter | SPEC |
| validation | ValidationService → ModalValidationAdapter | VAL |
| cylinder | CylinderService → CylinderAdapter | CYL |
| comparison | ComparisonService | CMP；组合既有服务，没有新solver |
| evidence | EvidenceService → EvidenceAdapter | EVI |
| scientific_arrays | ResultArrayService → owning adapter | ARRAY；不允许自由文件读取 |
| accounts | AccountService / AccountRepository / MailService | AUTH；不经过Scientific Adapter |

后续单一operation catalog每项记录`operation_id,method,path,blueprint,service,request_model,response_model,documented_errors,auth_policy,cache_policy,delivery_phase,description,examples`。本文operation_id就是catalog稳定键；下面表中模型全部在05定义。Blueprint装配由同catalog绑定，必须校验路由method/path和catalog无漏项。catalog不是第二套手写schema。

## 2.2 Data validation, docs and testability guarantees

adapter出口校验05 canonical，service校验支持组合，Blueprint入口校验Pydantic request，返回前验证typed DTO/ApiEnvelope。未知字段/NaN/shape错不会JSON化成成功。输入ValidationError=400；source→model错误=500 CANONICAL_SCHEMA_MISMATCH，不能误报用户请求400。API 404/405由app级handler统一，Blueprint不能捕获路由匹配前所有404。

Pydantic JSON Schema（请求validation mode、响应serialization mode）+ catalog组合OpenAPI **3.1.0**。同名组件冲突拒绝导出；$defs/$ref转换为components/schemas并保持union/Fact discriminator；schema自定义serializer需同时匹配真实JSON。后续从该OpenAPI生成openapi-typescript与openapi-fetch类型，禁止frontend另抄一套科研字段。

DOC01 `GET /api/v1/openapi.json`返回原生OpenAPI对象，**不套ApiEnvelope**，否则Swagger无法消费；DOC02 `GET /api/docs`返回本地Swagger UI HTML，JS/CSS本地，拔网线可读。均为文档资源。Flask不会自动完成该管线，必须后续实现schema export/catalog检查。外部依据：[Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)、[OpenAPI3.1](https://spec.openapis.org/oas/v3.1.0.html)、[Flask errors](https://flask.palletsprojects.com/en/stable/errorhandling/)。

Application factory注入registry/source root/adapter/cache；科学service不依赖request/current_app；AccountRepository/MailService/clock可替换。契约测试用Flask test client并校验响应serialization schema、catalog与OpenAPI，transaction test用隔离MySQL；不靠SMTP或CFD完成unit tests。[Flask factory](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)、[testing](https://flask.palletsprojects.com/en/stable/testing/)。

# 3. Envelope and scientific availability

05 ApiEnvelope所有请求均包括：`schema_version,request_id,registry_revision:Fact<ID>,data_revision:Fact<ID>,availability,data或error,issues`。KNOWN revision来源当前显式registry；account/docs/routing未加载revision用NOT_APPLICABLE或UNKNOWN。

AVAILABLE+data、issues空；PARTIAL+data、issues非空；失败MISSING/UNSUPPORTED/ERROR+error且无data。具体array/metric/history都带自身ScientificResult，不用outer availability当科学认证。每个科学图有result_id、semantic、unit/scope/time、verification、asset/evidence refs。

组合请求的局部ResourceSlot无value时不填null/0。UNKNOWN/MISSING/N/A Fact用于字段事实；不得只靠HTTP状态区分所有事实。

## 3.1 Partial example policy

Cylinder allocation overview200 PARTIAL：sector AVAILABLE，front_band AVAILABLE，cumulative_2d MISSING、MISSING_SCIENTIFIC_ASSET；issues列累计2D缺口。不能整个experiment500，也不能201/206。Cross-flow选择Case8 A_u时该侧map MISSING，budget/metrics照常显示。请求“只要缺失的特定map”则404 known missing（见5），二者不同。

普通 metadata list可AVAILABLE，即使其Experiment.status=PARTIAL；外层表示请求资源可成功列举，不保证每个科学任务存在。返回对象中status在05有明确定义。

# 4. Query and request schemas

以下命名请求模型只包含表中允许query/body及对应path。path参数若无特别规定为受控ID；所有不适用query如Gate time、Cylinder cumulative-map参数均400 INVALID_REQUEST，不悄悄忽略。

| Request model | Fields and bounds |
| --- | --- |
| RegistryQuery | `registry_revision?:ID` |
| SnapshotQuery | RegistryQuery + `field?:ID`；field必须当前snapshot fields实际存在 |
| HistoryQuery | RegistryQuery + `series?:List<ID>,offset:Integer=0,limit:Integer=2000`；1≤limit≤5000，offset≥0；服务端只slice真实点 |
| MetricQuery | RegistryQuery + `metric_id?:ID,snapshot_index?:Integer`；snapshot仅已有checkpoint定义metrics支持，不把terminal metric按任意游标改值 |
| AlignmentQuery | RegistryQuery + `scalar_step:Integer,policy:NEAREST_RECORDED\|PINNED=NEAREST_RECORDED,snapshot_index?:Integer`；PINNED需snapshot_index；NEAREST禁止snapshot_index |
| SpectrumQuery | RegistryQuery + `q_at?:Number`；曲线接口q_at必填；四档enum |
| EigenmodeQuery | RegistryQuery + `q_at:Number,side:LEFT\|RIGHT=RIGHT,rank:Integer=0,representation:COMPLEX_VECTOR\|PRIMITIVE_PROFILE=COMPLEX_VECTOR,component?:string`；rank0…31，representation/component实际支持才可用 |
| ComparisonQuery | RegistryQuery + `case8_config:ID=D_u,cylinder_config:ID=D_u`；无sort/winner/normalize参数 |
| EvidenceQuery | RegistryQuery + `experiment_id?:ID,status?:VerificationStatus,section:CURRENT\|GAPS\|HISTORY\|ALL=CURRENT,offset:Integer=0,limit:Integer=50`；1≤limit≤200 |
| DefinitionQuery | RegistryQuery + `semantic_id?:ID` |
| ArrayQuery | RegistryQuery；format固定FLAT_JSON，不接用户dtype/member/path/downsample |
| VerificationCodeRequest / RegistrationRequest / LoginRequest | 使用05第16节JSON字段；Content-Type application/json；同源Origin与X-CSRF-Token必需 |
| EmptyAccountRequest | 无JSON业务字段；logout body={}或无body；仍需Origin/CSRF |

所有HistoryQuery返回每选series完整meta+当前page，total_count保持真实总数。offset≥total_count合法返回points=[]、returned_count0、has_morefalse，区别“已知不存在history”（后者不返回空成功）。point_count不能改成page length。Closure stage多于5000时分页完整读完；不以分页当科学downsampling。Case8默认1912全返回；Cylinder默认2000，图必须读完全部9757或显著标“已加载2000/9757”，不能把部分点当完整曲线。

# 5. Centralized error contract

| HTTP | Error code / Availability | Trigger and behavior |
| --- | --- | --- |
| 400 | INVALID_REQUEST / ERROR | malformed query/JSON、未知query键、非finite、错误字段类型、shape参数不接受等；细节不回显raw secrets |
| 400 | INVALID_EMAIL / ERROR | QQ邮箱形式或SMTP header换行不合法 |
| 401 | UNAUTHENTICATED / ERROR | /auth/me没有有效session；Replay不要求session |
| 401 | INVALID_CREDENTIALS / ERROR | 登录账号/密码不匹配或账号disabled，共同文案 |
| 403 | CSRF_FAILED / ERROR | Origin不合法、缺/错CSRF，含未登录POST |
| 404 | UNKNOWN_EXPERIMENT / MISSING | experiment_id未知 |
| 404 | API_ROUTE_NOT_FOUND / MISSING | /api下未知route，domain SYSTEM；app-level JSON handler，不回HTML |
| 404 | UNKNOWN_CONFIG / MISSING | 未注册config且不属于已知科学不支持组合 |
| 404 | INVALID_RESULT_ID / MISSING | result identity未知；不是known missing asset |
| 404 | UNKNOWN_EVIDENCE_ID / UNKNOWN_ASSET_ID / UNKNOWN_DEFINITION_ID / MISSING | 各registry identity不在索引 |
| 404 | SNAPSHOT_NOT_FOUND / MISSING | 请求有效整数但不是已存snapshot，例如Case8第7帧；details列1…6 |
| 404 | MISSING_SCIENTIFIC_ASSET / MISSING | 已知预期资产不存在/丢失，例如Case8 A/B/C cumulative maps或Cylinder cumulative2D；附缺口evidence |
| 405 | METHOD_NOT_ALLOWED / ERROR | 已知API path method错误；保留Allow header；不落SPA HTML |
| 409 | SOURCE_DATA_DRIFT / ERROR | 原数据字节hash与registry记录不同；停止数值返回/失效cache；Evidence仍读原记录 |
| 409 | SOURCE_CHANGED_DURING_READ / ERROR | 稳定读取期间stat/identity变化；不发送mixed bytes；可重试 |
| 409 | REVISION_UNAVAILABLE / ERROR | 请求无法解析的registry/release revision；不自动换当前结果 |
| 409 | ACCOUNT_ALREADY_EXISTS / ERROR | 注册提交已存在规范化email；唯一DB约束作最终判断 |
| 415 | UNSUPPORTED_MEDIA_TYPE / ERROR | 账号JSON POST的Content-Type不支持；domain SYSTEM |
| 422 | UNSUPPORTED_COMBINATION / UNSUPPORTED | 语法正确但超出已核验组合：q=.2、Cylinder C_u、Closure B_u CFL.1、Fig13 mode16 |
| 422 | INVALID_OR_EXPIRED_CODE / ERROR | code过期/错误/locked/consumed/email-purpose不匹配；统一账号文案，不返回存储状态或正确code |
| 429 | RATE_LIMITED / ERROR | resend/email/IP/login限制；Retry-After秒数；details可显示冷却规则，不泄漏其他用户信息 |
| 500 | SOURCE_READ_ERROR / ERROR | 受控源解析/权限/文件损坏失败；server log request_id定位，无路径/stack泄漏 |
| 500 | CANONICAL_SCHEMA_MISMATCH / ERROR | source或adapter输出违背05；不是用户ValidationError |
| 500 | INTERNAL_ERROR / ERROR | 未分类异常，统一安全文案 |
| 503 | FEATURE_NOT_ENABLED / ERROR | 账号关闭、尚未交付模块/API；delivery进度不能冒充科学缺失 |
| 503 | MAIL_SERVICE_UNAVAILABLE / ERROR | SMTP连接/认证/提交失败；不激活新challenge；旧有效challenge保留 |
| 503 | ACCOUNT_STORE_UNAVAILABLE / ERROR | MySQL连接/事务存储失败，仅账户受影响 |

领域分类：科学目标/组合/源错误domain SCIENTIFIC；请求/routing/internal domain SYSTEM；账号domain ACCOUNT。错误中的retryable显式：unsupported/invalid/known missing=false，临时source race/服务不可用=true，corrupt schema/真实数据漂移=false（需核查，不循环请求修复）。500SOURCE_READ_ERROR可由typed cause判断临时/长期，不能统一无限重试。

优先级：先syntax400，再experiment404，再识别已知不支持config/组合422，其他未知config404，再registered result/field404，再availability/source checks。Cylinder C_u是已知不支持，永远422，不能某路由变UNKNOWN_CONFIG。未知result与known missing通过registry逻辑目标区分，不能靠FileNotFoundError猜实验身份。

# 6. System / registry / content operations

以下及后续表：所有成功模型都包装ApiEnvelope<T>；文档资源DOC01/02例外。GET均可RegistryQuery。首切片标Alpha，Full表示首切片后现有P0扩展，Account独立追加设计，不是科学首切片必需。

| Operation ID | Method / path | Response T | Destination / phase |
| --- | --- | --- | --- |
| SYS01 | GET /system | ProjectInfo | P01/P02/system shell；Alpha |
| REG01 | GET /experiments | ExperimentList | P02/P04；Alpha先联通Case8，其他PLANNED |
| REG02 | GET /experiments/{experiment_id} | Experiment | P06 overview；Alpha Case8 |
| REG03 | GET /experiments/{experiment_id}/configs | ConfigList | P06 selectors；Alpha Case8 |
| REG04 | GET /experiments/{experiment_id}/capabilities | CapabilityList | P06 tabs/controls；Alpha Case8 |
| CONTENT01 | GET /explore/scenes | SceneList | P03；Full；7scene |
| CONTENT02 | GET /explore/scenes/{scene_id} | ScenePreset | P03；Full；scene1…7 |
| CONTENT03 | GET /mechanism | MechanismContent | P05/P03 S2/3；Full；SCHEMATIC |
| DEF01 | GET /definitions | DefinitionList | 科学plot注释；按semantic过滤 |
| DEF02 | GET /definitions/{definition_id} | ScientificDefinition | scope/公式/units/detector；Alpha当前所用定义 |
| MASK01 | GET /masks/{mask_id} | MaskSpec | 固定overlay；按受控array_ref取bool数组；Full/按切片 |
| DOC01 | GET /openapi.json | 原生OpenAPI3.1 document | 开发/审核；Alpha契约工具 |
| DOC02 | GET /api/docs（无/api/v1重复前缀） | HTML local Swagger UI | 开发/审核；Alpha契约工具 |

表内除DOC02外path均相对`/api/v1`。实验列表轻量，只发6个canonical metadata；fields/array/数万points不在启动列表中。REG02自然提供Case8 experiment metadata，不再重复 `/case8/metadata` 第二权威字段集。capability由后端registry提供，不让frontend硬写Cylinder无Spectrum。

# 7. Case8 operations

SNAPSHOT_INDEX_CONVENTION = USER_VISIBLE_1_BASED_RECORDED_INDEX。所有 /snapshots/{snapshot_index} 及相关selector使用严格1-based编号：Case8 1…6、Cylinder 1…5；0不允许。初始保存帧可为 snapshot_index=1、step_index=0；step_index 是 completed accepted steps，原source_step_index可保留，不能重新编号科研文件。路径/selector中0按既有 INVALID_REQUEST 拒绝，不作为初态别名。

基础path：`/experiments/case8/configs/{config_id}`，A_u/B_u/C_u/D_u。metadata/config/capability使用REG02/03/04，evidence使用EVI通用操作。

| Operation | GET relative path | Query / T | Scientific rule |
| --- | --- | --- | --- |
| C801 | {base}/snapshots | RegistryQuery → SnapshotIndex | 每组恰6真实step/time/fields；只有refs，无values |
| C802 | {base}/snapshots/{snapshot_index} | SnapshotQuery → FieldSnapshot | index1…6；不允许time插帧；field筛选只投影已有metadata |
| C803 | {base}/snapshots/{snapshot_index}/fields/{field_id} | RegistryQuery → FieldResponse | 真实field header/source/domain/array_ref；ARRAY01取值 |
| C804 | {base}/entropy-history | HistoryQuery → EntropyHistory | 1912 accepted-step、cumulative/step/stage aggregate；sources各自保留 |
| C805 | {base}/scalar-series/{series_id} | HistoryQuery（禁止重复series query）→ ScalarSeries | 具体semantic series；不能用display name认科学量 |
| C806 | {base}/metrics | MetricQuery → MetricCollection | width/RMS/HF定义/detector/time_scope；terminal不随游标虚变 |
| C807 | {base}/allocation | RegistryQuery → AllocationResult | 仅D_u FACE_FIELD，DIAGNOSTIC_RERUN；A/B/C404known missing |
| C808 | {base}/snapshot-alignment | AlignmentQuery → SnapshotAlignment | scalar completed step1…1912；nearest真实帧与两个时间，fixed同距规则 |

C802第6帧实际completed_step1912、physical_time.08；中间time取NPZ，不能0.016/.032/.048/.064简单圆整。Flow和native-face instantaneous可来自不同asset/status，field独立header；如混合catalog top snapshot Verification PARTIAL，已核验字段依旧各有status。C804 source_step_index0…1911，canonical endpoints1…1912，CSV time_end与snapshot completed_steps的关系必须正确。series参数允许值由registry列完整ID，例如case8.D_u.E_at_cumulative，不能自由公式。

# 8. Gate operations

| Operation | GET path | Response T | Rule |
| --- | --- | --- | --- |
| GATE01 | /experiments/gate/gates | GateRegistry | 三gate matched q metadata来自冻配置 |
| GATE02 | /experiments/gate/gates/{gate_id}/allocation | AllocationResult | CELL_FIELD，STATIC+TRAJECTORY_INTEGRATED，array[32,128] |
| GATE03 | /experiments/gate/gates/{gate_id}/summary | AllocationSummary | E_at、cell-window份额、measure、curve slot |
| GATE04 | /experiments/gate/comparison | GateComparison | 三图metadata/refs、共同extent/color、approximately matched |

Gate IDs exact Acoustic/Pressure/Ungated。无entropy-history、无arbitrary q/time/map播放；额外q_at/time query400。GATE04仅按这三张真实array计算共同渲染范围，不能把map数值先normalize偷偷改；single图保留同comparison color scale，可显式切换显示但必须说明。Gate `sum(map)=E_at`，不可二次乘dt/dxdy。分配curve若需派生只经明确adapter processing验证，不能直接假装现有生产记录。

# 9. Entropy closure operations

| Operation | GET path | Query / T | Rule |
| --- | --- | --- | --- |
| CLO01 | /experiments/entropy-closure/runs | RegistryQuery → ClosureRunRegistry | 五个确立组合，不把config×CFL自由相乘 |
| CLO02 | /experiments/entropy-closure/runs/{run_id} | RegistryQuery → EntropyClosureRun | 例如D_u-cfl-0.05；run协议核定CFL |
| CLO03 | /experiments/entropy-closure/runs/{run_id}/stage-history | HistoryQuery → ClosureHistory | PER_STAGE；G/D/R_SD/eps_SD，stage source1…3→canonical0…2 |
| CLO04 | /experiments/entropy-closure/runs/{run_id}/step-history | HistoryQuery → ClosureHistory | PER_STEP；S/DeltaS/E_*_step/R_time_step/cumulative |
| CLO05 | /experiments/entropy-closure/refinement | RegistryQuery → RefinementSummary | D_u四CFL已有R(T)/slope，B_uzero channel独立 |

run identity中可识别的B_u-cfl-0.1或D_u-cfl-0.03→422 UNSUPPORTED_COMBINATION；其他随机run未知404 INVALID_RESULT_ID。无空间state trajectory接口，不借vortex别组图。Raw member`t_stage_or_step_time`含义显示原定义，不能按stage号构造假时间。

# 10. Spectrum and eigenmode operations

| Operation | GET path | Query / T | Rule |
| --- | --- | --- | --- |
| SPEC01 | /experiments/spectrum/dataset | RegistryQuery → SpectrumDataset | 68records summary与refs，不默认载入所有512values/top32vectors |
| SPEC02 | /experiments/spectrum/curves | SpectrumQuery（q_at必填）→ SpectrumCurve | 一个q恰17ell；对比四曲线可4次请求/缓存 |
| SPEC03 | /experiments/spectrum/modes/{ell} | SpectrumQuery（q_at必填）→ SpectrumRecord | 同base/q/ell的alpha、delta baseline、eigen refs |
| SPEC04 | /experiments/spectrum/modes/{ell}/eigenmode | EigenmodeQuery → Eigenmode | LEFT/RIGHT、rank0…31；values经ARRAY01按需 |
| SPEC05 | /experiments/spectrum/validation-combinations | RegistryQuery → ValidationRegistry | 完整24个Fig13合法mode/q/epsilon组合 |

SPEC05只接受RegistryQuery并返回完整24个组合，不筛选后伪称另一份完整registry。前端从24个supported组合显式选择；SPEC02/03不提供连续q，.2→422。ell0…16允许，但Fig13只有1/4/8/12；SPEC04已有vectors可查全部合法ell，primitive profile/component只有保存/已核验转换可请求。已知缺profile为404 MISSING_SCIENTIFIC_ASSET，不猜rank替代。

raw complex向量ScientificArray每element real/imag；不把512vector length误认为512×32全部eigenvectors。Eigenmode normalization/phase/component order可查；未知限制清楚。View相位只是显示变换，非CFD movie。无serialized Jacobian/Fourier endpoint；数据不存在，registry明确MISSING。

# 11. Modal validation operations

| Operation | GET path | Query / T | Rule |
| --- | --- | --- | --- |
| VAL01 | /experiments/modal-validation/runs | RegistryQuery → ValidationRegistry | 完整24runs |
| VAL02 | /experiments/modal-validation/runs/{run_id} | RegistryQuery → ModalValidationRun | mode/q/epsilon/rank/branch来自summary |
| VAL03 | /experiments/modal-validation/runs/{run_id}/summary | RegistryQuery → ModalValidationSummary | sigma_LIN/RK3/CFD、fraction discrepancy、fit0…32、R2 |
| VAL04 | /experiments/modal-validation/runs/{run_id}/history | HistoryQuery（series禁止）→ ModalValidationHistory | 默认33points；真实time/amplitude/log-amplitude |

run ID例`fig13.m08.q-0.396.eps-1e-5`。API path命名不是科研文件名，以registry映射。33points的page total33；mode16/q.132/非法epsilon已知组合422；不存在其他run随机ID404。只播放projected amplitude，不返回CFD空间帧。Spectrum Validation tab与独立Modal Validation目录用这些相同ID/operation，不复制24runs身份。

# 12. Cylinder operations

base：`/experiments/cylinder/configs/{config_id}`，A_u/B_u/D_u；C_u422。

| Operation | GET relative path | Query / T | Rule |
| --- | --- | --- | --- |
| CYL01 | {base}/snapshots | RegistryQuery → SnapshotIndex | 每组5 metadata，真实step0/2439/4878/7318/9757 |
| CYL02 | {base}/snapshots/{snapshot_index} | SnapshotQuery → FieldSnapshot | instant face现有字段，不承诺5 density movie |
| CYL03 | {base}/snapshots/{snapshot_index}/fields/{field_id} | RegistryQuery → FieldResponse | native geometry、scope、Pi_instantaneous；ARRAY01取值 |
| CYL04 | {base}/entropy-history | HistoryQuery → EntropyHistory | 原9757step scalar；numbering由source核定 |
| CYL05 | {base}/scalar-series/{series_id} | HistoryQuery（series禁止）→ ScalarSeries | unit/definition/interior-only |
| CYL06 | {base}/allocation | RegistryQuery → CylinderAllocationOverview | sectors/band available，2D缺口slot；200 PARTIAL |
| CYL07 | {base}/allocation/sectors | RegistryQuery → AllocationResult | ANGULAR_SECTORS，16bins/17edges；静态累计 |
| CYL08 | {base}/allocation/front-band | RegistryQuery → AllocationResult | REGION_SCALAR，fixedA_u径向±.16、cumulative |
| CYL09 | {base}/metrics | MetricQuery → MetricCollection | centerline/frontmean widths、RMS/HF-RMS原定义及detector floor |

**没有 `/allocation/cumulative-map` 或 `/allocation/heatmap` 科学operation**。在capability/overview返回known missing，ARRAY01不允许从sector result访问虚构二维member。未知API path404统一routing error；不能为缺失map新增实际numerical schema endpoint。如果后续用户强制请求该能力需解决上游缺口/范围变更，本阶段不补数据。

# 13. Cross-flow composite

CMP01 `GET /comparisons/case8-cylinder`，ComparisonQuery → CrossFlowComparison，推荐后端composite。

service统一检查两个合法config、固定revision、结果scope/provenance与局部failure；比frontend随意拼字段更容易保证比对约束和稳定partial。不是新的科学derived ranking；不对两边budget/localization做隐式normalize。数组只发refs，避免composite传多map，前端按当前可见视图用ARRAY01取。

左Case8累计native-face仅D_u；其他config map MISSING但其预算/指标保留。右Cylinder sector/band保留，没有累计2D。ComparabilityRule默认DESCRIPTIVE_ONLY；无赢家/总score，也不把不同mask percentage放统一排名。任何side plot→自己的evidence，composite列两侧全部refs。

# 14. Evidence operations

| Operation | GET path | Query / T | Destination |
| --- | --- | --- | --- |
| EVI01 | /evidence | EvidenceQuery → EvidenceIndex | P08；section CURRENT排除历史/未核验数值主线，GAPS/HISTORY可独立查 |
| EVI02 | /evidence/{evidence_id} | RegistryQuery → EvidenceRecord | P09/quick view；完整method/config/assets/hashes/freeze/processing/verification/limits |
| EVI03 | /results/{result_id}/provenance | RegistryQuery → ResultProvenance | 任意科学图View Evidence；多source全部refs |
| EVI04 | /assets/{asset_id} | RegistryQuery → SourceAsset public DTO | 逐资产说明/hash/status，不是文件下载 |

任何科学成功响应内嵌ProvenanceRef与scientific header；完整Evidence按需加载。这是**混合provenance方案**：小summary常驻、full detail独立，兼顾任意图可查与数值payload大小。data_hash、method hash、current/recorded source hash、ETag分开。source data drift时EVI仍200可检查，数值API409；Evidence加载成功不是该结果可用于数值展示的认证。

EVI01默认limit50并server filter，不将2337资产全传前端。asset绝对路径仅backend locator；公共source_display及受控relative_origin是说明，不是file://下载。没有任意path重定向或attachment从科研根下载。

# 15. Scientific arrays, large payloads and loading

ARRAY01 `GET /results/{result_id}/arrays/{array_id}`，ArrayQuery → ScientificArray（05 §7.3）。result/array_ref精确匹配；只能registered数组，包括field、已核验mask/坐标、eigenvalues/vector/channel。每一个坐标/bin边界数组有自己的semantic/unit/header（例如角度不是integrated entropy）。

snapshot/Allocation/Eigenmode metadata用ArrayRef；服务根据当前selection加载所需一张/一个vector。Gate comparison只有3×4096小中数组，按需取3图；Case8 face分别4128与4096；spectrum block512values、所选vector512elements，不能返回整个4×17×512×32向量库。npz作为后端科学容器，不直接下载给浏览器。

| Transport | Evaluation | V1/future |
| --- | --- | --- |
| nested JSON | 小矩阵直观，但shape/axes重复且跨location不便 | 不作规范array形态 |
| flat JSON + gzip | 类型清楚、shape/axes可校验、浏览器简单、双精度Number | **V1推荐**；exact values、C-order、complex real/imag |
| binary endpoint | 浮点/complex紧凑、高效 | 未来明确byte order/dtype/shape/version/headers后扩展，不能直接裸byte猜 |
| NPZ | 科研Python容器合适；浏览器需ZIP/NumPy解析与whole-file拆解 | 后端只读，非V1 wire格式 |
| MessagePack | 更紧凑，但需额外client codec且complex仍自定义 | 当前无强需要 |
| Arrow | 大表列式优势，嵌套metadata与科学array另需定义 | 未来大表性能实测再评估 |

V1先保留全精度；Case81912/圆柱9757标量和二维4096/4128数组无需预先下采样。Closure多页真实数据不等downsampling。禁用会改变科学点集合的自动chart sampling或标记为rendering-only并可切全点；V1默认不启用。以后任何rendering-only下采样须携带算法、原count/显示count、display-only标签、完整数据入口并单独契约版本；不能从简图重新计算metrics。

metadata first→当前tab history/metric→selected snapshot field→array；进入谱tab才SPEC01/02，选择Modes才SPEC04/ARRAY01，打开Evidence才EVI02。current config切换取消旧请求/拒绝旧generation，Vue Query key带revision/result/selector。缓存保留source IDs/hash/status，不靠ETag当科学验证；数据漂移失效缓存。已观测hash按稳定stat可缓存计算，guard必须核验来源身份及读取前后未变，不能mtime单独认证。

# 16. Account operations — QQ verification and sessions

Account Extension 已设计并保留 MySQL、QQ email、OTP、session、CSRF、Account Blueprint 和 AUTH 契约；交付优先级正式冻结：

```text
ACCOUNT_EXTENSION_PRIORITY=P1_NON_BLOCKING
ACCOUNT_EXTENSION_BLOCKS_P0=NO
ACCOUNT_EXTENSION_BLOCKS_CASE8_SLICE=NO
ENABLE_ACCOUNTS_DEFAULT=false
```

账号不属于 P0 scientific core 或 Case8 Functional Vertical Slice DoD，Account DB/API 不作为 Phase 5 首批必做项。MySQL、QQ SMTP 或 Account Service 不可用时，Entry、Home、Lab、Case8 Replay、Scientific API、Evidence、Explore 与核心 Replay 仍支持 Anonymous Replay。首阶段不优先实现 registration/email code/login/session；后续账号切片仍遵守本文现有安全模型。

AUTH01–AUTH06 的 delivery_phase = P1_NON_BLOCKING；契约保留，implementation deferred。

AccountFeatureInfo在SYS01；账户开关默认关闭，可独立实现/启用。用户已授权**新增账号注册设计**，本轮未授权范围仍限制只写三文档，因此不连接MySQL、发邮件、建表或注册。MySQL+PyMySQL port3308，库名待定；smtp.qq.com465 SSL、环境发件账号与SMTP授权码；docs无secret。

| Operation | Method / relative path | Request → T | Status / side effect |
| --- | --- | --- | --- |
| AUTH01 | GET /auth/csrf | 无body → CsrfTokenResponse | 200、no-store，绑定匿名/已登录浏览器CSRF cookie状态 |
| AUTH02 | POST /auth/email-verification-challenges | VerificationCodeRequest → VerificationChallengeResponse | 200、SMTP_ACCEPTED；投递到用户输入的QQ邮箱；不是固定sender收件 |
| AUTH03 | POST /auth/register | RegistrationRequest → RegistrationResponse | 201、原子创建用户/consume code；login_required=true |
| AUTH04 | POST /auth/login | LoginRequest → SessionResponse | 200、Set-Cookie session+旋转CSRF |
| AUTH05 | GET /auth/me | session cookie → SessionResponse | 200或401；过期/dropped session不延期 |
| AUTH06 | POST /auth/logout | EmptyAccountRequest → LogoutResponse | 200幂等，清cookie/吊销session；需CSRF同源 |

三POST body必须application/json（logout可无body）；不支持form-urlencoded；Origin为受控同源，X-CSRF-Token与cookie绑定。Content-Type不符415 UNSUPPORTED_MEDIA_TYPE（domain SYSTEM，availability ERROR）；OPTIONS按明确开发CORS策略，不由generic JSON error吞header。401不把未登录误报科学MISSING。

验证码默认6位，TTL600s、max5wrong attempts、60s cooldown、email5/hour/IP20/hour；login IP20/15min。Server rate-limit原子占用MySQL rate_limit row，返回429 Retry-After。code HMAC摘要且constant-time比较，不日志/返回；SMTP发送时不持DB事务；generation处理乱序回执，只有成功激活的新码替换旧active，失败保留旧码。详见04§23及05§16。

注册不是只验证字符串：锁challenge，校验email/purpose/state/expire/attempts，同事务唯一user insert+consume，wrong attempt计数须提交；并发两次最多一个user。password12…128 scrypt，session opaque24h DB only digest。MailService/DB unavailable503、Replay照常匿名访问。cookie HttpOnly、SameSite=Lax、HTTPS Secure；loopback HTTP明确local例外。账户状态无FROZEN_VERIFIED/科学Evidence，也不扩导航或新增账号页面，Entry/system壳AccountDialog。

账号邮箱格式以05一致策略校验：ASCII邮箱、@qq.com域、trim+domain lowercase、local part保留；真正所有权由验证码证明。SMTP_SSL使用验证证书/主机名的TLS context和有限timeout，不把SSL开关等同无需证书校验。

# 17. Request/response examples

例子使用05§18的**文档模板展开**；`@EXnn`表示将对应完整canonical模板展开到data位置，`@R/@U/@V`展开05明确类型。数字占位符必须由真实来源替换，不是可执行JSON fixture，API绝不返回@字符串或`<from canonical source>`。这里完整给出wire envelope和T绑定；不重复另一套科学字段。实际每例的展开结果必须通过同Pydantic serialization schema；mock必须独立MOCK。

共用展开：`@CURRENT_REGISTRY`/`@CURRENT_DATA`为`{state:KNOWN,value:<actual revision ID>}`，无release时不用虚构release ID。request_id是示例追踪ID非实际服务器ID。

## API-EX01 — List experiments

Request：`GET /api/v1/experiments`

```json
{"schema_version":"1.0.0","request_id":"example-reg01","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":{"items":["@EX01","<complete Experiment gate>","<complete Experiment entropy-closure>","<complete Experiment spectrum>","<complete Experiment modal-validation>","<complete Experiment cylinder>"]},"issues":[]}
```

所有Experiment字段按05§4，不含values。本例描述首切片交付完成后的目标状态：仅Case8 IMPLEMENTED，其余PLANNED；当前Phase4 Freeze尚无operation实现。真实capability保留，Near1D不列。

## API-EX02 — Case8 D_u recorded snapshot 6

Request：`GET /api/v1/experiments/case8/configs/D_u/snapshots/6?field=density`

```json
{"schema_version":"1.0.0","request_id":"example-c802","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":"@EX02","issues":[]}
```

data是FieldSnapshot、index6/step1912/time.08；FieldDescriptor给array_ref。接着`GET /api/v1/results/case8.D_u.snapshot.6.density/arrays/density`取4096值：

```json
{"schema_version":"1.0.0","request_id":"example-array01","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":{"result":"<EX02.fields[0].result展开>","descriptor":{"array_id":"density","dtype":"float64","shape":[32,128],"order":"C","axes":["y","x"],"encoding":"FLAT_JSON","element_count":4096},"values":"<all 4096 original float64 numbers in C order>"},"issues":[]}
```

## API-EX03 — Case8 entropy history

Request：`GET /api/v1/experiments/case8/configs/D_u/entropy-history?series=case8.D_u.E_at_cumulative&offset=0&limit=1`

```json
{"schema_version":"1.0.0","request_id":"example-c804","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":{"experiment_id":"case8","config_id":"D_u","series":["@EX03"],"stage_aggregate_refs":["<registered dotE_at_s0/s1/s2 series IDs>"],"snapshot_alignment":{"state":"NOT_APPLICABLE","reason":"No scalar selection in history request; C808 supplies alignment"},"limitations":[{"id":"lim.case8.dense-fields","code":"DISCRETE_RECORDED_ONLY","description":"1912 scalar points correspond to six recorded spatial snapshots","affected_refs":["case8.D_u.E_at_cumulative"],"severity":"WARNING"}],"evidence_refs":["ev.case8.D_u.E_at_cumulative"]},"issues":[]}
```

此分页例只1点，total仍1912；默认请求取全1912。selected_scalar_step1经C808对应source history step0，时间取time_end。

## API-EX04 — Gate Pressure allocation

Request：`GET /api/v1/experiments/gate/gates/Pressure/allocation`

```json
{"schema_version":"1.0.0","request_id":"example-gate02","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":"<EX04完整结构替换gate/config=Pressure、result=gate.Pressure.allocation、asset=asset_6850b4bab5cc及对应summary/evidence；matched q从Pressure配置.31018332312583474，不替换成.396>","issues":[]}
```

array_ref shape32×128；取ARRAY01；sum=E_at，无time播放参数。

## API-EX05 — Spectrum q_at=.396 curve

Request：`GET /api/v1/experiments/spectrum/curves?q_at=0.396`

```json
{"schema_version":"1.0.0","request_id":"example-spec02","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":{"dataset_id":"spectrum.common-mach6.v1","q_at":0.396,"records":"<17 complete SpectrumRecord objects ell0..16; ell8 is EX05; every delta has same-ell q0 baseline>"},"issues":[]}
```

## API-EX06 — Mode8 eigenmode

Request：`GET /api/v1/experiments/spectrum/modes/8/eigenmode?q_at=0.396&side=RIGHT&rank=0&representation=COMPLEX_VECTOR`

```json
{"schema_version":"1.0.0","request_id":"example-spec04","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":{"result":"@R(spectrum.q-0.396.ell-8.right.rank-0,eigenmode,FROZEN_PRODUCTION,STATIC/NONE,spectrum.common-base,model_normalized_mode,FROZEN_VERIFIED,[asset_8f3a3aa5c631,asset_3b8c484e13f4])","eigenmode_id":"spectrum.q-0.396.ell-8.right.rank-0","spectrum_record_id":"spectrum.q-0.396.ell-8","ell":8,"q_at":0.396,"side":"RIGHT","rank":0,"branch_id":{"state":"UNKNOWN","reason":"Bind stored branch metadata, not infer from rank"},"eigenvalue":{"real":"<from canonical source>","imag":"<from canonical source>"},"normalization":{"id":"spectrum.stored-normalization","definition":{"state":"UNKNOWN","reason":"Bind saved normalization/source convention during adapter implementation"},"phase_convention":{"state":"UNKNOWN","reason":"Do not guess phase"},"component_order":{"state":"UNKNOWN","reason":"Read source ordering before primitive conversion"},"processing_ref":{"state":"NOT_APPLICABLE","reason":"Stored complex vector format projection"},"evidence_refs":["ev.spectrum.normalization"]},"component":"stored_vector","representation":"COMPLEX_VECTOR","domain":"<SpatialDomain PROFILE_CELL shape[128,4], source x128 plus explicit conservative component dimension; 512 elements are not512 spatial cells>","values_ref":{"result_id":"spectrum.q-0.396.ell-8.right.rank-0","descriptor":{"array_id":"eigenvector","dtype":"complex128","shape":[128,4],"order":"C","axes":["x","conservative_component"],"encoding":"FLAT_JSON","element_count":512}},"mask":"<MaskSpec SPECTRUM_FIXED_SHOCK_CELLS 58..66>","localization":"<ResourceSlot<Metric> from fixed-mask saved/verified localization>"},"issues":[]}
```

normalization未知时显示限制，不生成primitive profile。ARRAY01返回512个{real,imag}；前端real/magnitude是显式显示投影，不改变正式认证。

## API-EX07 — Fig13 run

Request：`GET /api/v1/experiments/modal-validation/runs/fig13.m08.q-0.396.eps-1e-5`

```json
{"schema_version":"1.0.0","request_id":"example-val02","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":"@EX06","issues":[]}
```

history：`GET /api/v1/experiments/modal-validation/runs/fig13.m08.q-0.396.eps-1e-5/history` → ApiEnvelope<ModalValidationHistory>，points33、step0…32、actual physical_time/amplitude/log_amplitude，summary同EX06。values不从eigenmode相位模拟生成。

## API-EX08 — Cylinder D_u sectors and partial availability

Request：`GET /api/v1/experiments/cylinder/configs/D_u/allocation/sectors`

```json
{"schema_version":"1.0.0","request_id":"example-cyl07","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":"@EX07","issues":[]}
```

sector16/edges17、interior-only cumulative；geometry array header为angle unit，channel header为model entropy。Overview `GET .../allocation`：

```json
{"schema_version":"1.0.0","request_id":"example-cyl06","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"PARTIAL","data":{"experiment_id":"cylinder","config_id":"D_u","sectors":{"availability":"AVAILABLE","value":"@EX07"},"front_band":{"availability":"AVAILABLE","value":"<REGION_SCALAR AllocationResult with fixed-front mask/cumulative scalar/fraction>"},"cumulative_2d":{"availability":"MISSING","error":"@MISSING_CYLINDER_MAP"},"limitations":[{"id":"lim.cylinder.no-cumulative-map","code":"NO_FULL_CUMULATIVE_2D","description":"Only cumulative angular sectors and fixed-band scalar are saved","affected_refs":["missing_cylinder_trajectory_spatial_pi_at"],"severity":"WARNING"}],"evidence_refs":["ev.cylinder.D_u.sectors","ev.cylinder.D_u.front-band","ev.missing.cylinder-cumulative2d"]},"issues":["@MISSING_CYLINDER_MAP"]}
```

`@MISSING_CYLINDER_MAP`展开：

```json
{"domain":"SCIENTIFIC","code":"MISSING_SCIENTIFIC_ASSET","message":"Full trajectory cumulative 2D Pi_at is not available; sector and band results are available","target":{"resource_type":"cumulative_2d","identity":{"state":"KNOWN","value":"missing_cylinder_trajectory_spatial_pi_at"}},"retryable":false,"details":[],"evidence_refs":["ev.missing.cylinder-cumulative2d"]}
```

## API-EX09 — Evidence Detail

Request：`GET /api/v1/evidence/ev.case8.D_u.snapshot.6.density`

```json
{"schema_version":"1.0.0","request_id":"example-evi02","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"AVAILABLE","data":"@EX08","issues":[]}
```

VERIFIED_NOT_FROZEN不能被metadata200改成FROZEN_VERIFIED；UNKNOWN/current-source观察与checkpoint freeze缺口可见，无absolute_path。

## API-EX10 — Unsupported q_at

Request：`GET /api/v1/experiments/spectrum/curves?q_at=0.2`

HTTP422：

```json
{"schema_version":"1.0.0","request_id":"example-unsupported","registry_revision":"@CURRENT_REGISTRY","data_revision":"@CURRENT_DATA","availability":"UNSUPPORTED","error":{"domain":"SCIENTIFIC","code":"UNSUPPORTED_COMBINATION","message":"q_at is not in the verified spectrum set","target":{"resource_type":"spectrum_curve","identity":{"state":"KNOWN","value":"spectrum"}},"retryable":false,"details":[{"field":"q_at","issue":"Outside the recorded discrete parameter set","allowed_values":["0","0.132","0.264","0.396"]}],"evidence_refs":["ev.spectrum.protocol"]},"issues":[]}
```

这不是empty曲线/自动近邻.264/500。Cylinder C_u和Fig13 mode16同类422；Case8 A_u累计map为known missing404，不能混成unsupported参数。

## API-EX11 — Registration extension

先AUTH01获取CSRF；AUTH02 `POST /api/v1/auth/email-verification-challenges`，headers Origin同源、X-CSRF-Token实际值，body `{"email":"<registrant @qq.com mailbox>","purpose":"REGISTER"}`。

```json
{"schema_version":"1.0.0","request_id":"example-auth02","registry_revision":{"state":"NOT_APPLICABLE","reason":"Account operation"},"data_revision":{"state":"NOT_APPLICABLE","reason":"No scientific data"},"availability":"AVAILABLE","data":{"challenge_id":"<actual UUID>","email":"<registrant @qq.com mailbox>","purpose":"REGISTER","expires_in_seconds":600,"resend_after_seconds":60,"delivery_status":"SMTP_ACCEPTED"},"issues":[]}
```

AUTH03 `POST /api/v1/auth/register`，body fields `email,challenge_id,code,password,display_name`；此文不填password/真实code。HTTP201 data=`{user:AccountUser,login_required:true}`。登录200 token只在Set-Cookie；重发429 Retry-After；SMTP失败503 AUTH domain错误；请求和响应均无科学verification。

# 18. Contract tests and scientific regression plan

只设计未来检查，不创建测试文件、不安装依赖、不运行CFD。Fixture使用受控临时test workspace或fake，不改科研源。准确的浮点回归tolerance按已有协议/每量定义，不能随意“合理近似”；原time/identity/value序列默认序列化roundtrip一致。

| Test class | Required proof |
| --- | --- |
| Contract/schema | 每operation path/method/request/response/errors与catalog/OpenAPI/TS一一对应；Fact/union/extra/finite/shape/serialization正确；post body错误400不含raw input |
| Identity | 六experiments独立；Case8 config four、Cylinder three；random ID404；known unsupported C_u422；不同副本显式asset而非按文件名合并 |
| Case8 regression | 4×6 snapshot actual step/time/fields；C802第6帧1912/.08与canonical source完全一致；CSV1912/source_step0→completed1；真实E_*序列及metrics定义/来源 |
| Temporal semantics | scalar/snapshot不共享同粒度；nearest strict同距早time/小index；换config重新匹配；PINNED恢复；stage0…2/source1…3、increment/cumulative分开 |
| Gate semantics | 三32×128map sum=各E_at；无double measure；matched config非Case8；固定cell mask和shared scale；无time/q插值 |
| Closure | 五run row counts、3stage*steps；CFL从protocol核定，metadata correction可追溯；非法config/CFL422，不empty；R_time_step与cumulative定义保留 |
| Spectrum | 完整68唯一q×ell、512/block、top32左右；fixed mask、delta baseline；complex实虚往返；unsupported q422、NaN400；无matrix伪接口 |
| Fig13 | 全24runs×33points；selected mode/q/epsilon/branch来自source；fit0…32 inclusive；relative fraction；真实amplitude，不CFD field movie |
| Cylinder | 三config、9757scalar、五actual face；16sectors/17edges、band cumulative/interior-only；累计2Dslot MISSING且无value；无fake heatmap |
| Provenance | 所有科学结果evidence_refs与actualasset一致；source/data hashes分别；SOURCE_DATA_DRIFT409、源码drift显示原结果限制；cache不跨revision误报verified |
| Availability/errors | known missing404、unknown404不同code；组合partial200/slots；source load500；404/405 JSON且Allow保留；no SPA fallback API；plots失败不清其他tab |
| Accounts | QQ recipient与sender独立、SMTP_SSL465；验证码过期/五次错/冷却/发送失败/回执乱序；并发唯一用户与consume；密码scrypt/cookie/CSRF；secret不进DTO/log；DB/SMTP失败不影响Replay |
| UI/e2e | 五模板Entry→Home→Lab→Case8→Evidence→返回；URL恢复、request race、config切换取消、MOCK标识；本机断网冷启动Replay和docs本地资源可用 |

响应校验通过不能取代scientific regression；HTTP200不能取代scope/semantic/provenance验证。账号unit用fake repository/mail/clock；行锁/并发integration用隔离MySQL，不用SQLite替代；真实邮箱测试不自动发送。

# 19. Joint decision summary and review boundary

FRONTEND_STACK=Vue 3 + TypeScript + Vite + Vue Router；BACKEND_STACK=Flask + Python；CHART_STACK=Apache ECharts；FIELD_RENDER_STACK=Native Canvas 2D；STATE_MANAGEMENT=URL/Vue Router + Pinia + TanStack Vue Query；API_CLIENT=openapi-typescript + openapi-fetch；TEST_STACK=pytest/Flask test client/NumPy + Vitest/Vue Test Utils + Playwright。

此处冻结的是设计决定。OpenAPI/canonical registry/mock/DB/Release Bundle的创建属于后续实施；没有提前开始。CASE8_VERTICAL_SLICE_TECH_PLAN和十二步DoD位于04末尾；先完成五模板真实链路和Evidence，D_u累计图随后独立接入，账号不阻塞科学首切片。

非阻塞未决项同04 Q1…Q5：历史源码归档、SI映射/分发许可、Cylinder几何/primitive字段、硬件性能、MySQL库名/账号实际交付阶段。**OPEN_QUESTIONS_COUNT=5**。缺答案时保守Fact/能力表达；发布/可执行复现前解决对应门槛，不为设计PASS新增科研任务。

## PHASE4_ACCEPTANCE_RECORD

### Implementation delivery freeze

```text
SCHEMA_DESIGN_SCOPE=FULL_V1
SCHEMA_IMPLEMENTATION_STRATEGY=BY_VERTICAL_SLICE
```

所有operation在本次Freeze时均为 CONTRACT_DEFINED、尚未 IMPLEMENTED；contract定义完成与软件交付状态分开，既有metadata DeliveryStatus仍使用PLANNED/IMPLEMENTED，不为此改变公开DTO。

| Delivery group | Contract status at freeze | Implementation policy |
| --- | --- | --- |
| SYS01、REG01–04、DEF01/DEF02、C801–06/C808、ARRAY01、EVI02/EVI03 | CONTRACT_DEFINED | 首批Case8切片进入实现；当前尚未开始 |
| EVI04及首切片实际使用的共享契约/文档能力 | CONTRACT_DEFINED | 仅确实需要时实现，不扩大Day1 DoD |
| C807、EVI01、CONTENT、MASK及其余Gate/Closure/Spectrum/Validation/Cylinder/Cross-flow operations | CONTRACT_DEFINED | IMPLEMENTATION_DEFERRED；对应切片到达再实现 |
| AUTH01–AUTH06 | CONTRACT_DEFINED | IMPLEMENTATION_DEFERRED；delivery_phase=P1_NON_BLOCKING |

Case8 DoD不依赖Accounts、Gate或Spectrum等其他切片；保留全部现有契约，不要求Phase5 Day1全部实现。文档版本1.0.1仅为澄清补丁，既有payload schema_version=1.0.0、/api/v1及API语义保持不变。

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

验收只指三份技术设计联合检查，不表示已实现或科学重认证；上游SHA核对保持原值。数据库/邮件未连接，密码和SMTP授权码未写文档。

```text
TECHNICAL_FOUNDATION=PASS
UPSTREAM_SCOPE_READ=YES
UPSTREAM_INVENTORY_READ=YES
UPSTREAM_PRD_READ=YES
UPSTREAM_IA_READ=YES
SYSTEM_ARCHITECTURE_CREATED=YES
DATA_SCHEMA_CREATED=YES
API_CONTRACT_CREATED=YES
FRONTEND_STACK=Vue 3 + TypeScript + Vite + Vue Router
BACKEND_STACK=Flask + Python
CHART_STACK=Apache ECharts
FIELD_RENDER_STACK=Native Canvas 2D
STATE_MANAGEMENT=URL/Vue Router + Pinia + TanStack Vue Query
ARCHITECTURE_SCHEMA_ALIGNED=YES
SCHEMA_API_ALIGNED=YES
IA_API_ALIGNED=YES
CASE8_VERTICAL_SLICE_PLAN_DEFINED=YES
CAPABILITY_MODEL_DEFINED=YES
PROVENANCE_MODEL_DEFINED=YES
SCIENTIFIC_STATUS_MODEL_DEFINED=YES
ERROR_CONTRACT_DEFINED=YES
PARTIAL_RESULT_CONTRACT_DEFINED=YES
ACCOUNT_REGISTRATION_DESIGN_DEFINED=YES
FRONTEND_CODE_WRITTEN=NO
BACKEND_CODE_WRITTEN=NO
PACKAGES_INSTALLED=NO
CFD_RUNS_STARTED=0
SCIENTIFIC_FILES_MODIFIED=NO
UPSTREAM_DOCS_MODIFIED=NO
DATABASE_CONNECTED=NO
EMAILS_SENT=0
NEXT_PHASE=CASE8_FUNCTIONAL_VERTICAL_SLICE
NEXT_PHASE_STARTED=NO
OPEN_QUESTIONS_COUNT=5
```

# CROSS_DOCUMENT_CONSISTENCY_MATRIX

本表闭合04 owner → 05 schema → 06 operation → 已冻结IA目的地；Account是用户明确追加的弹窗，不增第十页面。schema通用helper通过持有实体公开，不要求每helper有独立REST资源。

| Capability | Architecture owner (04) | Schema (05) | API (06) | IA destination |
| --- | --- | --- | --- | --- |
| System identity / entry/home | RegistryService / shared shell | ProjectInfo / ExperimentRef | SYS01 | P01/P02；Entry静态可用不以接口成功为门禁 |
| Experiment registry/configs | RegistryService | Experiment / ExperimentConfig / ConfigList | REG01–03 | P04/P06，六独立实验 |
| Capability-driven controls/tabs | RegistryService / services | ExperimentCapability / ConfigCapability / ControlSpec / CapabilityList | REG04 | P06，按族/当前config隐藏与禁用 |
| Case8 snapshots | Case8Adapter / Case8Service | SnapshotIndex / FieldSnapshot / FieldDescriptor / FieldResponse / ScientificArray | C801–03 + ARRAY01 | P06 Flow；P03S2上下文 |
| Case8 entropy | Case8Adapter / Case8Service | EntropyHistory / ScalarSeries / ScalarPoint | C804–05 | P06 Entropy，P03S1 |
| Scalar/snapshot alignment | Case8Service | SnapshotAlignment / TimeSpec | C808 | P06双时间、URL恢复 |
| Case8 metrics | Case8Adapter / Case8Service | MetricCollection / Metric / DetectorSpec / ScientificDefinition | C806 + DEF01–02 | P06 Metrics |
| Case8 D_u native-face allocation | Case8Adapter / Case8Service | FACE_FIELD AllocationResult / AllocationField / AllocationSummary / MeasureConvention | C807 + ARRAY01/MASK01/EVI | P06 Allocation、P07/P03S6，DIAGNOSTIC_RERUN |
| Gate allocation / comparison | GateAdapter / GateService | GateRegistry / CELL_FIELD AllocationResult / GateComparison / SpatialCurve | GATE01–04 + ARRAY01/MASK01 | P06 Gate、P03S4 |
| Entropy closure | EntropyClosureAdapter / ClosureService | EntropyClosureRun / ClosureRunRegistry / ClosureHistory / RefinementSummary | CLO01–05 | P06 Semi-/Fully-discrete，PER_STAGE≠PER_STEP |
| Spectrum | SpectrumAdapter / SpectrumService | SpectrumDataset / SpectrumCurve / SpectrumRecord / SpectralBaseline | SPEC01–03 + ARRAY01 | P06 Spectrum/P03S5；同ell q0 baseline |
| Eigenmode | SpectrumAdapter / SpectrumService | Eigenmode / NormalizationSpec / ComplexValue / MaskSpec | SPEC04 + ARRAY01/MASK01/DEF | P06 Modes/P03S5；非CFD movie |
| Fig13 | ModalValidationAdapter / ValidationService | ValidationRegistry / ModalValidationRun / Summary / History / ModalPoint | SPEC05 + VAL01–04 | P06 Validation，两入口共享24×33 |
| Cylinder snapshots/scalars/metrics | CylinderAdapter / CylinderService | FieldSnapshot / EntropyHistory / ScalarSeries / MetricCollection | CYL01–05/09 + ARRAY01 | P06 Flow/Entropy/Metrics；5instant face |
| Cylinder sectors / front band / missing2D | CylinderAdapter / CylinderService | CylinderAllocationOverview / ANGULAR_SECTORS / REGION_SCALAR / ResourceSlot | CYL06–08 + ARRAY01 | P06 Sector Allocation、P07/P03S6 |
| Cross-flow | ComparisonService | CrossFlowComparison / CrossFlowSide / ComparabilityRule | CMP01 | P07/P03S6；独立定义，无统一ranking |
| Evidence / provenance / asset | EvidenceAdapter / EvidenceService | EvidenceIndex / EvidenceRecord / ResultProvenance / SourceAsset / Verification / ProcessingRecord | EVI01–04 | P08/P09/quick view/P06Evidence/P03S7 |
| Scientific definitions / masks / units | registry + owning adapter | ScientificDefinition / MaskSpec / SpatialDomain / UnitSpec / ScopeSpec | DEF01–02 / MASK01 / 持有实体 / ARRAY01 | 任意plot说明与overlay |
| Explore curated state | ContentService / guided wrapper | SceneList / ScenePreset / ScientificTarget | CONTENT01–02 +相同科学operation | P03七Scene，不另复制backend |
| Mechanism explanation | ContentService / shared MechanismView | MechanismContent / Node / Edge | CONTENT03 + EVI | P05/P03S2/S3；SCHEMATIC，非Near1D numerical |
| Unified scientific failures/partial | app central handler / services | ApiEnvelope / ErrorBody / ResourceSlot / Fact / ScientificLimitation | 所有API的5节映射 | page/tab/plot隔离，无零补缺失 |
| Contract validation/documentation | app factory / Pydantic / operation catalog | 上述请求/DTO和serialization JSON Schema | DOC01–02 +全operation tests | 开发契约，不新增业务模板 |
| QQ verification / registration | AccountService / MailService / AccountRepository | VerificationCodeRequest / ChallengeResponse / RegistrationRequest / Response / MySQL tables | AUTH01–03 | Entry/system壳AccountDialog |
| Login / session / logout | AccountService / AccountRepository | LoginRequest / SessionResponse / AccountUser / LogoutResponse | AUTH04–06 | 同一AccountDialog/system壳；Replay匿名 |

停止点：Phase4技术基础已正式冻结，等待人工确认 Freeze。`NEXT_PHASE_STARTED=NO`；尚未创建前后端工程、数据库、测试、release数据或新科学结果。

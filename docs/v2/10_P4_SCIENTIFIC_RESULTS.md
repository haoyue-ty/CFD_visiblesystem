# V2-P4 科学结果定义与来源

日期：2026-10-03（Asia/Shanghai）。适用：本软件 Case8 新运行及既有 P2/P3 完成 Run 的只读投影。

## 结果契约

`ScientificRunResult` 包含独立 identity、归一化 config、runtime、fields、真实 snapshot 索引、entropy、metrics、allocation、limitations、provenance。`result_hash` 为去除自身字段后的规范 JSON SHA-256；它与 `scientific_result.json` 文件 SHA-256、Solver 原始 `result.json` SHA-256、方法 SHA-256、配置 hash、科学源依赖 hash 分别记录。新 Run 不继承 V1 的冻结身份，也不根据模板自动获得论文复现结论。

新 worker 在 POSTPROCESSING 时计算并严格验证契约，原子写入 `scientific_result.json`，再将该文件纳入最终 provenance 输出清单。Manager 复核所有登记输出 hash 和结果 identity 后才能发布 COMPLETED。结果页、view context 及后续 AI/报告均使用同一契约和 `result_hash`。

旧 Run 缺少该文件时，在只读结果 API 中按当前后处理版本投影其自身已验证的产物，不写回、不补算轨迹、不借用 V1。旧 Run 的后处理 hash 属于此次投影代码；Solver 包装版本仍保留原运行时的登记 hash。不存在累计 face 数据时返回 `arrays=null, scalar_totals=null, availability=UNAVAILABLE, reason`；真实零通道返回 AVAILABLE 和实际零数组。

## 派生场

U 的原生 shape 为 `[Ny,Nx,4]`，分量为 `[rho,rho*u,rho*v,E]`。公开 cell 字段 shape 为 `[Ny,Nx]`、axes 为 `[y,x]`、C order，附真实 cell center 坐标、domain extent、snapshot ID/time 和输入 NPZ hash。

| 字段 | 算法 | 单位 |
| --- | --- | --- |
| density | U[...,0] | model density |
| pressure | (gamma−1) × (E−(mx²+my²)/(2rho)) | model pressure |
| velocity_x / velocity_y | mx/rho、my/rho | model velocity |
| speed | sqrt(u²+v²) | model velocity |
| mach | speed / sqrt(gamma × pressure / rho) | dimensionless |

任何非有限值、shape/time 不匹配、非正密度或非正压力均返回 RUN_OUTPUT_INVALID。模型单位没有 SI 标定。网格来自本 Run 配置和初始坐标，不固定为 32×128。

## 熵与 face 几何

标量 history 复用锁定 source observer 和 `_history_row`，每个接受步均保存 stage 0/1/2 的 dotE、deltaE 和累计 E。三个观测状态为 U_n、U_1、U_2；权重为 `[1/6,1/6,2/3]`。

`dotE_c = dy*sum(Pi_c_x)+dx*sum(Pi_c_y)`。

`deltaE_c = dt*sum_s w_s*dotE_c(U_s)`；`E_c(n+1)=E_c(n)+deltaE_c`。

包含所有唯一残差 face 和 x 边界；周期 y seam 保留 slot0、排除重复 slotNy。空间范围与已登记 observer 的 face_audit 一致。结果构造逐项重新核对历史时间、步序、阶段权重、增量和累计总量。

| 科学量 | 记录范围 | 表示 |
| --- | --- | --- |
| 瞬时 Pi | 所选真实快照时刻 | native x/y-face；model entropy / time / face measure |
| 累计空间分配 A_c | 本 Run 完整已计算区间 | sum_steps dt*sum_stages w_s*Pi_c(U_s,face)；model entropy / face measure |
| 累计标量 E_c | 所有真实接受步 | dy*sum(A_x)+dx*sum(A_y)；model entropy |

x-face shape=`[Ny,Nx+1]`，axes=`[y_cell,x_face]`，x 在网格边界、y 在 cell center，face measure=dy。y-face shape=`[Ny,Nx]`，axes=`[y_face,x_cell]`，y 是边界且周期接缝只计一次，face measure=dx。两种 orientation 分开复用 FaceAllocationView；不 reshape 为 cell、不求和为一张图。

软件中的 AllocationObserver 只扩展原 observer 的诊断遍历：在其 `_face_diagnostics` 返回值上累计，与原 scalar observe_stage 使用同一份 face 诊断；snapshot 不参与累计。没有修改科学源、RHS、flux 或 SSP-RK3 算术。三阶段数量须为 3×accepted_steps。空间积分与原 scalar history 在 rtol=1e-10/atol=1e-12 下核对，不通过则不发布成功。

## 宏观指标

所有指标来自本 Run `checkpoint_diagnostics`，源码锁定为 `solver.diagnostics.flagship_cross_modal_case8`。在终态展示，并附时间、单位、定义、detector、窗口、归一化、适用条件与本 Run Evidence。

| 指标 | 定义与条件 |
| --- | --- |
| Shock width | 每行以距初始预期 corrugated front 最近的 p50 为锚，取距 p50 最近的 p10/p90 crossing；要求 p10≤p50≤p90；平均有效行的 x90−x10。阈值基于已登记上/下游压力；单位 model length，网格分辨限制 dx。 |
| Front RMS | 有效行的 p50 前沿位置减去有效行均值，再取 RMS；同一 detector；单位 model length。 |
| HF (front) | front displacement 的 rfft/Ny；k>MODE=4 的能量除以所有 k≥1 能量；分母零时为真实零。全周期 y、无额外倍增系数、dimensionless。 |

源谱对缺失前沿行执行补零；P4 为避免把补零解释为完整前沿谱，当任意行缺失时将 HF 标为不可用。全部行缺失时 width/RMS 也为不可用。其余有效行统计保留有效行计数。绝不据单个指标给出普适稳定性、最优系数或跨协议排名。

## API 与视图上下文

| 接口 | 返回 |
| --- | --- |
| GET /api/v2/runs/{run_id}/result | ScientificRunResult |
| GET /api/v2/runs/{run_id}/evidence | identity、config、effective config、版本/依赖/输出 hash、结论边界 |
| GET /api/v2/runs/{run_id}/snapshot/{snapshot_id}/field?field=... | 六种受控科学字段，保留原 Density 接口 |
| GET /api/v2/runs/{run_id}/snapshot/{snapshot_id}/faces | 所选快照的六个瞬时 native face 数组 |
| GET /api/v2/runs/{run_id}/snapshot/{snapshot_id}/view-context | Run/result/evidence/snapshot/field/time/region + 确定性统计 |

view-context 接受四个可选区域边界 x_min/x_max/y_min/y_max；必须完整、有序、有限且位于本 domain。统计包含矩形边界内的真实 cell center，提供 count/min/max/mean；不插值、不按面积加权。没有选中 center 时返回 null + UNAVAILABLE + reason，禁止把空区域均值写成 0。上下文绑定 result_hash 和 snapshot_sha256，为 P5 预备，不触发 AI 调用。

未知 Run/快照为404；非 COMPLETED、FAILED/CANCELLED 均不能读完整结果，返回409；非法 field/region/query 为400；产物漂移或科学定义校验失败为500。公开接口只接受受控 identity，不返回绝对路径或服务器 traceback。

输出 capability 已开放 fields/entropy/metrics/allocation，实际可用性仍取决于本 Run 产物。输入的 capability revision 沿用 p2.1，因为数值输入协议未变；结果定义由独立 p4.1 postprocess 版本登记。

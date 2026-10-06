# P2 Case 8 真运行与 benchmark

日期：2026-10-03（Asia/Shanghai）。记录为真实 V2 child process 新计算，不使用 V1 终态充当输出。详细有效配置、调用次数、输出 hash、包版本和时间戳在 [p2_solver_acceptance.json](p2_solver_acceptance.json)。

## 条件与时间定义

Windows 11、Intel i7-13620H（10 核/16 逻辑处理器）、HP OMEN 16、物理 RAM 16,858,472,448 bytes；Python 3.12.9、numpy 2.5.3、scipy 1.18.1、matplotlib 3.11.2、PyYAML 6.0.3。详见 [硬件记录](p2_hardware.json)。单个 CFD worker 串行运行，BLAS/OMP/MKL 为 1 线程；同机同时有后端与浏览器回归进程，未声明空载或跨机器性能。

`subprocess_total_wall_seconds` 是 parent 从 execute 调用至 worker 退出及输出 hash 检查完成的实测时间，包含导入、初始化、求解、快照、后处理及 provenance 提交。`solver_seconds` 是 worker 内时间循环（含观察/history/snapshot）。Windows RSS 使用 GetProcessMemoryInfo 的 PeakWorkingSetSize；不是采样估值，也不是系统剩余内存。目录大小包括该 Run 的全部文件，scientific output bytes 单独在 JSON 登记并排除缓存/可变日志。

## 主要新 Run

| 目的 | UUID | 网格 / 步数 / T | 总耗时 (s) |
| --- | --- | --- | ---: |
| B_u 3 步 smoke | `195de019-df3c-4611-bfa9-c80248b878fe` | 128×32 / 3 / .00012552301255230126 | 2.889 |
| D_u 3 步 smoke | `58dde3c3-80e2-4289-a5cc-7315cf9a2cb1` | 128×32 / 3 / .00012552301255230126 | 2.954 |
| Run A（B_u 系数） | `736affcb-1602-46a3-8013-5e9189c360bb` | 64×16 / 478 / .04 | 27.084 |
| Run B（D_u 系数，repeat 1） | `a7d0f5a1-245a-493c-a0d3-e495bfb95d7c` | 64×16 / 478 / .04 | 26.196 |
| D_u fast repeat 2 | `8b49e861-c341-4aeb-b810-0fb41c067a72` | 64×16 / 478 / .04 | 27.701 |
| D_u fast repeat 3 | `c681cf67-5ad5-4920-b901-b88ef631ee87` | 64×16 / 478 / .04 | 26.150 |
| 正式 D_u 完整协议 | `e97042be-e24d-40a7-b5e4-c39f56f84c0e` | 128×32 / 1912 / .08 | 344.938 |

Run A/B 使用 q_aa=3.96、q_at=0/.396，初始数组 hash 和 dt 完全相同；Run A 并非 A_u。实际 dt 来源于初态波速，fast 为 .04/478，paper 为 .08/1912；无硬编码 fast 步数、重试或改 CFL。

## fast 的三次重复

| Repeat | Wall (s) | Peak working set (bytes) | 总目录 (bytes) |
| --- | ---: | ---: | ---: |
| 1 | 26.196091700112447 | 101,572,608 | 1,076,138 |
| 2 | 27.700950200203806 | 101,974,016 | 1,076,137 |
| 3 | 26.150453899987042 | 102,256,640 | 1,076,138 |

中位数 26.196 秒，范围 26.150–27.701 秒；0 失败、三个 UUID、相同初始/终态数组 hash。运行时间、进程 identity、来源文件和日志等元数据不同，不能因此声称全部输出文件逐字节相同。

据此登记 `case8.fast.D_u` 的 benchmark_status=PASSED；未改数值协议时分类 LIVE_FAST_RUN，改参数仍为 CUSTOM_RUN。最终登记后再运行 `beb0c25c-7838-4dde-876d-25f38178793f`，原始终态仍相同，记录在 [p2_promoted_fast.json](p2_promoted_fast.json)。网页执行保持关闭，P3 接入调度后方可启动。

## 正式对照与限制

正式 D_u 与 corrected production 终态逐位相同，所有比较的 case_row 数字和 J2B 全域 stage/history 数字误差均为 0（1912 行）。比较前固定 atol=1e-12、rtol=1e-10，参考 hash 前后相同。front localization 与全轨迹空间分配尚未交付，native-face 快照只代表瞬时量。

fast 是更粗网格下的有效真实计算，不能代替论文精度；本次记录不证明普适稳定性、宏观指标单调性或最优系数。科学结果可追溯与本机 runtime benchmark 是不同结论。

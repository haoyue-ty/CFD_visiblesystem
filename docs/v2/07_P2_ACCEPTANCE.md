# V2-P2 真实 Case 8 求解验收

日期：2026-10-03（Asia/Shanghai）。用户要求“进行 p2”，范围依据 `ShockPath_V2_改造实施计划.md` 的 P2。沿用 `codex/shockpath-v2` 工作区，保留已有 P0/P1 未提交内容。没有提交、推送或改写科研源。

**状态：P2 完成，M2 通过。** P3 网页提交/队列/工作台与 P4 科学结果契约仍待实施。

## 2026-10-03 当前工作区复核

用户再次要求“进行 p2改造”时，工作区已有本页所述 P2 实现。本轮保留已有改造，未重复修改产品代码；新增 [本轮复核记录](p2_recheck.json)，未覆盖下文历史验收与 benchmark。

- 当前 P2 定向测试：**37 passed，1.33s**；43 文件科学依赖锁核查通过，运行环境未变化。
- 两次新的完整 64×16 求解均完成 478 步、T=.04：Run A `62ef250d-c95f-4719-9e11-6ca65886e648`（q_at=0，18.572s），Run B `f49bd79a-d4d1-480d-93da-00890496b8bf`（q_at=.396，17.552s）。初态与步长一致，零通道精确为 0，终态最大绝对差为 0.7445417394433349；实际 RHS/flux 调用次数与参数核查通过。Run B 终态 hash 与此前 benchmark 相同。这两次耗时不是新的三次重复 benchmark。
- 此前正式 Run 早于最终 `software_identity.json` 启动记录补强，因此本轮重新积分正式 D_u：新 Run `784371a2-e1f2-4d7e-becd-35db931253a2`，128×32、1912 步、T=.08，实测进程总耗时 **317.316s**。当前软件及依赖 identity 匹配；终态与参考 **BITWISE**，比较的终态指标及 1912 行全域 stage/history 列误差全部为 0；比较规则与参考 hash 在新积分前记录。
- 新求解后完整科研根 **27,843 文件 / 5,429,811,970 bytes** 的 path/size/mtime_ns/SHA-256 指纹与原始锁定清单完全一致。

本轮没有重跑下文完整后端、浏览器及构建回归；其计数保留为前轮历史结果。网页提交、队列、取消与工作台继续属于 P3。

## 最终验证结果

| 检查 | 实际结果 | 记录 |
| --- | --- | --- |
| 独立 Run A / Run B | 同一初态、64×16、478 步、T=.04；q_at=0 的 E_at 精确为 0，q_at=.396 的 E_at=0.0015385656281803953；终态 max abs 差为 0.7445417394433349 | [主真运行验收](p2_solver_acceptance.json) |
| q_aa 生效、源步进与 RK 权重 | 四系数 3 步 smoke 与不带 observer 的原 SSP-RK3 逐位相同；独立权重重算最大误差 ≤6.94e-18；q_aa 两组同条件轨迹有非零差异，负密度触发原 stage guard | [源等价核查](p2_source_equivalence.json) |
| fast 重复 benchmark | 3 次成功、0 失败、终态 hash 相同；26.196 / 27.701 / 26.150 秒，中位数 **26.196 秒**；峰值工作集 96.87–97.52 MiB，目录约 1.026 MiB | [benchmark](08_P2_BENCHMARK.md)、[硬件](p2_hardware.json) |
| 正式 D_u 新积分 | 1912 步、T=.08；终态 **BITWISE**，max abs/L2 relative error 均 0；全部比较的终态指标与 1912 行全域 stage/history 列误差均 0；实际进程总耗时 344.938 秒 | [比较规则及误差](p2_solver_acceptance.json)、[执行日志](p2_solver_final.log) |
| 完整后端回归 | **1539 passed / 1 skipped，966.43s**；Windows symlink 权限 skip 保留 | [最终 stdout](p2_backend_regression.log) |
| 最终 V2 / contract 定向回归 | **249 passed / 1 skipped，206.20s**，含 P0/P1/P2 及 V1 Case8 合约；最后的 P2 定向 suite 为 37 passed | [日志](p2_final_targeted.log)、[JUnit](p2_final_targeted_results.xml)、[P2 JUnit](p2_targeted_results.xml) |
| 完整浏览器回归 | **225 passed，10.1m**，使用项目既定单 worker / 30s assertion 配置 | [日志](p2_browser_final.log)、[JUnit](p2_browser_results.xml) |
| 最终创建页面 | **5 passed，10.8s**；benchmark 已通过、fast 分类、修改/确认/AI 异常/手机布局；网页启动仍禁用 | [日志](p2_builder_final.log)、[JSON](p2_builder_results.json) |
| 构建 / OpenAPI / types / V1 子集 | PASS；50 paths / 333 schemas；独立 export/type regeneration byte-identical；47 V1 paths / 298 V1 schemas 不变。构建保留既有大 bundle 告警 | [契约](p2_contracts.log)、定向 JUnit |
| 公共资源与生产包 | PASS，2438 public assets；无本地路径、mock 科学 provider 或禁止科学结论进入生产包 | [公共审计](p2_public_audit.log)、[扫描](p2_production_scan.log) |
| 全科研根保护 | **PASS**，27,843 文件 / 5,429,811,970 bytes，path/size/mtime_ns/SHA-256 全部一致；P0 37 文件和 P2 43 文件依赖锁分别复查 | [最终源保护](p2_source_preservation.json) |
| benchmark 登记后的完整 fast 再跑 | 新 Run `beb0c25c-7838-4dde-876d-25f38178793f`，478 步，`LIVE_FAST_RUN`，原始终态 hash 与 benchmark 相同，启动/结束软件 identity 相同 | [最终登记核查](p2_promoted_fast.json) |

全量后端与浏览器回归开始时保留 P1 capability；真运行通过后追加 benchmark 登记与软件来源的启动前/结束 hash 一致性保护。最终 249 项定向回归与 5 项 builder suite 核查当前 P2 DTO/分类/契约；另外完成当前版完整 fast 再积分和四系数源等价核查。没有把不同轮计数相加成一次 suite，也没有重写 P1 历史验收。

初轮误用默认 2 worker / 10s assertion 的浏览器配置，为 **210 passed / 15 timeout failures（6.8m）**，失败集中在旧 V1 Closure/Cylinder/Evidence 视图，同时有 Waitress queue 日志。保留 [首轮日志](p2_browser_first.log) 和 [首轮 JUnit](p2_browser_first_results.xml)。改用项目已登记的完整验收配置（单 worker、30s assertion、retries=0）重跑全部 225 项通过；没有更改 V1 功能代码、删除断言或新增产品 fallback 来消除失败。

源 loader 补强为禁止旧 pyc 参与后重新执行完整真实验收。最终 benchmark 期间后端/浏览器回归也在本机运行，负载条件有记录；早一轮中位数 20.59s 仅为执行过程中观察，当前正式登记为最终一轮 26.196s，不提供 ETA 或跨机器耗时承诺。

## 交付与边界

- `Case8SolverAdapter.validate_config / prepare_run / execute / postprocess` 与 `scripts.run_case8` 独立命令入口；每次生成新的 UUID，不复用历史求解结果。同一 Run 不允许再次启动，重复 caller/worker 有独占 claim。
- worker 只读导入唯一科学根的经哈希登记模块，显式调用 `initial_setup(n, ny, gas)`、有限体积 RHS、带 q_aa/q_at 的目标 flux、源 `source_equivalent_ssprk3_step` 和 `Case8EntropyObserver`。固定初始化字段逐项比对源常量，不修改模块全局量。
- fast/custom 根据实际初态与网格计算波速：`rate=max(|u|/dx+|v|/dy+a/dx+a/dy)`，`raw_dt=CFL/rate`，`steps=ceil(T/raw_dt)`，`dt=T/steps`。paper 标准匹配时再与原 `locked_protocol` 和 J2B protocol lock 比较。无调低 CFL、重试、裁剪或参数替换。
- 保存初态、终态、逐 step/逐 stage 熵历史、有效配置、真实 checkpoint cell 状态和 native x/y-face 瞬时图、确定性终态宏观诊断、日志、来源和输出 SHA-256。
- 全域 face 测度保持原 observer 定义：所有唯一残差面（包括 x 边界），周期 y seam 只计一次；RK 时间权重为 1/6、1/6、2/3。瞬时面图没有冒充轨迹累计空间分配，后者及正式 V2 scientific result DTO 属于 P4。
- smoke 只执行 2–5 步，记录实际时间，状态为 `SMOKE_COMPLETED`，`full_requested_interval_completed=false`；不能被当作完整论文复现。完整计算的状态仅在后处理、物理性和输出来源提交成功后为 `COMPLETED`。
- 启动失败、worker 非正常退出、诊断异常、源漂移和 timeout 都保留失败记录；timeout 在 Windows 下终止该 worker 进程树。P3 的网页队列、取消、重启恢复与 API/SSE 尚未实现。

## 科学源绑定与隔离

P0 静态扫描把 `from solver.fluxes import registry` 记为父包，遗漏了实际加载的 registry 和其依赖。P2 增加 `solver.fluxes.registry` 到启动依赖闭包，得到 43 文件清单 [source_manifest_p2.json](source_manifest_p2.json)，保留原 37 文件 [P0 清单](source_manifest.json)。formal 驱动仅作为参考文件登记，未导入或执行其 CLI。

worker 启动前核对全部依赖 hash；MetaPathFinder 对科学模块 namespace 使用 allowlist，拒绝未知模块，并强制从登记绝对位置加载；执行前后再核对 `module.__file__` 和 SHA-256。SourceLoader 直接编译经哈希核对的 source bytes，避免 `-B` 仍可读取既有 `.pyc` 的问题。mtime/size/hash 的完整源前后审计独立于依赖 identity。

cwd、TEMP/TMP/TMPDIR、MPLCONFIGDIR、用户目录缓存和 XDG cache 指向 Run 内；`-B` / `PYTHONDONTWRITEBYTECODE=1`，BLAS/OMP/MKL 单线程。子进程不继承 API key/token/secret/password 环境变量。Run 与每个写入 target 重新检查 containment，拒绝重定向 Run identity 或子目录的 symlink/junction。

项目 `.venv` 为求解安装 scipy/matplotlib/PyYAML extras，因为源初始化的正常导入闭包需要它们；没有制作替代科学实现或安装绘图环境。未生成科研图；以后绘图仍遵循用户指定的 conda `analysis-env`。P0 package inventory 保留为历史；清单 `--verify` 分开报告科学源 identity 与运行环境变化。

## 真运行与正式对照

主验收 [p2_solver_acceptance.json](p2_solver_acceptance.json) 记录独立 Run ID、起止时间、有效配置、实际 RHS/flux 次数、输出 inventory、硬件/包版本和重复 benchmark。Run A 使用 B_u 系数（3.96/0），Run B 使用 D_u 系数（3.96/0.396），两者共用 64×16、CFL=.05、T=.04 和相同初始条件。Run A 不是 A_u。

正式 D_u 使用 128×32、CFL=.05、T=.08，共 1912 步。比较规则在运行前写入：终态优先逐位相等，数值容差 atol=1e-12、rtol=1e-10；对照 corrected production 的终态/case_row 与 J2B 的全域逐 step/逐 stage 历史。参考文件 hash 在运行前登记并在运行后复查。没有用参考终态作为求解输出，历史文件只在新积分完成后进入比较。

[p2_source_equivalence.json](p2_source_equivalence.json) 单独核查四种 A_u/B_u/C_u/D_u 系数的 3 步 smoke 与原不带 observer 的 `advance_ssprk3_step`；独立重算 stage 权重和累计量，并检查负密度被原 stage guard 拒绝。q_aa 和 q_at 生效均比较相同初态/时间协议的实际轨迹，而非仅检查输入 JSON。

科学比较只证明登记协议及本机环境下的匹配；不建立普适稳定性、最优系数或单调宏观指标结论。全域熵列的对照不意味着已完成 P4 的 front localization / 累计空间分配验收。

## 复查命令

从项目根目录使用 PowerShell 7：

```powershell
./.venv/Scripts/python.exe -B -m pip install -r requirements.lock.txt
./.venv/Scripts/python.exe -B -m pip install --no-deps -e .
./.venv/Scripts/python.exe -B -m scripts.run_case8 --template case8.fast.D_u
./.venv/Scripts/python.exe -B -m scripts.run_case8 --template case8.paper.B_u --smoke-steps 3
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p2_solver
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p2_certify
./.venv/Scripts/python.exe -B -m pytest tests/v2_p2 -q
./.venv/Scripts/python.exe -B -m scripts.verification.v2_source_manifest --runtime --output docs/v2/source_manifest_p2.json --verify
```

`--config` 接受 P1 ValidateExperimentRequest JSON，并在 prepare 与 worker 内再次验证。CLI 不接收输出目录、科研根、命令或任意脚本。实际大数组保留在 Git 忽略的 `runtime/runs/<uuid>/`；提交型验收记录在 docs/v2，不能把摘要当作全量可下载数据。

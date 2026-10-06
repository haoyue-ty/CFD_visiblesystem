# V2-P3 任务管理与运行工作台验收

日期：2026-10-03（Asia/Shanghai）。范围依据用户“进入 p3”及实施计划 P3。沿用 codex/shockpath-v2 工作区，保留 P0/P1/P2 未提交内容；未提交或推送 Git，未改写科研源，未调用付费 AI。

**状态：P3 完成，M3 通过。** 三入口共享配置验证；用户确认后单独提交，后台真实计算可排队、观察、取消并恢复记录。完整科学结果与 Evidence、AI 结果解释、报告仍属于 P4–P6。

## 最终验证

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| 完整后端回归 | 1574 passed / 1 skipped，918.09s；保留 Windows symlink 权限 skip | [日志](p3_backend_regression.log)、[JUnit](p3_backend_results.xml) |
| 完整既有浏览器回归 | 225 passed / 0 failed，627.61s；单 worker、retries=0 | [日志](p3_browser_regression.log)、[JUnit](p3_browser_results.xml) |
| 当前 P2/P3 定向回归 | 69 passed，23.11s；含幂等并发、取消/完成竞态、中断恢复、原子提交容量检查、错误 resource target | [日志](p3_targeted.log)、[JUnit](p3_targeted_results.xml) |
| 真实 HTTP / Waitress | 串行、8 次同 key 重试、排队/运行取消、worker 崩溃、重启、重复 leader、超时、容量上限、history/Density 对照均 PASS | [真实运行记录](p3_live_acceptance.json)、[服务日志](p3_live_server.log) |
| SSE 与普通 API | 四条持续流正常；第五条为 429；普通 API 最大实测耗时 0.0310s；Last-Event-ID 重放终态事件通过 | [真实 HTTP 记录](p3_live_acceptance.json) |
| 当前真实浏览器闭环 | 模板确认/提交、响应丢失后同 key 重试、专业参数排队取消、刷新、SSE 断开后轮询、终态 Density、列表筛选、未知 Run、桌面/手机均 PASS；无 pageerror | [浏览器记录](p3_browser_acceptance.json)、[桌面](p3_workspace_desktop.png)、[手机](p3_workspace_mobile.png) |
| 构建 / OpenAPI / types | PASS；57 paths / 350 schemas；独立导出、类型再生成 byte-identical；既有大 bundle 告警保留 | [构建](p3_build.log)、[契约](p3_contracts.log) |
| V1 契约子集 | 原 47 paths / 298 schemas 与开始 HEAD 中的完整定义相同 | [最终复核](p3_final_checks.json) |
| 公共资源/生产包 | PASS；2438 科学资产，未公开绝对路径、mock 科学 provider 或禁止的科学结论 | [公共审计](p3_public_audit.log)、[生产扫描](p3_production_scan.log) |
| 最终完整源保护 | 27,843 文件 / 5,429,811,970 bytes，path/size/mtime_ns/SHA-256 指纹与原始锁定清单一致；43 文件依赖锁核查通过 | [最终复核](p3_final_checks.json) |
| 新 managed fast 轨迹 | 新 Run 的终态 hash 与此前 P2 benchmark 一致；Density 与该 Run 原始数组逐项一致 | [最终复核](p3_final_checks.json)、[HTTP 对照](p3_live_acceptance.json) |

各 suite 是独立执行，未将不同轮计数相加。完整回归开始后追加了少量边界检查和 UI 收尾；最终 69 项定向回归及当前浏览器/真实运行复核分别登记。未重跑 P1 的真实付费 provider 验收，也未重复 P2 正式规模 benchmark 充当 P3 检查。

## 交付

- RunStore：跨进程事务锁、原子 JSON、持久 index、请求 key/digest、运行记录和事件。Run 与 index 两次提交之间发生中断，重试/dispatcher/重启均修复索引；不重复创建高成本任务。
- RunManager：显式独占 leader；一个数值子进程，复用 P2 prepare/worker/postprocess。factory 与 OpenAPI 导出不启动求解；launcher 启动或复用 daemon，开发 reloader 不产生第二个 consumer。
- 默认资源：1 worker、3 queued、1800s、最多 128×32、6 snapshots、64 MiB/Run。数值范围沿用 capability；失败不改 CFL、参数或离散方法。Waitress 12 threads，SSE 最多四连接。
- 状态：QUEUED → STARTING → RUNNING → POSTPROCESSING → COMPLETED；进度来自真实 steps/time。验证完整区间、输出 hash 和确定性产物后才能发布成功。取消请求与终态由同一锁仲裁。
- 原生 PID + 创建时间识别身份；取消/超时终止实际 Windows 进程树。worker 检查 manager 存活；重启把中断活跃运行记为 WORKER_INTERRUPTED，不续算。已收到的取消在恢复时完成 CANCELLED，排队任务继续保留。
- 八条 catalog 操作：创建、列表、详情、取消、SSE、history、snapshots、snapshot Density。创建 202 不等待求解；同 key 重试返回原 Run，主动再次运行使用新 key/UUID。
- SSE 事件序号随记录原子提交，十秒心跳、三十秒轮换与 Last-Event-ID/after 重放；前端同时四秒状态查询。公开日志仅真实数值进度行，未暴露 traceback 或磁盘浏览能力。
- /workspace 列表与 /runs/:runId 工作台；三入口确认后可启动求解。Density 直接读取本次保守变量 rho，保留真实网格、坐标、时间与 hash；复用 SnapshotViewer，不赋予 V1 冻结身份。

## 真实 Run

- HTTP 串行 Run A：77bfc321-a19b-4e58-b54d-9de2e4835e01；Run B：0ce4a47a-f80e-45ea-a49c-d6b7dc1d912d。两者 64×16、478 步、T=.04；第二个仅在前一个完成提交后启动。q_at=.396 / 0，真实 history 为各 478 行、各六帧，终态密度与对应 NPZ 精确相同。
- 浏览器最新 Run：ea852646-72ce-40fc-b5f3-99329ff0895b。第一次请求已接受但响应被测试主动丢弃；重试使用同一个 key 和 Run，随后刷新/断流后仍完成真实 478 步。
- 取消、崩溃、重启、超时与容量测试的 UUID/PID 身份及结果见真实 HTTP JSON；失败和取消的部分数组未被当作完成结果发布。
- 新运行和科学输出保留在忽略的 runtime；文档摘要不是全量数据替代品。OUTPUT capability 的完整科学字段契约仍为 P4；本阶段开放的是 Run 专属 history 和 Density。

## 首轮问题与修正

首轮真实 HTTP 求解本身完成，但可变 run_control.json 被错误纳入科学 output inventory，随后调度更新造成 hash 漂移。保留 [首轮失败记录](p3_live_first_attempt.json) 和 [首轮日志](p3_live_first_server.log)。修正为排除生命周期记录和原子提交临时文件，数组、配置、诊断及软件/来源 identity 继续核查；新增回归并完整重跑真实 HTTP/浏览器验收通过。容量统计也处理并发原子替换导致的瞬时文件消失。没有删断言、借用 V1 输出或增加产品 fallback。

## 使用与复查

使用 PowerShell 7 启动：

```powershell
pwsh -NoProfile -File ./scripts/serve_backend.ps1
npm run build --prefix frontend
npm run preview --prefix frontend -- --port 4173 --strictPort
```

新建实验 → fast D_u → 验证 → 核对/确认 → 启动求解 → 真实进度/终态 Density；实验工作台可筛选和重新打开 Run。后台默认 127.0.0.1:5000，前端默认代理该地址。

```powershell
./.venv/Scripts/python.exe -B -m pytest tests/v2_p3 tests/v2_p2 -q
./.venv/Scripts/python.exe -B -m scripts.verification.v2_p3_live
node scripts/verification/v2_p3_browser.mjs
```

真实验收脚本要求没有其他活跃 manager，使用独立本地端口并实际创建 CFD；测试结束关闭自己的服务进程，记录保留。生产启动另行使用正常 launcher。下一阶段为 P4：完整 ScientificRunResult、派生场/指标定义、真实多帧与 V2 Evidence。

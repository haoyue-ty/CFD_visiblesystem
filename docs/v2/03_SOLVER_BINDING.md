# V2-P0 Solver 绑定与写入隔离策略

日期：2026-10-02（Asia/Shanghai）。P0 无 worker、无 Solver Adapter、无 CFD 执行入口。现有 Case8Adapter 继续只读回放。

## 1. 软件侧边界

唯一科学源为 [source_manifest.json](source_manifest.json) 中的根和 allowlist。formal CLI 会生成科研输出且冻结配置，禁止直接启动。只复用经核查 flux、初始化、RHS、stage guard、SSP-RK3 observer 和诊断函数；参数化包装层在软件项目内实现，禁止修改科学源全局常量。

新增 `backend/solver_runtime/paths.py`：server 固定使用 `<workspace>/runtime`，run_id 为服务端 canonical UUID，Run 目录为 `runtime/runs/<uuid>`；Path.resolve 后检查 workspace containment 和与 scientific_root disjoint，拒绝链接/目录联接跳出边界。helpers 只解析不 mkdir，没有执行副作用。`runtime/` 已加入 `.gitignore`，不接受用户/AI 提交 runtime 路径。

P2/P3 worker 全部写入此 Run 目录：config、effective_solver_config、status、provenance、events、log、diagnostics、snapshots、derived、ai、report。RunStore 状态/索引使用临时文件+原子 rename。runtime root 和每个实际写入 target 都须复查，防止已有子目录链接；P0 helpers 是基础边界检查，并非完整写文件服务。

## 2. 未来 worker 启动要求

- 由 server 生成 subprocess argv，使用固定 Python、`-B`，不接受 shell 命令字符串；`PYTHONDONTWRITEBYTECODE=1`。
- cwd、TEMP、TMP、TMPDIR、MPLCONFIGDIR、HOME 类库缓存策略均指向本 Run 的 runtime 子目录。不得改变当前 shell 的 HOME/CODEX_HOME。
- 设置明确 module search roots，启动前核对清单；import 后验证实际 `module.__file__`、dependency SHA-256，遇到 drift 停止。
- 排除 formal main()、run_case8_micro() 等未经软件路径封装的入口；禁止调用科研目录默认输出参数。
- 复用初态波速和 stage guards。effective config 必须记录真正传到 flux/setup/stepper 的参数，不能只有用户 JSON。
- 若选定模块链有不可接受的 import 副作用，使用软件目录中的受控镜像，登记原始路径/hash、镜像 hash、差异及原因；不能维护另一套数值方法。
- 缺依赖、源漂移、无效状态直接失败，不自动降低 CFL/改参数重试。

这些启动策略在 P2/P3 实现验收。当前 app factory 和 OpenAPI export 不 import 科学 solver，不启动线程/worker；P0 测试只用临时软件目录和软件 DTO。

## 3. 可执行核查

```powershell
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration capture
./.venv/Scripts/python.exe -B -m scripts.verification.v2_source_manifest --verify
./.venv/Scripts/python.exe -B -m scripts.verification.source_audit --baseline .cache/phase11-final/source-before.json --output docs/v2/source_preservation.json
./.venv/Scripts/python.exe -B -m pytest tests/v2_p0 -q
```

capture 已执行，覆盖 27,843 文件、5,429,811,970 bytes，按 path/size/mtime_ns/SHA-256 捕获包括缓存文件在内的完整科研根。前置完整清单位于忽略目录 `.cache/phase11-final/source-before.json`；摘要和最终对比在 docs/v2 保存，未来每次 solver milestone 需重新 capture，而不是用 P0 摘要代替新运行前置记录。

首次 capture 在基线测试启动后、V2 源审计/任何未来 solver import 之前；本阶段无科学执行，所有核查是读操作。它证明捕获至最终核查之间完整源不变，不倒推未捕获之前的历史状态。依赖锁另行永久保存，不能用全根 fingerprint 代替依赖 identity。

Windows 目录链接越界测试使用平台可用的机制；本机 symlink 权限不可用，单项 skip，不能算通过。另两项 PowerShell 7 directory junction 测试已通过，覆盖 runtime 根和 runs 子目录链接越界；普通路径/重叠/identity 越界检查也通过。P2 真运行后仍须完整源前后核查，P0 通过不保证未来 worker 已实现隔离。

## 4. P2 实现记录（2026-10-03）

以上章节保留 P0 当时的策略与核查范围。P2 已新增独立 Adapter/worker、逐写入 target 检查、UUID 路径禁止链接重定向、受控子进程环境和源文件编译 loader。加载前/后 verify、未知科学模块拒绝、固定源路径和禁写 bytecode 已进入可执行实现。`-B` 不足以禁止读取旧缓存，因此 loader 直接编译 SHA-256 已核查的源码 bytes。

启动清单扩展为 [source_manifest_p2.json](source_manifest_p2.json)，包含 baseline 终态诊断的实际 flux registry 导入闭包，共 43 文件；P0 清单与历史 package inventory 保留。清单校验把源 identity 与运行环境分开报告。正式 CLI 仍未执行，软件 worker 复用已登记源函数。

实际运行与源保护结果见 [P2 验收](07_P2_ACCEPTANCE.md)。P3 Run Manager / API / SSE / 用户取消尚未实现；P2 只有 standalone 同步 Adapter、独占启动和 timeout 进程树清理。

## P3/P4 后续实施记录（2026-10-03）

上述 P2 状态是当时记录。P3 Manager、API、串行调度、SSE、取消和恢复已实现，见 [P3 验收](09_P3_ACCEPTANCE.md)。P4 在软件侧扩展原 entropy observer 的 face 诊断遍历，按 SSP-RK3 原阶段状态累计各通道 face 数据；不会改变源 RHS/flux/积分器，也不会将 snapshot 调用纳入时间累计。`backend/postprocess/allocation.py`、`case8.py` 和结果模型纳入软件包装 hash 清单，科学源依赖仍使用同一 43 文件清单。

新 worker 保存 `derived/cumulative_faces.npz` 及 `scientific_result.json`，在提交 COMPLETED 前验证空间积分/标量累计、字段定义、历史权重和输出 hash。旧 Run 没有累计 face 文件时明确不可用。定义与复查入口见 [P4 科学结果定义](10_P4_SCIENTIFIC_RESULTS.md) 和 [P4 验收](11_P4_ACCEPTANCE.md)。

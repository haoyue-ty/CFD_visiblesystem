# V2-P0 基线与回归报告

开始日期：2026-10-02，验收日期：2026-10-03（Asia/Shanghai）。执行环境为 PowerShell 7 和项目 `.venv`；没有执行 CFD，没有修改 `D:/Paper/passage6` 科学源。测试原始日志保存在本目录。

## 1. Git 基线

| 项目 | 实际记录 |
| --- | --- |
| 开始分支 | codex/github-upload |
| 开始 HEAD | d4abbac4c7cd479ad2e927d5e1902a48df7e26b8 |
| 开始 tracked diff | 空 |
| 开始 untracked | ShockPath_V2_总体技术方案.md、ShockPath_V2_改造实施计划.md |
| 实施分支 | codex/shockpath-v2（从上述 HEAD 创建） |
| V2 前新增回退标签 | V1_PRE_V2_P0_20261002 → d4abbac4c7cd479ad2e927d5e1902a48df7e26b8（保留当前中文 V1） |
| FUNCTIONAL_V1_FREEZE 标签对象 | 21a9add240192a3f6b1c291c80f9c34e60d05b9d；类型 tag |
| FUNCTIONAL_V1_FREEZE 实际提交 | 061cac00e7dc41211a7d347124328b92ac9aff82（`^{}` 解析） |
| 标签实际提交与开始 HEAD | 祖先关系成立，merge-base=061cac00… |

标签之后当前 HEAD 多出三次提交：`9dfc886`（V1 freeze docs）、`8e960bd`（Chinese UI polish）、`d4abbac`（Chinese introduction/guide）。annotated tag 对象不能当作“另一条未合并开发历史”；不能按 Phase12 旧文本 SHA 直接覆盖当前 UI。保留原标签、原分支和上述开始 HEAD，可据此恢复 V1。

## 2. 基线与验证记录

| 检查 | 实际结果 / 日志 |
| --- | --- |
| V1 首次 backend suite | 1355 passed、1 failed，526.34s；[baseline_pytest.log](baseline_pytest.log)；该失败受到本次提前编辑影响，见下节 |
| 原失败单项在开始 HEAD 的完整 Git archive 中执行 | 1 passed，2.93s；[baseline_original_guard.log](baseline_original_guard.log) |
| 历史测试改为 accepted V1 snapshot 后定向验证 | 1 passed，4.79s；[historical_guard.log](historical_guard.log) |
| V1 build（含 vue-tsc） | 通过；[baseline_build.log](baseline_build.log)；已有 bundle >500kB 告警 |
| P0 修改后 build | 通过；[p0_build.log](p0_build.log)，同一既有 bundle 大小告警 |
| OpenAPI / types 基线 | 通过；[baseline_contracts.log](baseline_contracts.log) |
| P0 修改后 OpenAPI / types | 通过；[p0_contracts.log](p0_contracts.log)；47 paths / 298 schemas，独立导出和保存文件 byte-identical |
| public evidence/asset audit | 通过；[baseline_public.log](baseline_public.log)，2438 assets，无公共绝对路径泄漏 |
| production scan | 通过；[baseline_scan.log](baseline_scan.log)，无 mock、科研绝对路径和禁止科学结论进入 bundle |
| 最新 P0 suite | 38 passed、1 skipped，6.62s；[p0_tests.log](p0_tests.log)；symlink 权限 skip，两个 Windows junction 越界测试通过 |
| 完整 backend 修改后回归 | 1387 passed、1 skipped，544.70s；[p0_regression.log](p0_regression.log) |
| 最终 catalog + V1 bootstrap 定向回归 | 58 passed、1 skipped，32.34s；[p0_catalog_tests.log](p0_catalog_tests.log)，包含最新全部 P0 测试 |
| frontend unit + real API + mock browser suite | 220 passed，8.9m；[baseline_frontend.log](baseline_frontend.log) |
| 静态依赖锁复查 | 37 files，PASS；`v2_source_manifest --verify` |
| 完整科研源前后核查 | PASS；27,843 文件、5,429,811,970 bytes，path/size/mtime_ns/hash 全部一致；[source_preservation.json](source_preservation.json) |

OpenAPI SHA-256：`4aaf96c4120805c61948cf590af12a4e21cd98b04d68e2585ca5f97e377626c4`。
生成 TypeScript SHA-256：`1fb6bff5d5075e6818c1f481995ce30dffd98cb2a7fd2d65ea379445811c1631`。

## 3. 首次测试失败的归因和处理

首次 suite 尚未结束时修改了 `.gitignore`。历史测试 `test_closure_integration_does_not_authorize_other_frozen_changes` 读取 live checkout 的旧冻结 slice，本应发现注入的 `backend/models/core.py` 未授权变更，却先发现新增 `runtime/` ignore，因此原断言 regex 不匹配。这是本次执行时序造成的验证干扰，不是既有 V1 缺陷，也不代表 API 行为不兼容。

已在开始 HEAD `d4abbac…` 的完整只读 Git archive 中运行**原未修改测试**，通过。当前测试采用与相邻历史 audit reproduction 一样的 snapshot 策略：固定 accepted V1 `061cac0…`、用真正 repo 的 Git objects 解析历史、只在 snapshot 注入非法改动。它继续要求拒绝 core.py 改动，未扩大历史 freeze allowlist，未更改冻结文档/清单，未删除旧检查。

首次 suite 的 1355 passed 与独立 snapshot 的 1 passed 是分开执行的证据；不能把它们描述成一次完整 clean baseline suite 的 1356 passed。最终完整回归单独报告。

完整回归收集时有 31 个 P0 passing case；末轮新增了 7 个 Windows junction / transport guard / strict JSON case，并对最终版运行全部 P0+bootstrap 定向回归。上表每个计数对应其真实单次运行，不能把合并覆盖数冒充一轮全量测试计数。V1 默认 routes/OpenAPI/types 在最终版仍完全相同。

## 4. 复查命令

```powershell
./.venv/Scripts/python.exe -B -m pytest -q
npm run build --prefix frontend
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration contracts
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration public
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration scan
./.venv/Scripts/python.exe -B -m scripts.verification.v2_source_manifest --verify
$env:PYTHONDONTWRITEBYTECODE='1'
Set-Location frontend
npx playwright test --config playwright.phase11.integration.config.ts
```

Playwright 使用真实 V1 API 和独立 mock 开发 suite，均是回放验收；REAL API 不代表实时求解。Waitress queue-depth 告警如有出现只记录为现有 suite 的观察，不能由此宣称 P3 SSE 并发验收通过。未做 fast benchmark、正式复现、AI 或 V2 UI 验收，这些属于后续阶段。

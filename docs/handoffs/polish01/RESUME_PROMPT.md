# 验收完成记录

本轮剩余工作已完成，`POLISH01_STATUS=PASS`。下方原始接手提示保留为历史上下文，所列失败、未完成步骤和旧报告警告已由最终验收替代，不应再次执行为待办。

- Evidence 隐藏提示已在展示层修复；定向 E2E 及完整 220 项套件均通过。
- 类型检查、构建、合同/公开资产、最终生产扫描、科研源清单与两种分辨率 QA 均通过。
- 最终材料：[POLISH01_ZH_CN_HANDOFF.md](POLISH01_ZH_CN_HANDOFF.md)、[CHECKS.json](CHECKS.json)、[FRONTEND_TEST_RESULTS.json](FRONTEND_TEST_RESULTS.json)、[GIT_AUDIT.json](GIT_AUDIT.json)。
- 最终提交：本验收提交的 `HEAD`，通过 `git rev-parse HEAD` 解析；字面哈希见最终聊天报告。
- `NEXT_STAGE=COMPETITION_VISUAL_SYSTEM_POLISH`；等待用户新指令，未自动启动。

---

# 新窗口交接提示词

你接手 ShockPath Competition Polish 01：全站中文化与中国用户友好化。请在现有未提交修改上继续收尾，不要从头重做，也不要进入下一轮视觉优化。

## 用户偏好与边界

- 仓库：`D:\code_project\CFD_visiblesystem`。Windows 终端默认 PowerShell 7（pwsh）；绘图参考 conda analysis-env；不启用 obra/superpowers skills，不主动派生子代理。
- 分支：`codex/polish01-zh-cn`。
- BASE_COMMIT / 当前 HEAD：`9dfc886b558311fc3a0145fea686a8dc6f3627f7`。
- FUNCTIONAL_V1_FREEZE 祖先：`061cac00e7dc41211a7d347124328b92ac9aff82`，已确认存在。
- 起始 worktree 干净；当前修改全部是本轮 OWNED，没有预先存在或无关修改。尚未暂存、commit 或 push。
- 科研源 `D:\Paper\passage6` 严格只读。禁止运行 CFD、修改数值、补零、插值或造生产科研数据。
- 只改前端展示语言及必要中文排版；不要改 backend enum、API/JSON/schema identity、ID、公式、科学变量、科学文件名、哈希、路由或科学计算逻辑。
- 原始完整需求在 `C:\Users\t\.codex\attachments\fc75d3f9-f3f1-4ecf-83a0-ff198cddce2d\已粘贴的文本.txt`。

## 已完成实现

- `frontend/src/presentation/zh-CN.ts`、`zh-CN.json`、`typography.css`：1353 条精确映射；集中 availability/fact/verification/origin/tab/experiment/evidence-section 词汇；七幕中文叙事。
- Entry、Home、Explore S1–S7、Lab、六种实验、机制、Cross-flow、Evidence 三分区与详情、标题/metadata、无障碍、图表/tooltip/空状态/错误状态已中文化。
- URL、canonical value 与选择器提交值保持原样。必要科学英语（品牌、Case 8、Mach、配置/变量/公式、方法/ID/文件名/哈希）保留。
- 科学表述已复核：Strict 1D 触发可存在但切向接收/输出为零；正熵产不代表所有模态统一增强阻尼；跨流动只作描述性比较；真实缺口仍明确显示。
- `chartCopy` 只改展示字段，跳过数据/坐标/维度/source 数组；三项新单测验证身份、精度/零值、数组不变及科学叙事边界。`zh` 只查词典自有属性，未知特殊名字 constructor/__proto__ 不误映射。
- 中文字体使用系统栈；窄屏导航/表格换行、频谱图局部滚动、图表说明间距已修复。没有重做主题、布局或动画。
- 旧 E2E 只更新展示文案/selector，科学数值/ID/API 状态断言保持。

## 已实际通过

- Backend 全量 pytest：1356 passed，558.67 秒。之后未修改 backend，不必无理由重复耗时验证。
- Frontend unit：18 passed（最新完整运行的 unit 项目也通过）。
- 最新 `npm run build`：vue-tsc 与生产构建通过。当前 bundle `index-GupM5Bug.js`，CSS `index-Bg_h4KTQ.css`；既有 >500KB chunk 警告不影响构建。
- Contract：OpenAPI 保存/独立导出/运行时字节一致，47 paths / 298 schemas；生成类型字节一致。`docs/handoffs/polish01/CONTRACT_AUDIT.json`。
- Production scan：MOCK provider/payload 0、科研路径暴露 0、正向夸大结论 0。`PRODUCTION_SCAN.json`。
- Public asset audit：2438 来源资产，公开绝对 locator 0，download routes 0。`PUBLIC_ASSET_AUDIT.json`。
- 科研源前后完整路径/size/mtime/SHA 清单一致，27843 files；fingerprint=`8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`。`SOURCE_PRESERVATION.json`。
- 真实 backend + 生产 preview：1920×1080 和 390×844 各 43 组路由/标签页，普通英文句段残留 0、根页面横向溢出 0、pageerror 0。93 张截图、86 份正文、2 份 browser-audit 已保存进 docs。
- `git diff --check` 通过。

## 未完成与已知失败

1. 最新全量前端 220 项（18 unit + 202 E2E）没有跑完。用户要求先停，在第 99 项后中止；其中第 86 项失败。不能标记 FRONTEND_E2E=PASS 或 POLISH01_STATUS=PASS。
2. 先处理 `frontend/tests/evidence-real-api.spec.ts:128`，测试名 `public text strips unsafe locators; all links are application routes and never downloads`。它期待 `[来源路径已隐藏]`，实际未出现该中文提示。失败材料：`frontend/test-results/phase11-final/evidence-real-api-public-t-a0c3f--routes-and-never-downloads-phase5-10-real-api/error-context.md`。
   `frontend/src/data/evidence.ts` 的 safeText 仍产生英文 `[source locator withheld]`；当该 marker 嵌在更长字符串时，精确 zh 查找可能不命中。请确认失败实际内容，再以展示层修复保持 locator 清除逻辑和无路径泄漏断言，不要放宽安全断言。未在旧窗口修复。
3. `.cache/phase11/playwright.json`/xml 是此前 78 项定向运行（71 pass / 7 fail）的旧报告。旧问题多数后来已修，不能用该报告判断最新结果，也不能复制成最终报告。完整运行被中止尚未覆盖旧报告。
4. `CHECKS.json` 尚未生成；`POLISH01_ZH_CN_HANDOFF.md` 是草稿，已标记用户停止/未验收。应据最终验证结果更新。
5. 尚未完成最终 git 审计/暂存/commit/clean 检查；未推送。
6. 最终全量测试后再做一次科研源清单比较及最终 production scan，确保最终源码/构建与收据一致。

## 接手建议顺序

先检查 git status / branch / log 并读需求和交接。修已知 Evidence 提示失败，先跑定向测试；通过后构建并完整跑已有前端 220 项套件，让它结束，不要因新发现的可并行整理事项反复中止重启。

```powershell
# frontend 目录
npm run build
npx playwright test --config=playwright.phase11.integration.config.ts tests/evidence-real-api.spec.ts --project=phase5-10-real-api --grep 'public text strips'
npx playwright test --config=playwright.phase11.integration.config.ts

# 仓库根目录
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -B -m scripts.verification.phase11_integration scan
$env:PYTHONPATH=(Get-Location).Path
.\.venv\Scripts\python.exe -B .cache/polish01-source-verify.py
```

完整前端配置自动启动 backend 5110 / production 4410 / mock development 4510，worker=1、retries=0。本窗口所有启动的服务已停止。系统原来有 5000 端口进程（此前 PID 2636）不是本轮创建的，不要随意终止；重新检查端口归属。

如修改可见 UI，请按需刷新截图。可复用 `scripts/verification/polish01_browser.mjs`：`POLISH_UI_URL`、`POLISH_QA_WIDTH=1920/390`、`POLISH_QA_FOCUS=1`；输出在 `.cache/polish01/{1920,390,focus}`。浏览器审计现在会在 pageerror、根溢出、普通英文残留时失败。大数据页面偶尔可能 networkidle 超时，应确认服务和负载再重跑，不得忽略真实错误。

验收后更新 docs 的最终字段、CHECKS.json 和必要截图，再逐文件审计，只暂存本轮 OWNED 修改。禁止盲目 git add -A。临时处理脚本和清单已移到忽略目录 `.cache/polish01/tools`，不提交；其他 .cache/test-results/dist 也不提交。

提交完成后输出用户原需求第 52 节的全部字段、实际 FINAL_COMMIT、三份短清单和 NEXT_STAGE=COMPETITION_VISUAL_SYSTEM_POLISH；工作区必须干净。只宣布下一阶段，不自动开始。不创建新工作树丢失现有未提交修改，不自动回滚。

入口材料：`docs/handoffs/polish01/POLISH01_ZH_CN_HANDOFF.md`、`LANGUAGE_AUDIT.md`、`AMBIGUOUS_LANGUAGE_ITEMS.md`（当前 0）、`SCREENSHOT_AUDIT.md`、截图目录及四份验证 JSON。

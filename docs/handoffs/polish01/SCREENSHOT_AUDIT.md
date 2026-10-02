# 截图与浏览器审计

最终验收已使用 Evidence 隐藏提示修复后的生产构建刷新全部截图和正文，构建资产哈希见 [CHECKS.json](CHECKS.json)。

使用真实 backend（5110）与生产 preview（4410）。每种分辨率覆盖 43 组路由及标签页，共 86 张逐页截图；另有 7 张图表、tooltip 和证据定义重点截图。全部页面无运行时错误、无根页面横向溢出，普通英文句段扫描为 0。

正文快照（同名 .txt）和 browser-audit.json 同时保留。提交的正文快照仅规范行尾空白；原始正文留在忽略缓存中，所有文案和科学数值保持。英文动作标签经语言策略分类：品牌、科学变量、配置、字段、文件与证据标识保留。`overflowElements` 可记录局部滚动图表内部的宽画布，根页面 scrollWidth 与 viewport 宽度仍相等，不表示页面溢出。

| 路由 / 选择 | 1920×1080 | 390×844 | 根宽度 / 文案扫描 |
| --- | --- | --- | --- |
| `/` | [截图](screenshots/1920/00.png) | [截图](screenshots/390/00.png) | PASS / 0 |
| `/home` | [截图](screenshots/1920/01.png) | [截图](screenshots/390/01.png) | PASS / 0 |
| `/explore?scene=1` | [截图](screenshots/1920/02.png) | [截图](screenshots/390/02.png) | PASS / 0 |
| `/explore?scene=2` | [截图](screenshots/1920/03.png) | [截图](screenshots/390/03.png) | PASS / 0 |
| `/explore?scene=3` | [截图](screenshots/1920/04.png) | [截图](screenshots/390/04.png) | PASS / 0 |
| `/explore?scene=4` | [截图](screenshots/1920/05.png) | [截图](screenshots/390/05.png) | PASS / 0 |
| `/explore?scene=5` | [截图](screenshots/1920/06.png) | [截图](screenshots/390/06.png) | PASS / 0 |
| `/explore?scene=6` | [截图](screenshots/1920/07.png) | [截图](screenshots/390/07.png) | PASS / 0 |
| `/explore?scene=7` | [截图](screenshots/1920/08.png) | [截图](screenshots/390/08.png) | PASS / 0 |
| `/lab` | [截图](screenshots/1920/09.png) | [截图](screenshots/390/09.png) | PASS / 0 |
| `/lab/mechanism` | [截图](screenshots/1920/10.png) | [截图](screenshots/390/10.png) | PASS / 0 |
| `/lab/experiments/case8` | [截图](screenshots/1920/11.png) | [截图](screenshots/390/11.png) | PASS / 0 |
| `/lab/experiments/gate` | [截图](screenshots/1920/12.png) | [截图](screenshots/390/12.png) | PASS / 0 |
| `/lab/experiments/entropy-closure` | [截图](screenshots/1920/13.png) | [截图](screenshots/390/13.png) | PASS / 0 |
| `/lab/experiments/spectrum` | [截图](screenshots/1920/14.png) | [截图](screenshots/390/14.png) | PASS / 0 |
| `/lab/experiments/modal-validation` | [截图](screenshots/1920/15.png) | [截图](screenshots/390/15.png) | PASS / 0 |
| `/lab/experiments/cylinder` | [截图](screenshots/1920/16.png) | [截图](screenshots/390/16.png) | PASS / 0 |
| `/cross-flow` | [截图](screenshots/1920/17.png) | [截图](screenshots/390/17.png) | PASS / 0 |
| `/evidence` | [截图](screenshots/1920/18.png) | [截图](screenshots/390/18.png) | PASS / 0 |
| `/evidence?section=GAPS` | [截图](screenshots/1920/19.png) | [截图](screenshots/390/19.png) | PASS / 0 |
| `/evidence?section=HISTORY` | [截图](screenshots/1920/20.png) | [截图](screenshots/390/20.png) | PASS / 0 |
| `/evidence/ev.case8.D_u.allocation` | [截图](screenshots/1920/21.png) | [截图](screenshots/390/21.png) | PASS / 0 |
| `/lab/experiments/case8?config=D_u&tab=flow` | [截图](screenshots/1920/22.png) | [截图](screenshots/390/22.png) | PASS / 0 |
| `/lab/experiments/case8?config=D_u&tab=entropy` | [截图](screenshots/1920/23.png) | [截图](screenshots/390/23.png) | PASS / 0 |
| `/lab/experiments/case8?config=D_u&tab=allocation` | [截图](screenshots/1920/24.png) | [截图](screenshots/390/24.png) | PASS / 0 |
| `/lab/experiments/case8?config=D_u&tab=metrics` | [截图](screenshots/1920/25.png) | [截图](screenshots/390/25.png) | PASS / 0 |
| `/lab/experiments/case8?config=D_u&tab=evidence` | [截图](screenshots/1920/26.png) | [截图](screenshots/390/26.png) | PASS / 0 |
| `/lab/experiments/cylinder?config=D_u&tab=flow` | [截图](screenshots/1920/27.png) | [截图](screenshots/390/27.png) | PASS / 0 |
| `/lab/experiments/cylinder?config=D_u&tab=entropy` | [截图](screenshots/1920/28.png) | [截图](screenshots/390/28.png) | PASS / 0 |
| `/lab/experiments/cylinder?config=D_u&tab=sectors` | [截图](screenshots/1920/29.png) | [截图](screenshots/390/29.png) | PASS / 0 |
| `/lab/experiments/cylinder?config=D_u&tab=metrics` | [截图](screenshots/1920/30.png) | [截图](screenshots/390/30.png) | PASS / 0 |
| `/lab/experiments/cylinder?config=D_u&tab=evidence` | [截图](screenshots/1920/31.png) | [截图](screenshots/390/31.png) | PASS / 0 |
| `/lab/experiments/entropy-closure?run=D_u-cfl-0.05&tab=semi-discrete` | [截图](screenshots/1920/32.png) | [截图](screenshots/390/32.png) | PASS / 0 |
| `/lab/experiments/entropy-closure?run=D_u-cfl-0.05&tab=fully-discrete` | [截图](screenshots/1920/33.png) | [截图](screenshots/390/33.png) | PASS / 0 |
| `/lab/experiments/entropy-closure?run=D_u-cfl-0.05&tab=evidence` | [截图](screenshots/1920/34.png) | [截图](screenshots/390/34.png) | PASS / 0 |
| `/lab/mechanism?source_scene=3` | [截图](screenshots/1920/35.png) | [截图](screenshots/390/35.png) | PASS / 0 |
| `/lab/experiments/spectrum?spectral_q=spectrum.q-0.396&spectral_mode=8` | [截图](screenshots/1920/36.png) | [截图](screenshots/390/36.png) | PASS / 0 |
| `/lab/experiments/modal-validation?spectral_q=spectrum.q-0.396&spectral_mode=8&spectral_run=modal-validation.m08_q0p396_eps1e-04` | [截图](screenshots/1920/37.png) | [截图](screenshots/390/37.png) | PASS / 0 |
| `/evidence/ev.mechanism.theory-implementation` | [截图](screenshots/1920/38.png) | [截图](screenshots/390/38.png) | PASS / 0 |
| `/evidence/evidence.spectral.spectrum.q-0.396.mode-08` | [截图](screenshots/1920/39.png) | [截图](screenshots/390/39.png) | PASS / 0 |
| `/evidence/evidence.spectral.spectrum.q-0.396.mode-08.right.rank-00.complex_vector.stored_vector` | [截图](screenshots/1920/40.png) | [截图](screenshots/390/40.png) | PASS / 0 |
| `/evidence/evidence.spectral.modal-validation.m01_q0p000_eps1e-04.history` | [截图](screenshots/1920/41.png) | [截图](screenshots/390/41.png) | PASS / 0 |
| `/evidence/ev.missing.cylinder-cumulative2d` | [截图](screenshots/1920/42.png) | [截图](screenshots/390/42.png) | PASS / 0 |

重点检查：

- [Case 8 熵耗散 tooltip](screenshots/focus/entropy-chart-tooltip.png)：中文步数/时间/图例，数值保持完整。
- [增长验证](screenshots/focus/growth-validation-canvas.png)：模态运行按钮中文化，未保存线性历史说明与图表副标题不重叠。
- [特征模态](screenshots/focus/eigenmode-canvas.png)：复数表示、投影、说明与图例保持科学身份，中文标题留出说明间距。
- [圆柱绕流标量历史](screenshots/focus/cylinder-entropy-chart.png)与[角向扇区](screenshots/focus/angular-sector-chart.png)：单位/变量原样，中文标签清楚。
- [证据科学定义](screenshots/focus/evidence-definitions.png)：来源、定义、时间/空间规则、度量和科学限制可核查。

修复记录：独立机理页返回文字漏译；模态运行标签 mode → 模态；谱证据边界/机制来源说明补齐；窄屏长精确数值换行；长图表说明与副标题分开；频谱 grid 子项允许收缩，使 736 像素画布在局部容器滚动。未隐藏、重采样或缩短科学数据。

人工复核覆盖 Entry/Home、七幕叙事、Lab、机制、实验与证据的主要呈现；重点检查长标题、图例、状态标签、表格、tooltip 与窄屏。布局未作视觉体系重构。

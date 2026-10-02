# 语言分类与维护规则

源代码审计范围为 `frontend/src` 的 Vue/TypeScript/JSON 和入口 HTML；浏览器审计覆盖 43 组真实路由与标签页，在 1920×1080、390×844 下分别获取截图和全部可见正文。集中词典的英文 key 是原始文案查找键，不作为中文界面直接呈现。

| 分类 | 本轮处理 | 典型内容 |
| --- | --- | --- |
| TRANSLATE | 普通展示文案统一中文 | 导航、按钮、加载、缺失、错误、图表标题/轴名/图例、证据字段、七幕叙事、科学边界 |
| KEEP_ENGLISH | 保留科学/技术身份的原始值 | ShockPath、Case 8、Mach、A_u/B_u/C_u/D_u、q_aa/q_at/E_at、CFL/RK3/RHS/PSD/EC/HF/RMS、Re(λ)、ε、Δx、Pi_at/Π_at、Fourier、SHA-256、ETag、CFD/API/JSON/HTTP |
| KEEP_ENGLISH | 稳定命名和数据选择身份继续可读 | cross_mode_ec_unified_v1、experiment/result/evidence/asset ID、Acoustic/Pressure/Ungated 配置 ID、field ID（如 density/pressure/front/radial_interior_pi_at）、RIGHT/LEFT、ABS_PROJECTED_COEFFICIENT、科学文件名、哈希、revision |
| BILINGUAL_FIRST_USE | 核心机制入口首次中英对照，后续中文 | 跨模态（cross-mode）；保留已有 Fourier 表达 |
| INTERNAL_ONLY | 不改 canonical identity，显示另行映射 | AVAILABLE/MISSING/UNSUPPORTED、CURRENT/GAPS/HISTORY、KNOWN/UNKNOWN、verification enum、route name/query/JSON key、class/testid、源码注释、开发 MOCK fixture、诊断代码 |
| AMBIGUOUS | 0 项；无强行翻译或等待决定的项 | 已确认边界见下一表 |

| 语义边界 | 采用的中文表达 | 依据 |
| --- | --- | --- |
| face integrated | 面上时间积分 | 原生 x/y 法向面资产已含时间积分，未包含空间面积分；不额外乘空间或时间度量 |
| cell integrated | 单元积分 | 已保存 Gate 单元资产含时间和空间度量，保持现有求和规则 |
| spectral abscissa | 谱横坐标；工作区“横向模态频谱” | 显示已保存的 Fourier 模态与 Re(λ)，不改写为时间 FFT 或空间流场 |
| Strict 1D | 严格一维，触发可存在，切向接收与输出为零 | 保留机制和科学限制；禁止解释为门控不激活 |
| source drift=false | 记录时源码与当前源码一致 | 原始 false 不被误译为发生漂移；未知仍显示未知及理由 |
| comparison policy | 仅作描述性比较；不进行统一排名 | DESCRIPTIVE_ONLY/NO_UNIFIED_RANKING 的内部值原样保留 |
| UNKNOWN/MISSING/UNSUPPORTED/ERROR | 未知/缺失/不支持/加载失败 | 科学缺口与软件网络错误分开；已记录的 0 和 false 不按缺失处理 |

词典只进行精确展示映射；有限动态句型仅处理 Case 8 配置说明、机理页返回幕号和模态按钮标签。数值、单位符号、ID、公式及未登记的值原样透传。图表数组和数据源不经过文案转换。后续新增后端文案应在有科学上下文的前提下补充映射，不能通过翻译 canonical schema 或任意单词替换实现。

普通英文残留启发式扫描结果为 0；同时人工审查 `englishActions`，保留项均为上述科学身份或含科学身份的中文动作。截图检查覆盖中文导航、七幕长标题、状态 chip、表格、图表图例/说明、熵耗散 tooltip、证据返回路径与窄屏布局。扫描和人工复核结果用于本轮冻结内容，不宣称自动识别任意未来英文文案。

你的思路总体是对的，但我建议改掉一个关键点：**不要“前端全部设计完成 → 再开始后端”**。ShockPath 是一个高度依赖真实 CFD 数据、实验配置和分析接口的项目，如果前端先完全定死，后面很容易因为 `Pi_at.npy`、entropy trajectory、spectrum、eigenmode 等数据结构和接口能力不匹配而大改。

更适合你的方式是：

> **项目边界冻结 → 数据资产审计 → PRD → 用户流程/信息架构 → 数据契约/API → 低保真页面 → 做一个端到端纵向切片 → 再全面展开前后端 → 最后比赛包装。**

我建议你严格按下面这个顺序开发。

1. **先做“项目冻结”，不要马上画页面。**
   第一件事是明确 V1 到底做什么、不做什么。你现在的 V1 可以冻结成 7 个模块：Mechanism、Experiment、Entropy、Allocation、Spectrum、Cross-flow、Reproducibility。此时还要冻结比赛演示的核心故事线：`q_at 参数 → pathway 激活 → E_at → 空间分配 → Fourier 响应 → Case8/Cylinder 不同宏观结果`。输出一个很短的 `PROJECT_SCOPE.md`，明确 P0/P1/P2 功能。这样之后不会做到一半又不断加功能。
2. **第二步不是 PRD，而是“本地科研资产审计”。**
   这是你的项目和普通 Web 项目最大的区别。先让 Codex 扫描 `D:\Paper\passage6`，不要修改任何数据，只建立资产地图：哪个目录里有 Case8、Cylinder、Gate ablation、entropy closure、Fourier spectrum、eigenmode、Fig13 24 runs；每个实验有哪些 `csv/npy/json/npz`；哪些可以直接驱动前端，哪些只有论文图而没有原始数据；哪些计算适合 Replay，哪些适合 Live Demo。最后形成 `DATA_ASSET_INVENTORY.md`。
   **这一阶段非常重要，因为 PRD 应该建立在“你真实拥有什么数据”之上，而不是想象系统应该有什么。**
3. **第三步正式写 PRD。**
   这时 PRD 才会很准确。PRD 需要明确每个页面解决什么问题、用户能进行什么操作、输入是什么、输出是什么、读取哪个真实实验、什么时候调用 Replay、什么时候调用 Live Solver。例如 Allocation 页面不是简单写“展示热图”，而应该明确：用户切换 Acoustic / Pressure / Ungated → 读取对应 `Pi_at.npy` → 使用同一个 shock window → 显示热图、累计曲线、inside/outside fraction。你的论文已经明确区分 pathway budget、spatial allocation 与 macroscopic consequence，这正适合作为整个产品的信息架构。    JCP初稿_全图插入_带正式图注_20260930_QA
4. **第四步做用户流程和信息架构，而不是马上做高保真 UI。**
   先画整个产品的页面关系，例如：
   `Home → Mechanism → Experiment → Entropy/Allocation → Spectrum → Cross-flow → Reproducibility`。
   同时设计两种入口：`Explore Mode` 给评委快速理解，`Lab Mode` 给技术演示。再确定每一个页面的主操作。比如 Spectrum 页面主操作只能有几个：选择 `q_at`、选择 Fourier mode、切换 eigenmode、查看 RK3/CFD validation。避免一个页面出现十几个按钮。
5. **第五步必须先定义“数据契约 + API 契约”。**
   这一步应该发生在精细设计 UI 之前。比如统一实验数据格式：
   `metadata.json / config.json / metrics.json / entropy.csv / allocation.npz / spectrum.csv / state.npz`。
   然后规定后端接口，例如 `/api/cases`、`/api/experiments/{id}`、`/api/entropy/{id}`、`/api/allocation/{id}`、`/api/spectrum/{id}`、`/api/verify/{id}`。
   前端从此不关心你本地数据原来散落在哪，它只认统一接口。这样以后你改实验目录，不用改 UI。
6. **第六步做低保真线框图。**
   这时候你才真正开始“设计前端需要什么内容”。不要先追求漂亮，只确定布局。每一页先问三个问题：用户第一眼必须看到什么？用户能操作什么？操作后什么东西发生变化？例如 Entropy 页可以固定成：左侧 CFD field；右上三通道 ledger；右中 cumulative curve；底部时间轴；右下 closure verification。布局定下来之后再做视觉。
7. **第七步做一个完整的“纵向切片”，这是整个开发流程最重要的节点。**
   不要同时开发七个页面。先只做一个完整 Case8 流程：
   `真实 Case8 数据 → Python loader → FastAPI → 前端 → q_at 切换 → E_at 曲线 → Pi_at allocation → metrics`。
   哪怕界面很丑，也要先把这一条跑通。比如用户选择 `B_u / D_u` 后，系统能够真实返回对应 entropy budget，并显示 Case8 的 front RMS、HF、shock width。只有这一条端到端跑通，说明你的架构是成立的。
   **这个节点以前，不建议花大量时间做动画和精美 UI。**
8. **第八步才建立正式视觉系统和高保真 UI。**
   纵向切片成立以后，统一设计：颜色、字号、卡片、图例、坐标轴、按钮、状态颜色、Tooltip、公式样式。可以直接继承你论文现在的 SCI 风格：白底、浅灰、浅青、蓝、浅粉、珊瑚色，但 Web 可以比论文稍微更有动态感。此时再把 Mechanism Explorer 做漂亮，把 Fig.1 从静态图升级成真正的交互机制图。
9. **第九步进入“前后端并行开发”，而不是前端做完再做后端。**
   到这里接口已经冻结，所以可以并行：前端做 Mechanism、Entropy、Allocation、Spectrum、Cross-flow；后端做 data adapter、analysis service、replay engine、live solver、verification。后端每新增一个稳定接口，前端马上接入。这个阶段最好遵循“一个模块一个模块验收”，不要七个页面一起半成品。
10. **第十步补 Live Solver，但不要让它阻塞主系统。**
    大型生产实验全部 Replay。Live Solver 只承担“证明这是真的 CFD 系统”的任务，例如运行 64×16 或 128×32 小算例。即使 Live Solver 临时出问题，正式演示仍然可以使用冻结真实数据。换句话说，`Replay 是生产功能，Live 是增强功能`，不要反过来。
11. **第十一步做 Reproducibility Center。**
    在基础功能稳定后，把你的 method hash、config、FREEZE manifest、CSV/NPY evidence、entropy closure 放进系统。这会让 ShockPath 从“漂亮 CFD 网页”变成“科研软件”。尤其你的 entropy observer 有与实际有限体积 RHS 达到浮点精度闭合的独立验证，这非常值得产品化展示。    JCP初稿_全图插入_带正式图注_20260930_QA
12. **最后才做比赛模式、视频和 PPT。**
    单独增加一个 `Demo Mode`，让系统按固定路线演示：Mechanism → Same budget / different allocation → Spectrum → Case8/Cylinder → Reproducibility。比赛现场不能让评委自己摸索系统。Demo Mode 最好 3–4 分钟能完整走完核心故事，然后再允许自由探索。

所以，你原本的：

> 需求文档 → 了解前端内容 → 页面设计 → 后端 → 联动

我建议升级成：

> **范围冻结 → 数据资产审计 → PRD → 用户流程 → 数据/API 契约 → 低保真 UI → Case8 纵向切片 → 高保真设计 → 前后端并行扩展 → Live Solver → 可复现中心 → Demo/比赛包装**

其中最重要的是两点：

**第一，不要在数据资产审计以前写得过细的 PRD。**

**第二，不要等整个前端完成以后才开始后端。先把 Case8 做成一个端到端纵向切片。**

如果按文件来管理，我建议你的开发文档最终形成这样的顺序：

```
docs/
├── 00_PROJECT_SCOPE.md
├── 01_DATA_ASSET_INVENTORY.md
├── 02_PRD.md
├── 03_USER_FLOW_AND_IA.md
├── 04_DATA_SCHEMA.md
├── 05_API_CONTRACT.md
├── 06_UI_WIREFRAMES.md
├── 07_DESIGN_SYSTEM.md
├── 08_MVP_ACCEPTANCE.md
├── 09_TEST_PLAN.md
└── 10_COMPETITION_DEMO_SCRIPT.md
```

**你现在最应该做的第一个实际动作就是 `00_PROJECT_SCOPE.md + 01_DATA_ASSET_INVENTORY.md`。** 特别是后者，我建议直接让 Codex 扫描你整个 `D:\Paper\passage6`，只读分析，建立“论文每个模块 → 本地真实数据 → 可实现前端功能”的映射。做完这一步，再写 PRD，会比直接凭想象写需求文档稳很多。
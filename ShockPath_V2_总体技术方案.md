# ShockPath V2 总体技术方案
## 交互式 CFD 求解、科学可视化与 AI 分析平台

**版本**：V2.0 总方案  
**定位**：基于现有 ShockPath V1 增量升级，不推倒重做  
**项目根目录**：`D:\code_project\CFD_visiblesystem`  
**科学源根目录**：`D:\Paper\passage6`（严格只读）  
**核心方法**：`cross_mode_ec_unified_v1`  
**V1 状态**：`FUNCTIONAL_V1_FREEZE=YES`  
**V2 核心目标**：把 ShockPath 从“论文结果可视化网站”升级为“嵌入论文数值方法的交互式 CFD 求解与 AI 科学分析平台”。

---

# 1. 项目重新定位

ShockPath V2 不再以“展示已有 CFD 结果”为核心，而是形成完整的人机交互闭环：

```text
用户定义实验
    ↓
统一实验配置
    ↓
真实 CFD 求解
    ↓
确定性科学后处理
    ↓
交互式可视化
    ↓
AI 自动结果解释
    ↓
AI 科研助手持续问答
    ↓
自动生成实验报告
```

最终产品定义：

> **ShockPath 是一个面向多维可压缩流动的交互式 CFD 数值实验与 AI 科学分析平台。用户可以通过模板、专业参数或自然语言定义实验，系统调用嵌入 cross-mode 熵稳定耗散路径方法的真实有限体积求解器完成计算，再对流场、熵耗散路径、空间分配、模态/宏观指标进行可视化与分析，并由 AI 基于真实求解结果自动解释和生成实验报告。**

---

# 2. V1 与 V2 的关系

不重新建项目，不复制第二套前后端。

V1 保留：

```text
Explore
Lab
Evidence
Scientific Adapter
Canonical Scientific Models
Provenance / Reproducibility
已有论文冻结结果
Vue 3 + TypeScript
Flask + Python
ECharts / Canvas
```

V2 新增：

```text
Experiment Builder
Run Manager
Solver Adapter
Live Run Workspace
Scientific Result Workspace
AI Experiment Parser
AI Result Interpreter
AI Scientific Assistant
Automatic Report Generator
```

总体关系：

```text
ShockPath V1
  ├─ 引导探索
  ├─ 冻结结果
  ├─ 证据中心
  └─ 科学数据适配

        +

ShockPath V2
  ├─ 用户实验输入
  ├─ 实时求解
  ├─ 新实验结果
  ├─ AI 解释
  ├─ AI 助手
  └─ 自动报告
```

---

# 3. 核心设计原则

## 3.1 一个求解器，三个输入入口

三个入口最终必须统一生成同一个 `ExperimentConfig`：

```text
模板模式 ───────┐
专业模式 ───────┼──→ ExperimentConfig ─→ Solver
自然语言模式 ───┘
```

禁止维护三套求解逻辑。

---

## 3.2 Solver 负责计算，AI 不生成 CFD 数值

必须长期保持：

```text
Solver       → 计算
Postprocess  → 测量
Visualization→ 展示
AI           → 解释
Evidence     → 证明
```

AI 不得：

- 伪造 CFD 数值；
- 猜测缺失指标；
- 代替求解器生成流场；
- 用语言模型结果覆盖真实数值结果。

---

## 3.3 科学源继续严格只读

```text
D:\Paper\passage6
```

永久保持：

```text
READ ONLY
```

V2 新运行输出写入独立 runtime 目录，不写回论文源。

---

# 4. 三种实验输入模式

# 4.1 模板模式

面向：

- 比赛评委；
- 普通用户；
- 第一次使用 ShockPath 的用户。

目标：

> 3～4 次点击即可开始真实 CFD 求解。

示例：

```text
Case 8
→ D_u
→ 普通配置
→ 开始求解
```

页面建议：

```text
快速创建实验

流动问题
[ Case 8 ]

标准配置
[ D_u ]

计算模式
● 普通配置
○ 论文配置

[ 开始求解 ]
```

模板自动填充：

```text
Case
Mach
Grid
CFL
T
q_aa
q_at
Gate
Reconstruction
```

用户无需理解所有参数。

---

# 4.2 专业模式

面向：

- CFD 用户；
- 科研人员；
- 希望进行参数干预的用户。

允许在当前 solver 真正支持范围内输入：

```text
Mach
Nx
Ny
CFL
T
q_aa
q_at
Gate
Reconstruction
ε
```

建议分组：

```text
① 流动物理
Case
Mach
ε

② 数值设置
Nx
Ny
CFL
T
Reconstruction

③ ShockPath 方法
q_aa
q_at
Gate

④ 输出分析
Density
Pressure
Mach
Entropy
Pi_at
Shock width
Front RMS
HF metric
```

原则：

> 只有后端真实支持的参数才能开放。

禁止为了“看起来专业”暴露实际上无效的输入项。

---

# 4.3 自然语言模式

面向：

- 普通学生；
- 评委；
- 希望快速描述实验需求的用户。

示例输入：

```text
帮我建立一个 Mach 6 的 Case 8，
使用论文配置，
q_aa 保持 3.96，
把 q_at 改成 0.30。
```

AI 输出 `ExperimentConfigDraft`：

```text
Case          Case 8
Mach          6.0
Profile       Paper
q_aa          3.96
q_at          0.30
```

若用户修改了论文冻结参数：

```text
论文配置
→ 论文尺度 · 自定义参数
```

系统必须显示：

```text
当前不是论文标准 D_u 复现。
```

流程：

```text
用户自然语言
    ↓
AI Parser
    ↓
ExperimentConfigDraft
    ↓
Backend Validation
    ↓
配置预览
    ↓
用户确认
    ↓
创建 Run
```

AI 不得绕过用户确认直接启动高成本 CFD。

---

# 5. 统一 ExperimentConfig

三个输入入口最终都映射为统一模型：

```python
ExperimentConfig
```

建议结构：

```json
{
  "case_id": "case8",
  "profile": "fast",
  "physics": {
    "mach": 6.0,
    "epsilon": 0.0001
  },
  "grid": {
    "nx": 64,
    "ny": 16
  },
  "time": {
    "cfl": 0.05,
    "final_time": 0.04
  },
  "method": {
    "method_id": "cross_mode_ec_unified_v1",
    "q_aa": 3.96,
    "q_at": 0.396,
    "gate": "acoustic"
  },
  "discretization": {
    "reconstruction": "first_order"
  },
  "output": {
    "snapshot_interval": 100
  }
}
```

---

# 6. 计算模式

# 6.1 普通配置

用途：

```text
快速交互
比赛演示
参数探索
```

Case 8 初始建议：

```text
Grid = 64 × 16
CFL = 0.05
T = 0.04
```

最终值以真实 benchmark 为准。

状态：

```text
LIVE_FAST_RUN
```

必须明确：

> 普通配置用于快速交互，不等于论文正式复现实验。

---

# 6.2 论文配置

Case 8 正式协议：

```text
Grid = 128 × 32
CFL = 0.05
T = 0.08
```

支持标准配置：

```text
A_u
B_u
C_u
D_u
```

如果用户未修改论文参数：

```text
LIVE_PAPER_PROFILE
```

如果修改任一正式参数：

```text
PAPER_SCALE_CUSTOM
```

不得继续展示为“论文标准复现”。

---

# 6.3 自定义配置

专业模式或 AI 模式修改：

```text
Mach
Grid
CFL
T
q_aa
q_at
Gate
Reconstruction
ε
```

则标记：

```text
CUSTOM_RUN
```

---

# 7. 第一阶段支持的流动问题

第一阶段只真正开发：

```text
Case 8
```

架构从一开始支持未来扩展：

```text
Case 8
周期等熵涡
近一维受扰激波
Mach 3 圆柱绕流
```

但开发顺序必须：

```text
Case 8 完整闭环
    ↓
稳定
    ↓
再添加其他 Case
```

不同时开发多个 Live Solver。

---

# 8. 求解器总体架构

```text
Vue Web UI
   ↓
Experiment Builder
   ↓
ExperimentConfig
   ↓
Flask /api/v2
   ↓
Run Manager
   ↓
Case8SolverAdapter
   ↓
Existing CFD Solver
   ↓
cross_mode_ec_unified_v1
   ↓
Raw Run Output
   ↓
Scientific Postprocess
   ↓
ScientificRunResult
   ↓
Visualization / AI / Report
```

---

# 9. Solver Adapter

不要为了网页重写第二套 CFD。

新增：

```text
backend/
  solver_runtime/
      run_manager.py
      solver_adapter.py
      case8_adapter.py
      run_store.py
      progress.py
```

`Case8SolverAdapter` 只负责：

```text
ExperimentConfig
        ↓
转换成真实 solver 配置
        ↓
启动原求解器
        ↓
监控运行
        ↓
保存 diagnostics
        ↓
保存 snapshots
        ↓
调用 postprocess
```

建议接口：

```python
class Case8SolverAdapter:

    def validate_config(self, config):
        ...

    def prepare_run(self, run):
        ...

    def execute(self, run, progress_callback):
        ...

    def postprocess(self, run):
        ...
```

---

# 10. Run Manager

每一次 CFD 求解都形成一个 Run：

```text
RUN-20261002-000001
```

状态：

```text
QUEUED
STARTING
RUNNING
POSTPROCESSING
COMPLETED
FAILED
CANCELLED
```

`RunRecord`：

```text
run_id
config
status
created_at
started_at
finished_at
current_step
physical_time
progress
error
result_id
```

第一版不需要 Redis / Celery。

优先：

```text
Python subprocess
或
受控 ProcessPool
```

第一版：

```text
MAX_CONCURRENT_RUNS=1
```

---

# 11. Runtime 数据目录

新增：

```text
runtime/
  runs/
```

示例：

```text
runtime/
└── runs/
    └── RUN-20261002-000001/
        ├── config.json
        ├── status.json
        ├── provenance.json
        ├── solver.log
        │
        ├── diagnostics/
        │   ├── history.csv
        │   ├── entropy.csv
        │   └── residual.csv
        │
        ├── snapshots/
        │   ├── step_000000.npz
        │   ├── step_000100.npz
        │   ├── step_000200.npz
        │   └── final.npz
        │
        ├── derived/
        │   ├── metrics.json
        │   ├── entropy_budget.json
        │   ├── front.npy
        │   └── pi_at.npy
        │
        └── report/
            └── report_context.json
```

禁止写入：

```text
D:\Paper\passage6
```

---

# 12. API 设计

V1 `/api/v1` 保持不变。

V2 使用：

```text
/api/v2
```

建议接口：

```text
POST /api/v2/experiments/validate
POST /api/v2/experiments/parse-natural-language

POST /api/v2/runs
GET  /api/v2/runs/{run_id}
GET  /api/v2/runs/{run_id}/events
POST /api/v2/runs/{run_id}/cancel

GET  /api/v2/runs/{run_id}/history
GET  /api/v2/runs/{run_id}/snapshots
GET  /api/v2/runs/{run_id}/snapshot/{snapshot_id}
GET  /api/v2/runs/{run_id}/result

POST /api/v2/ai/runs/{run_id}/interpret
POST /api/v2/ai/chat

POST /api/v2/reports/{run_id}
GET  /api/v2/reports/{run_id}
```

---

# 13. HTTP 与实时运行

错误方式：

```text
POST /runs
↓
HTTP 等待 CFD 运行几十秒
↓
返回结果
```

正确方式：

```text
POST /runs
↓
立即创建 run_id
↓
返回
↓
后台独立求解
```

返回：

```json
{
  "run_id": "RUN-20261002-000001",
  "status": "QUEUED"
}
```

实时进度第一版建议：

```text
SSE
Server-Sent Events
```

接口：

```text
GET /api/v2/runs/{run_id}/events
```

---

# 14. Live Run Workspace

Route：

```text
/runs/:runId
```

运行中展示：

```text
RUN-0017                  ● 正在求解

Case 8
普通配置
q_aa = 3.96
q_at = 0.396

Step          624
Physical t    0.0254
Progress      34%
Runtime       12.8 s

██████████░░░░░░░░░░
```

如果 solver 已支持周期 snapshot：

```text
最新 Density
[ CFD field ]
```

如果第一版尚不能实时 snapshot：

先实现：

```text
status
step
physical time
runtime
```

求解完成后再显示 final field。

---

# 15. ScientificRunResult

AI 不直接读取 `.npz/.npy`。

后处理统一生成：

```python
ScientificRunResult
```

结构：

```text
identity
config
runtime
fields
entropy
metrics
allocation
limitations
provenance
```

任何缺失数据：

```text
null + availability
```

禁止以 `0` 代替缺失。

---

# 16. 结果工作台

求解完成后同一个 `/runs/:runId` 页面切换为结果状态。

建议布局：

```text
┌─────────────────────────────────────────────────────┐
│ Case 8 / RUN-0017                  ● 计算完成       │
│ q_aa=3.96 · q_at=0.396 · Fast                      │
├─────────────────────────────────┬───────────────────┤
│                                 │ AI 结果解读       │
│      CFD Scientific View        │                   │
│                                 │ 本次实验……        │
│ [Density ▼]                     │                   │
│                                 │ 关键发现          │
│          FIELD                  │ ① ...             │
│                                 │ ② ...             │
├─────────────────────────────────┤                   │
│ Entropy / Metrics               ├───────────────────┤
│ E_bg / E_aa / E_at              │ AI 科研助手       │
│ Shock width                     │                   │
│ Front RMS                       │ [输入问题...]     │
│ HF                              │                   │
├─────────────────────────────────┴───────────────────┤
│               [ 生成实验报告 ]                      │
└─────────────────────────────────────────────────────┘
```

---

# 17. 科学可视化

第一版不使用 Blender。

## 17.1 流场

支持：

```text
Density ρ
Pressure p
Velocity |u|
Mach
```

优先复用现有 Canvas/ECharts viewer。

---

## 17.2 耗散路径

ShockPath 特征层：

```text
Pi_bg
Pi_aa
Pi_at
```

累计预算：

```text
E_bg
E_aa
E_at
```

---

## 17.3 宏观指标

例如：

```text
Shock width
Front RMS
HF metric
```

界面必须注明：

> 当前指标仅描述当前流动与当前配置，不构成普适性能排名。

---

## 17.4 时间演化

若存在多个 snapshots：

```text
t=0 ─────●───────────── T
```

支持：

```text
播放
暂停
上一帧
下一帧
```

---

# 18. AI 总体架构

新增：

```text
backend/
  ai/
      client.py
      config_parser.py
      context_builder.py
      interpreter.py
      assistant.py
      report.py
      prompts.py
```

AI Provider 使用 DeepSeek。

API Key：

```text
只能存在 backend 环境变量
```

建议配置：

```env
DEEPSEEK_API_KEY=<rotated-key>
DEEPSEEK_BASE_URL=<provider-base-url>
DEEPSEEK_MODEL=<actual-model-id>
```

实际模型 ID 以当前 DeepSeek 账户/API 文档可用值为准，不在源码硬编码密钥。

---

# 19. AI Experiment Parser

自然语言输入专用。

输入：

```text
帮我用论文尺度跑 Case 8，
Mach 6，
q_aa=3.96，
q_at=0.30。
```

AI只输出：

```text
ExperimentConfigDraft
```

之后必须：

```text
Backend Validation
↓
UI Preview
↓
User Confirm
```

AI 不直接启动 CFD。

---

# 20. ScientificAIContext

AI 解释结果时只读取结构化科学上下文：

```json
{
  "run": {},
  "config": {},
  "entropy": {},
  "metrics": {},
  "allocation": {},
  "current_view": {},
  "selected_region": {},
  "limitations": [],
  "evidence": []
}
```

流程：

```text
Raw CFD
↓
Postprocess
↓
ScientificRunResult
↓
ScientificAIContext
↓
AI
```

禁止：

```text
AI 直接读取几十 MB NPZ 后自行推导数值
```

---

# 21. AI 自动结果解释

Run 完成后自动请求：

```text
POST /api/v2/ai/runs/{run_id}/interpret
```

AI 输出结构化 JSON：

```text
summary
key_findings[]
observations[]
limitations[]
suggested_questions[]
```

前端自己排版。

AI输出应分开：

```text
事实
解释
科学边界
```

---

# 22. AI 科研助手

结果页右侧常驻：

```text
AI 科研助手
```

用户可以问：

```text
q_at 在这次实验里做了什么？
为什么这里 Pi_at 很高？
这次结果和论文 D_u 有什么不同？
这能说明当前配置更稳定吗？
为什么 E_at 增加而某个指标没有下降？
```

AI Context 包含：

```text
current_run
current_variable
current_snapshot
selected_region
metrics
entropy
limitations
evidence
```

因此 AI 是：

> 上下文感知的科研助手

而不是普通 Chatbot。

---

# 23. AI 科学边界

System Prompt 必须要求：

```text
所有数值事实只能来自 structured scientific context。
缺失数据必须明确说明不可用。
禁止猜测 CFD 数值。
必须区分事实、解释和科学边界。
不得把单一 Case 结果扩展为普适结论。
不得根据 E_at 大小直接判断方法优劣。
```

禁止 AI 宣称：

```text
universally stable
best gate
best method
all modes improved
guaranteed stability
all-Mach robust
```

---

# 24. 自动实验报告

按钮：

```text
生成实验报告
```

第一版生成 HTML。

Route：

```text
/runs/:runId/report
```

固定结构：

```text
ShockPath 数值实验报告

1. 实验概况
2. 输入方式
3. 流动物理参数
4. 数值配置
5. ShockPath 方法配置
6. 求解过程
7. 流场结果
8. 熵耗散路径分析
9. 宏观指标
10. AI 科学解读
11. 科学边界
12. Provenance / Evidence
```

程序负责：

```text
数值
表格
配置
运行信息
图表
provenance
```

AI负责：

```text
自然语言解释
结果总结
科学边界表述
```

后续再增加 PDF 导出。

---

# 25. 一级导航建议

V2：

```text
首页
新建实验
实验工作台
引导探索
证据中心
```

AI 助手不作为一级导航。

它属于：

```text
Run Result Workspace
```

---

# 26. 新建实验页

Route：

```text
/experiments/new
```

首屏：

```text
创建实验

你希望如何开始？

┌──────────────┐
│ 快速模板      │
│ 选择标准算例 │
│ 快速开始     │
└──────────────┘

┌──────────────┐
│ 专业模式      │
│ 自定义物理与 │
│ 数值参数     │
└──────────────┘

┌──────────────┐
│ AI 创建实验   │
│ 用自然语言   │
│ 描述实验     │
└──────────────┘
```

三种模式最终都进入：

```text
实验配置摘要
```

例如：

```text
Case               Case 8
Mach               6
Grid               128 × 32
CFL                0.05
T                  0.08
q_aa               3.96
q_at               0.30
Gate               Acoustic
Reconstruction     First-order
Profile            Paper-scale custom
```

最后：

```text
[ 确认并开始求解 ]
```

---

# 27. 实验工作台

Route：

```text
/workspace
```

分类：

```text
运行中
已完成
失败
```

Run Card：

```text
Run ID
Case
Profile
q_aa
q_at
Status
Created At
```

操作：

```text
查看
继续分析
生成报告
取消（仅运行中）
```

---

# 28. 未来输入扩展

第一版完成后，可以逐步增加：

```text
初始条件 U_L / U_R
更多边界条件模板
更多重构方法
更多流动模板
上传初始场
参数扫描
Run A/B 对比
```

暂时不要做：

```text
任意 PDE
任意几何
通用网格生成器
Fluent 替代品
云端分布式求解
```

ShockPath 的核心是：

> 嵌入论文耗散路径方法的可控数值实验平台。

---

# 29. 开发阶段

# V2-P1：Unified Experiment Builder

目标：

```text
三种输入
↓
同一个 ExperimentConfig
↓
后端统一验证
```

完成：

- 模板模式；
- 专业模式；
- AI 自然语言解析；
- 配置摘要；
- 用户确认；
- Case Registry；
- Parameter Capability Registry。

此阶段先不要求 CFD 真跑。

---

# V2-P2：Real Solver Connectivity

目标：

```text
ExperimentConfig
↓
Case8SolverAdapter
↓
真实 Case 8 solver
↓
cross_mode_ec_unified_v1
↓
真实输出
```

最低验证：

```text
Run A:
q_aa=3.96
q_at=0

Run B:
q_aa=3.96
q_at=0.396
```

必须确认：

```text
两次 solver config 确实不同
两次均为独立真实 CFD
```

---

# V2-P3：Live Run Workspace

完成：

```text
Run Manager
background process
status
step
physical_time
runtime
progress
SSE
cancel
final density
```

---

# V2-P4：Scientific Result Workspace

完成：

```text
Density
Pressure
Mach
Entropy history
E_bg
E_aa
E_at
Pi_at
Shock width
Front RMS
HF
```

只展示后处理真实支持的量。

---

# V2-P5：AI Interpretation + Assistant

完成：

```text
ScientificAIContext
DeepSeek backend client
automatic interpretation
AI scientific assistant
current-view awareness
```

AI failure 不影响 CFD 使用。

---

# V2-P6：Automatic Report

完成：

```text
HTML report
fixed report structure
deterministic tables
AI interpretation
scientific limitations
provenance
```

---

# V2-P7：Compare / Parameter Sweep

最后开发：

```text
Run A vs Run B
q_aa sweep
q_at sweep
epsilon sweep
```

用于真正发挥“数字实验平台”价值。

---

# 30. 当前不开发

首期禁止扩张：

```text
Blender
3D
VTK
任意几何
mesh editor
通用 PDE
用户账户体系
大型数据库
分布式计算
AI 自主代理运行任意 CFD
```

先完成：

```text
Case 8
→ 三种输入
→ 真求解
→ 真可视化
→ AI解释
→ AI助手
→ 报告
```

---

# 31. V2 第一阶段最终用户体验

## 普通评委

```text
进入 ShockPath
↓
新建实验
↓
模板模式
↓
Case 8
↓
D_u
↓
普通配置
↓
开始求解
↓
看到真实运行
↓
看到 CFD 流场
↓
看到 AI 解释
↓
向 AI 提问
↓
生成报告
```

---

## CFD 专业用户

```text
新建实验
↓
专业模式
↓
Mach / Nx / Ny / CFL / T
q_aa / q_at / Gate / Reconstruction / ε
↓
运行
↓
查看真实场和熵耗散
↓
AI辅助分析
```

---

## 普通学生

```text
AI 创建实验
↓
“帮我跑一个 Mach 6 Case 8，
q_at 设置成 0.2”
↓
AI生成配置草稿
↓
用户确认
↓
真实求解
↓
AI解释
```

---

# 32. 核心竞争力

ShockPath V2 不应被描述为：

> 一个 CFD 可视化网站。

而应该描述为：

> **一个将新型熵稳定耗散路径方法、真实 CFD 求解、科学可视化与 AI 科研分析融合在一起的交互式数值实验平台。**

其区别在于：

传统 CFD 软件：

```text
设置参数
→ 求解
→ 流场
```

ShockPath：

```text
设置参数
→ 耗散路径设计
→ 真实求解
→ 流场
→ 熵预算
→ 空间分配
→ 宏观响应
→ AI解释
→ Evidence
→ 实验报告
```

---

# 33. 最核心的一句话

> **三个输入入口，一个真实求解器；数值由 Solver 产生，规律由 Postprocess 测量，结果由可视化呈现，含义由 AI 辅助解释，可信性由 Evidence 追踪。**

---

# 34. 当前立即执行的开发顺序

现在不要继续大规模美化 UI。

优先：

```text
V2-P1
Unified Experiment Builder
```

随后：

```text
V2-P2
Real Solver Connectivity
```

只有真实链路：

```text
用户输入
→ ExperimentConfig
→ Solver
→ cross_mode_ec_unified_v1
→ CFD 结果
```

跑通以后，再依次开发：

```text
P3 Live Workspace
P4 Scientific Result Workspace
P5 AI
P6 Report
P7 Compare / Sweep
```

这将成为 ShockPath V2 的正式开发主线。

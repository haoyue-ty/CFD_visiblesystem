# ShockPath 项目化方案  
## ——将《熵稳定耗散路径》CFD 论文转化为数媒大赛与计算机设计大赛参赛项目

> **项目定位**：将论文中的数值方法、真实 CFD 实验、熵预算观测、空间分配分析与 Fourier 模态分析，转化为一个**可交互、可运行、可解释、可复现的科研可视分析平台**。  
> **核心目标**：不是把论文“做成网页”，而是把论文里的科学机制变成评委能够操作、观察和验证的数字产品。

---

# 1. 项目名称与核心定位

## 1.1 推荐项目名

**ShockPath**  
**面向多维可压缩流动的熵稳定耗散路径数字实验与可视分析平台**

英文名：

**ShockPath — An Interactive Visual Analytics Platform for Identifiable Dissipation Pathways in Multidimensional Compressible Flows**

## 1.2 一句话介绍

> **让“看不见”的数值耗散，变得可设计、可测量、可定位、可追踪。**

## 1.3 核心科学问题

传统 CFD 往往把数值耗散理解为“大小不同的一个整体量”，而论文建立的是：

\[
\text{Parameter}
\rightarrow
\text{Pathway}
\rightarrow
\text{Entropy Budget}
\rightarrow
\text{Spatial Allocation}
\rightarrow
\text{Modal Response}
\rightarrow
\text{Macroscopic Response}
\]

因此项目不强调“某个参数更优”，而强调：

- 耗散由什么信息触发；
- 耗散作用于哪个模态；
- 每条耗散路径产生多少熵；
- 耗散发生在什么空间区域；
- 不同横向波数如何响应；
- 最终宏观流场为什么会出现不同结果。

核心科学表达：

> **Dissipation magnitude alone is insufficient.**

进一步可以概括为：

\[
\boxed{
\text{Pathway Budget}
\neq
\text{Spatial Allocation}
\neq
\text{Macroscopic Consequence}
}
\]

---

# 2. 论文如何转化为比赛项目

论文解决的是“科学问题”，比赛项目要解决的是“如何让别人使用、理解和验证这些成果”。

因此建议形成：

```text
JCP 论文
   ↓
算法 / Solver / 实验数据
   ↓
ShockPath 科研软件底座
   ↓
交互式科学可视化
   ↓
可运行实验平台
   ↓
可复现实验中心
   ↓
数媒大赛 / 计算机设计大赛
```

重点不是重新做大量实验，而是把已有的：

- CFD solver；
- cross-mode dissipation 方法；
- trajectory-level entropy observer；
- Case 8 / Cylinder / Vortex 等生产实验；
- Gate ablation；
- Fourier-Jacobian 分析；
- 模态验证；
- FREEZE / hash / CSV / JSON / NPY 数据；

统一转化为一个完整的产品。

---

# 3. 项目整体架构

建议采用：

## “一个科研计算底座 + 两种使用模式”

### 3.1 Explore Mode —— 科普 / 展示模式

面向：

- 数媒大赛评委；
- 非 CFD 专业评委；
- 科普展示；
- 演示视频。

目标是让用户不需要先理解复杂公式，就可以顺着问题理解：

1. 激波为什么需要数值耗散？
2. 耗散是不是越大越好？
3. 耗散由什么触发？
4. 耗散作用在哪里？
5. 相同总耗散为什么可能产生不同结果？
6. 为什么正的熵耗散并不等价于所有模态都更稳定？

强调：

- 动画；
- 交互；
- 真实 CFD 数据；
- 机制链；
- 视觉叙事。

---

### 3.2 Lab Mode —— 科研实验模式

面向：

- 计算机设计大赛；
- 科研软件展示；
- CFD 用户；
- 答辩技术演示。

用户可以选择：

- Case 8；
- Mach 3 Cylinder；
- Isentropic Vortex；
- Mach 6 perturbation；
- Fourier shock analysis。

可以设置：

\[
q_{aa},\quad q_{at},\quad Gate,\quad CFL,\quad \varepsilon
\]

系统自动加载真实运行结果，或者运行小规模 CFD Demo，并生成：

- shock width；
- front RMS；
- high-frequency energy；
- \(E_{bg}\)；
- \(E_{aa}\)；
- \(E_{at}\)；
- \(\Pi_{at}\) 空间分布；
- shock localization；
- spectral abscissa；
- eigenmode；
- linear / CFD growth rate comparison。

最终效果是：

> **用户可以直接“操作这篇论文”。**

---

# 4. 七个核心功能模块

| 模块 | 功能 | 对应论文内容 |
|---|---|---|
| 01 Mechanism Explorer | Cross-mode 路径机制交互展示 | Fig.1–2 |
| 02 CFD Experiment Lab | 实验选择、参数设置、结果回放 | 全部 CFD 实验 |
| 03 Entropy Ledger | 三通道熵产预算与闭合验证 | Sec.3 |
| 04 Allocation Explorer | Gate、\(\Pi_{at}\)、空间局部化分析 | Fig.6–9 |
| 05 Spectral Lab | Fourier 模态与谱响应分析 | Fig.10–13 |
| 06 Cross-flow Compare | Case 8 与 Cylinder 跨流动比较 | Fig.14–17 |
| 07 Reproducibility Center | 配置、hash、数据与复现实验 | FREEZE / manifest |

---

# 5. Module 01：Mechanism Explorer

## 5.1 目标

把论文 Fig.1 的静态机制图变成可以操作的交互图。

主要结构：

```text
Interface State
      │
      ├──────── Background PSD Kernel
      │
      └──────── Acoustic Gate J
                       │
              ┌────────┴────────┐
              ↓                 ↓
       Acoustic Output   Tangential Output
              │                 │
              └────────┬────────┘
                       ↓
            Entropy-scaled Combiner
                       ↓
            Physical Entropy Variables
```

## 5.2 关键交互

用户拖动：

\[
q_{aa}
\]

或：

\[
q_{at}
\]

对应 pathway 实时变化。

例如：

### \(q_{at}=0\)

Cross-mode pathway 灰色关闭。

### \(q_{at}>0\)

Tangential pathway 激活。

实时显示：

- \(J\)；
- \(P_a z\)；
- \(P_t z\)；
- \(\Pi_{aa}\)；
- \(\Pi_{at}\)。

## 5.3 1D / 2D 对比

做一个动画版 Fig.2：

### Strictly 1D

虽然：

\[
J>0
\]

但：

\[
P_tz=0
\]

因此：

\[
\Pi_{at}=0
\]

### Weakly 2D

出现非零 tangential content：

\[
P_tz\neq0
\]

于是：

\[
\Pi_{at}>0
\]

这部分非常适合作为评委理解 cross-mode 的第一入口。

---

# 6. Module 02：CFD Experiment Lab

## 6.1 实验选择

建议提供卡片：

- Case 8；
- Mach 3 Cylinder；
- Isentropic Vortex；
- Near-1D Mach 6 Shock；
- Fourier Shock Base State。

## 6.2 参数面板

用户可以选择：

```text
q_aa
q_at
Gate
CFL
Perturbation ε
Reconstruction
```

## 6.3 两种运行模式

### Replay Mode

调用已经冻结的真实生产数据。

优点：

- 快；
- 稳定；
- 可以展示完整高分辨率结果。

### Live Demo Mode

运行小规模网格，例如：

- 64×16；
- 128×32。

用于现场证明系统不是“录屏播放器”。

---

# 7. Module 03：Entropy Ledger

这是整个项目最值得重点打造的模块之一。

## 7.1 核心表达

把数值耗散做成“科学账本”。

```text
                 Numerical Dissipation
                         │
             ┌───────────┼───────────┐
             ↓           ↓           ↓
           Π_bg        Π_aa        Π_at
             │           │           │
          E_bg(t)     E_aa(t)     E_at(t)
```

## 7.2 时间轴

```text
t = 0 ━━━━━━━━━━━━━━━━━━━━━━━ t = T
```

拖动时间轴时同步更新：

- CFD 场；
- 三个通道瞬时熵产；
- 累计熵产；
- 总预算；
- shock location；
- front response。

## 7.3 闭合验证

加入：

### Semi-discrete closure

\[
G(U)+D(U)\approx0
\]

### Fully-discrete residual

\[
R(T)=\Delta S(T)+E_{obs}(T)
\]

以图表展示：

- 浮点精度闭合；
- CFL 减小时近三阶衰减。

这一模块可以证明：

> 平台中的 pathway budget 不是视觉包装，而是与真实 finite-volume RHS 一致的数值量。

---

# 8. Module 04：Allocation Explorer

## 8.1 核心问题

> **相同总预算，会不会分配到不同位置？**

提供三个 Gate：

```text
○ Acoustic Gate
○ Pressure Gate
○ Ungated
```

## 8.2 真实实验结果

三种 Gate 的总 \(E_{at}\) 非常接近，但 shock-window allocation 明显不同：

- Acoustic：约 99.83%
- Pressure：约 99.17%
- Ungated：约 89.23%

系统展示：

- 相同物理域；
- 相同色标；
- shock window；
- \(\Pi_{at}\) 空间热图；
- cumulative allocation curve；
- inside / outside fraction。

中央强调：

> **Same budget ≠ same allocation**

---

# 9. Module 05：Spectral Lab

这是项目中科研深度最高的模块。

## 9.1 主要交互

拖动：

\[
q_{at}:0\rightarrow0.396
\]

系统更新：

\[
\alpha(\ell,q_{at})
\]

横轴：

\[
\ell=0,\ldots,16
\]

纵轴：

\[
\max \Re(\lambda)
\]

## 9.2 点击 Fourier mode

例如点击：

- \(\ell=1\)
- \(\ell=4\)
- \(\ell=8\)
- \(\ell=12\)

弹出：

- leading eigenmode；
- shock localization fraction；
- \(q_{at}=0\)；
- \(q_{at}=0.396\)。

## 9.3 核心表达

用户可以看到：

- 某些模态向左移动；
- 某些模态向右移动；
- 高波数响应不同；
- 最大 spectral abscissa 不一定下降。

中央强调：

> **Positive entropy production ≠ uniform modal damping**

## 9.4 Linear vs CFD

调用 Fig.13 对应数据：

比较：

\[
\sigma_{RK3}
\]

与：

\[
\sigma_{CFD}
\]

显示短时间增长率高度一致。

这一步证明 spectral response 确实存在于生产求解器中。

---

# 10. Module 06：Cross-flow Compare

左右同时显示：

## Case 8

- 平面激波；
- front window；
- cross-mode localization；
- front RMS；
- HF energy。

## Mach 3 Cylinder

- 弯曲 bow shock；
- angular sectors；
- front-band；
- front RMS；
- HF-RMS。

对比：

```text
Pathway budget
Spatial allocation
Shock width
Front RMS
High-frequency response
```

最后给出：

\[
\boxed{
\text{Same Pathway}
+
\text{Different Flow}
\Rightarrow
\text{Different Allocation}
+
\text{Different Response}
}
\]

并强调：

\[
\boxed{
\text{Pathway Budget}
\neq
\text{Pathway Allocation}
\neq
\text{Macroscopic Consequence}
}
\]

---

# 11. Module 07：Reproducibility Center

这一部分是项目区别于普通学生可视化项目的重要模块。

展示：

```text
Method
cross_mode_ec_unified_v1

Method Hash
98776078...

Configuration
q_aa = ...
q_at = ...

Grid
128 × 32

Integrator
SSP-RK3

Evidence
✓ Raw trajectory
✓ Entropy budget
✓ Pi_at field
✓ Metrics
✓ Postprocess config
✓ Freeze manifest
```

提供：

- 数据索引；
- 实验配置；
- SHA-256；
- method hash；
- frozen evidence；
- summary；
- verify 按钮。

目标：

> 从“展示作品”升级为“科研软件”。

---

# 12. 系统页面建议

第一版控制在 6+1 页面，不要做得过多。

## Page 1：首页

ShockPath Hero Scene

重点展示：

- Case 8；
- Cylinder；
- 三条耗散路径；
- 项目一句话介绍。

---

## Page 2：Mechanism

对应：

- cross-mode architecture；
- strict 1D inactivity；
- trigger-output separation。

---

## Page 3：Experiment

参数：

- case；
- \(q_{aa}\)；
- \(q_{at}\)；
- gate；
- reconstruction；
- run / replay。

---

## Page 4：Entropy + Allocation

重点：

- entropy ledger；
- \(E_{at}\)；
- \(\Pi_{at}\)；
- gate allocation。

---

## Page 5：Spectral Lab

重点：

- spectral abscissa；
- eigenmode；
- RK3 / CFD validation。

---

## Page 6：Case Comparison

重点：

- Case 8；
- Cylinder；
- cross-flow response。

---

## Page 7：Reproducibility

重点：

- config；
- hash；
- raw data；
- freeze；
- verification。

---

# 13. 技术架构建议

## 13.1 前端

推荐：

- Vue 3 或 React；
- ECharts；
- Plotly；
- vtk.js；
- WebGL。

用途：

- 折线图；
- heatmap；
- CFD field；
- interaction；
- mode visualization。

## 13.2 后端

推荐：

**Python + FastAPI**

原因：

- 现有 CFD 代码本身就是 Python；
- NumPy / SciPy 数据链可以直接复用；
- 易于对接 solver 与 postprocess。

## 13.3 数据结构

统一所有实验：

```text
experiments/
├── case8/
│   ├── config.json
│   ├── state.npz
│   ├── entropy.csv
│   ├── Pi_at.npy
│   ├── metrics.json
│   └── spectrum.csv
│
├── cylinder/
├── vortex/
├── gate_ablation/
├── near_1d/
└── spectral/
```

## 13.4 后端 API

建议：

```text
/api/cases
/api/config
/api/run
/api/replay
/api/entropy
/api/allocation
/api/spectrum
/api/eigenmode
/api/metrics
/api/verify
```

---

# 14. 计算模式设计

不要让所有大实验都现场重跑。

推荐：

```text
                    ShockPath
                        │
          ┌─────────────┴─────────────┐
          ↓                           ↓
     Replay Engine               Live Solver
   冻结生产数据                   小型实时实验
          │                           │
          └─────────────┬─────────────┘
                        ↓
                 Analysis Engine
                        ↓
                 Visual Analytics
```

## Replay Engine

展示：

- Case 8；
- Cylinder；
- full entropy trajectory；
- spectral analysis；
- eigenmode；
- gate ablation。

## Live Solver

只运行：

- 小网格；
- 短时间；
- 简化 demo。

目的：

证明系统是真实计算软件。

---

# 15. 数媒大赛版本

## 15.1 项目定位

重点不是“CFD 新方法”，而是：

> **科学数据可视化 + 交互式科研实验平台**

## 15.2 重点投入

建议项目制作资源大致投入：

- 视觉表达：35%
- 交互体验：25%
- 技术创新：25%
- 科学内容：15%

这不是官方评分，而是开发优先级建议。

## 15.3 数媒版本重点

突出：

- 可视化；
- 动画；
- 交互；
- 科学故事；
- 用户理解成本低；
- 实验真实性。

---

# 16. 计算机设计大赛版本

后续版本建议定位为：

> **面向 CFD 数值方法研发的可复现实验、耗散归因与模态分析软件平台**

重点从“展示”转为“软件”。

开发重心：

- 工程系统：35%
- 算法创新：30%
- 功能完整度：20%
- 可视化：15%

重点加强：

- 用户管理；
- 实验配置；
- 后端任务；
- 结果数据库；
- 批量对比；
- 结果导出；
- 复现实验；
- solver 插件化。

---

# 17. 论文 17 张图如何项目化

| 论文图 | 项目功能 |
|---|---|
| Fig.1 | Interactive Pathway Architecture |
| Fig.2 | 1D / 2D Activation Demo |
| Fig.5 | Parameter Explorer |
| Fig.6 | Gate Allocation Explorer |
| Fig.7 | Perturbation Scaling |
| Fig.8 | Smooth-flow Transfer |
| Fig.9 | Reconstructed Shock |
| Fig.10 | Discrete Shock Laboratory |
| Fig.11 | Interactive Spectrum |
| Fig.12 | Eigenmode Explorer |
| Fig.13 | Linear-vs-CFD Validation |
| Fig.14 | Case 8 Dashboard |
| Fig.15 | Cylinder Dashboard |
| Fig.16 | Cross-flow Comparison |
| Fig.17 | External Flux Context |

因此现有论文图和数据都可以继续复用，不需要推倒重做。

---

# 18. 项目开发优先级

## P0：必须完成

1. Mechanism Explorer
2. Case 8 Replay
3. Entropy Ledger
4. Gate Allocation
5. Spectral Lab
6. Case 8 / Cylinder Compare
7. Reproducibility Center

## P1：有时间再做

8. 小网格 Live CFD
9. Experiment Manager
10. 数据导出
11. 参数扫描任务
12. 视频录制模式

## P2：后期计算机设计大赛扩展

13. 任务队列
14. 用户实验管理
15. 数据库
16. 插件式 Solver
17. 自动报告
18. 云端计算

---

# 19. 数媒大赛答辩叙事

比赛答辩不要从 Euler 方程开始。

建议：

## 0–20 秒：问题

> CFD 中，大家常常讨论“需要多少耗散”，但真正影响数值结果的不只是耗散多少，还包括耗散由什么触发、作用在哪里以及如何改变离散动力学。

## 20–50 秒：项目

> 我们开发 ShockPath，将原本不可见的数值耗散转化为可以设计、测量、定位和追踪的交互式数字路径。

## 50–100 秒：Mechanism

调整：

\[
q_{at}:0\rightarrow0.396
\]

观察 cross-mode pathway activation。

## 100–160 秒：Allocation

切换：

- Acoustic；
- Pressure；
- Ungated。

强调：

> Same budget ≠ same allocation.

## 160–220 秒：Spectral

展示：

> Positive entropy production ≠ uniform modal damping.

## 220–270 秒：Cross-flow

比较：

- Case 8；
- Cylinder。

## 最后

总结：

> ShockPath 建立了从参数、耗散路径、熵预算、空间分配、离散模态一直到宏观流场响应的完整数字机制链。

---

# 20. 项目最终成果包

```text
ShockPath/
│
├── Web Interactive Platform
├── CFD Solver
├── Entropy Observer
├── Spectral Analysis Engine
├── Experiment Database
├── Replay Engine
├── Live Demo Solver
├── Reproducibility Center
├── Competition Video
├── Presentation
├── Technical Whitepaper
└── JCP Paper
```

---

# 21. 当前最重要的开发原则

## 21.1 不要继续大量补 CFD 实验

现在比赛项目最大的收益已经不是：

> 再跑几个 benchmark。

而是：

> 把已有真实实验变成一个可以被操作和验证的产品。

只补：

- 小网格实时演示；
- 项目必须的数据接口；
- 缺失的交互数据。

---

## 21.2 真实数据优先

所有核心页面尽量读取：

- 真实生产数据；
- 冻结数据；
- 实际 CSV；
- 实际 NPY；
- 实际 solver output。

不能为了视觉效果伪造实验结果。

---

## 21.3 项目与论文保持同一科学边界

项目不能宣传：

- universal shock stabilizer；
- universal carbuncle cure；
- 所有模态都会更稳定；
- \(q_{at}\) 越大越好。

应该保持论文中的结论：

> Cross-mode pathway 可以被设计、测量、归因和追踪，但最终动力学后果具有明显的状态依赖、波数依赖和几何依赖。

---

# 22. 推荐开发周期

## 第一阶段：项目冻结

完成：

- 项目名称；
- logo；
- 页面结构；
- 数据结构；
- API 结构；
- UI 风格。

## 第二阶段：数据标准化

把已有实验统一整理为：

```text
config
state
entropy
allocation
metrics
spectrum
metadata
```

## 第三阶段：核心平台

先完成：

1. Mechanism
2. Experiment
3. Entropy
4. Allocation
5. Spectrum

## 第四阶段：高级功能

完成：

- Case8 / Cylinder comparison；
- Reproducibility；
- Live solver。

## 第五阶段：比赛材料

完成：

- 项目说明书；
- PPT；
- Demo 视频；
- 海报；
- 项目摘要；
- 技术架构图；
- AI 使用说明。

---

# 23. 最终项目逻辑

整个项目最终形成三层价值：

## 科学层

提出并验证：

**Identifiable entropy-stable dissipation pathways**

## 软件层

构建：

**CFD Experiment + Entropy Attribution + Spectral Analysis Platform**

## 数媒层

实现：

**复杂数值物理机制的交互式科学可视化**

最终项目表达：

\[
\boxed{
\text{Scientific Method}
+
\text{Computational Platform}
+
\text{Visual Analytics}
=
\text{ShockPath}
}
\]

---

# 24. 最终推荐路线

```text
现有 JCP 论文
     ↓
冻结算法与实验数据
     ↓
ShockPath V1
     ↓
数媒大赛
“让复杂科研机制被看见”
     ↓
增加工程功能
     ↓
ShockPath V2
     ↓
计算机设计大赛
“让科研实验能够执行、分析与复现”
     ↓
软著 / 大创 / 开源科研软件 / 后续竞赛
```

---

# 25. 当前下一步

现在最值得马上做的是：

### Step 1
冻结项目名称、定位和 7 个模块。

### Step 2
扫描本地 `D:\Paper\passage6`，建立**数据资产清单**。

### Step 3
确定前端页面与 UI 原型。

### Step 4
统一真实数据格式。

### Step 5
让 Codex 基于现有 solver 和真实实验数据开始搭建 ShockPath。

---

## 项目核心口号

> **See where numerical dissipation goes.**

中文：

> **看见数值耗散如何被触发、分配，并最终影响流动。**

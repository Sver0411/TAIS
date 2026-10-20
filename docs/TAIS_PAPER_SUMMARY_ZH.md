# TAIS 中文论文概要：最终学术大修

题目保留：**Trust-Aware Adaptive Sampling and Communication for Resource-Constrained IoT Monitoring: A Simulation-Based Evaluation**。

## 研究问题与三项贡献

在故障、采样和通信限制下，单节点监测如何权衡事件质量、资源统计和接收端信息年龄？这些权衡在两套不同合成任务条件下是否稳定？

1. 可执行地集成已有健康诊断、事件分析、采样、上传、Binary v1和独立接收端评价。
2. 与固定周期、Delta、Variance、Rao-inspired独立调度作可复现比较，区别原生系统、公共组件版本和近似预算资格。
3. 保留跨合成任务的负面结果、短事件漏检、诊断盲区与年龄成本，建立条件边界。

这是系统评估贡献，不是首创C11、ChangeAnalyzer、deadband、二进制理论或联合采样通信概念。

## 科学表述的关键限制

G1和G2不只观测分布不同：背景、噪声、故障通道/过程、事件形状/时序以及**真值时间区间规则**共同改变。G1是物理幅度形成的内区间，G2是完整外生支持区间。因此当前证据只说明跨合成任务下优势是否保留，不能单独归因于distribution shift，更不等于外部农业现场泛化。

G1的SU40−Variance F1差为+4.88pp。G2为−4.32pp，95%描述性区间[−9.11,+0.18]pp：不支持SU40相近预算F1优势，也没有证明其总体F1劣势。G2 Recall差区间[−14.58,−2.97]pp低于零，但属于多指标、多基线中的未校正单端点描述。

## Fixed20与SU40的实际冲突

| G2指标 | SU40 | Fixed20+C11 |
|---|---:|---:|
| F1 | 46.31% | 55.10% |
| 采样 | 85,055 | 82,800 |
| Binary v1字节 | 959,129 | 2,940,838 |
| 故障诱发误报 | 157 | 353 |
| 接收端P95年龄 | 113s | 18s |

Fixed20质量点估计更高，SU40字节和操作性诱发误报更少、普通数据更旧；不存在所有维度同时占优的模式。通信收益部分来自可共享U模块，不全是采样策略原创性。

G2短事件SU20 Recall37.34%，覆盖92.34%；SU40 Recall9.22%，GateOnly9.69%。全支持替换的52个事件在Gate/SU20/SU40中均漏检。稳定偏移无C11专用类型位。所有旧失败和NO-GO结论保留。

## 统计与预算

原协议冻结指标族、对比列表、种子和5%规则，但未建立独立注册的唯一确认性primary endpoint。当前突出F1/Variance/Fixed20是事后论文组织选择。区间逐项、未校正且为描述性，不作全局显著优效结论。

新分析只读取现有采样数，保留60个对照-目标组合，按2/5/10%检查资格。三阈值分析是事后敏感性；5%复现原规则。资格变化不改变参数、样本或质量。完整[敏感性CSV](../results/tais-paper-review/budget_sensitivity.csv)。

## 论文与投稿状态

**A：可以开始选择合适渠道并准备正式投稿。** A只是开始准备，不是录用保证。研究范围限于仿真系统权衡，仍无自然故障真值、农业现场事件、真实无线、MCU电流或电池寿命测量；Rao-inspired也不是完整复现。

摘要约187词；正文收拢为两张主要结果表、架构和两张关键结果图；完整操作点、健康/接收诊断、次要区间和预算敏感性在附录/不可变数据中。作者/单位占位保留，AI工具使用和人类确认事项列入[投稿清单](TAIS_SUBMISSION_CHECKLIST.md)。最终页数、编译和渲染结论以[布局审计](TAIS_PAPER_LAYOUT_AUDIT.md)为准。

[英文源码](../papers/tais/manuscript.tex) · [PDF](../papers/tais/manuscript.pdf) · [修改记录](TAIS_PAPER_REVISION_CHANGELOG.md) · [质量审查](TAIS_PAPER_QUALITY_REVIEW.md)。历史G1/G2完整结果见[证据入口](TAIS_PAPER_EVIDENCE.md)和[原G2报告](TAIS_CROSS_GENERATOR_REPORT.md)；其中旧阶段的B判断保留在Git历史，本轮没有改变那些性能事实。

本轮不再追加研究开发；下一步仅限渠道、模板和正式投稿准备。

#!/usr/bin/env python3
"""Generate Chinese evidence/reviewer documents from saved G1 results.

Importing this historical writer also updates document and result entry files.
Use dedicated read-only verifiers to inspect existing publication artifacts."""
from pathlib import Path
import json,shutil
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/tais-paper'
s=pd.read_csv(OUT/'test/analysis/summary.csv');b=pd.read_csv(OUT/'test/analysis/budget_comparisons.csv');ci=pd.read_csv(OUT/'test/analysis/paired_intervals.csv');manifest=json.loads((OUT/'test/manifest.json').read_text())
def get(m,g='overall',v='native'):return s[(s.method==m)&(s.group==g)&(s['view']==v)].iloc[0]
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'
def pct(v):return 'N/A' if pd.isna(v) else f'{v*100:.2f}%'
def integer(v):return 'N/A' if pd.isna(v) else f'{v:,.0f}'
def cis(A,B,metric='f1',view='native'):
 r=ci[(ci.A==A)&(ci.B==B)&(ci.metric==metric)&(ci.group=='overall')&(ci['view']==view)].iloc[0];return f'[{r.ci95_low*100:+.2f}, {r.ci95_high*100:+.2f}] pp'
methods=['AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-S','JO-SU-20','JO-SU-30','JO-SU-40']+[f'Fixed-{x}+C11' for x in [5,10,20,30,40,60]]+[f'{k}-budget-{t}+C11' for t in ['Gate','SU40'] for k in ['Delta','Variance','Rao-inspired']]
rows=[]
for m in methods:
 r=get(m);rows.append([m,pct(r.precision),pct(r.recall),pct(r.f1),pct(r.rx_f1),integer(r.samples),integer(r.uploads),integer(r.binary_v1_bytes),integer(r.fault_induced_false)])
main=table(['方法（native）','Precision','Recall','F1','Rx F1','采样','上传','v1字节','诱发误报'],rows)
budget_tables=[]
for view in ['native','common']:
 rr=[]
 for _,r in b[b['view']==view].iterrows():rr.append([r.target,r.method,f'{r.minimum:g}/{r.cap:g}',f'{r.test_gap*100:+.2f}%',str(r.within_5pct),f'{(r.target_recall-r.recall)*100:+.2f} pp',f'{(r.target_f1-r.f1)*100:+.2f} pp',cis(r.target,r.method,view=view)])
 budget_tables.append('### '+view+'\n\n'+table(['TAIS目标','独立方法','min/cap秒','实际采样差','±5%内','TAIS−对手Recall','TAIS−对手F1','F1配对95%CI'],rr))
A=get('JO-SU-40');G=get('GateOnly');T=get('AdaptiveSense+TrustLog')
comparisons=f'''新最终集 SU40 相对 TrustLog：Recall {pct(T.recall)}→{pct(A.recall)}，F1 {pct(T.f1)}→{pct(A.f1)}，采样 {(A.samples/T.samples-1)*100:+.2f}%，字节 {(A.binary_v1_bytes/T.binary_v1_bytes-1)*100:+.2f}%。相对 GateOnly：Recall差 {(A.recall-G.recall)*100:+.2f}pp，F1差 {(A.f1-G.f1)*100:+.2f}pp（95%CI {cis('JO-SU-40','GateOnly')}），采样 {(A.samples/G.samples-1)*100:+.2f}%，诱发误报 {integer(G.fault_induced_false)}→{integer(A.fault_induced_false)}。这不是任务提示中的历史SU结果。'''
text=f'''# TAIS 论文证据入口与完整实验报告

研究问题：故障健康信息、实际可见采样与通信规则怎样影响环境事件报告、采样/字节成本及接收端年龄？论文定位为**单节点双通道仿真系统研究**，不预设 TAIS 优于独立方法。

基准8b991530b77a3c7197bb998f0f4b49c1405ed96c；最终测试前冻结提交[{manifest['source_commit']}](https://github.com/Sver0411/TAIS/commit/{manifest['source_commit']})；本轮分支 research/tais-paper-evaluation，不合并main。历史算法、历史结果及上游子模块只读；仅README增加入口。

## 真实执行范围

开发600–609：36,900评分运行。最终610–629：{manifest['runs']:,}评分运行，20个种子×全部45场景。每个种子/场景有53个native方法版本和29个common调度视图。方法版本包括功能明确不同的公共组件版本，**不是82种独立算法**。每个操作点600个真实合成事件；无事件场景Recall为N/A。

实现：固定5/10/20/30/40/60严格复用旧replay；Delta为相邻变化/速率触发，Variance为带时间戳EWMA方差，Rao-inspired为4点趋势预测阈值穿越。后者不含CS、APDT和双预测，**无文献忠实复现成功主张**。原生独立方法不含健康诊断；+C11只外挂原始诊断不门控；+C11+U是明确公共TAIS上传消融。common保留各自实际采样时刻，统一检测器+C11记录+每采样上传，只隔离调度贡献。

源观测→到期采样→实际检测→上传决定→完整Binaryv1→独立解码→接收边沿评分。见[架构与论文](../papers/tais/manuscript.tex)、[冻结协议](TAIS_PAPER_PROTOCOL.md)、[配置](../configs/tais-paper.json)、[操作点](../results/tais-paper/operating-points.json)。

## 独立基线和TAIS实际结果

{comparisons}

{main}

这是代表性表；[全部82个方法/视图汇总](../results/tais-paper/summary.csv)和[全部场景/故障/关系/事件长度分组](../results/tais-paper/test/analysis/summary.csv)保留原生曲线、无健康小载荷版本、U消融及所有不利结果。主表中AS无健康，功能不等价；其他+C11版本使用相同健康字段和v1布局。

## 相近采样预算

仅用开发数据选择。首轮仅cap搜索全部失败，完整保留[失败校准](../results/tais-paper/budget-development/metrics.csv)和[旧操作点](../results/tais-paper/cap-only-operating-points.json)。测试前披露后续最小采样间隔搜索，并保留native最低5秒的原生曲线。预算点是有明确间隔约束的外部算法，不修改TAIS冻结点。表中差值始终为目标TAIS减独立对手；只有实际±5%以内可称近似匹配，不能称严格等预算。

{chr(10).join(budget_tables)}

[逐项预算核验](../results/tais-paper/test/analysis/budget_comparisons.csv)；[全种子配对区间](../results/tais-paper/test/analysis/paired_intervals.csv)。检验单元为随机种子，5000次配对bootstrap；区间为同生成器内描述性分析，多重对照不代表全局优效证明。

## 图表

![原生操作点](../results/tais-paper/test/analysis/native_tradeoffs.png)

![统一检测器的调度隔离](../results/tais-paper/test/analysis/common_tradeoffs.png)

四类图均实际生成：Recall—Samples、F1—Samples、F1—Binary bytes、故障诱发误报—Samples。图示离散点，不平滑、不插值。数字来自真实运行，不将历史SU统计冒充本轮结果。

## 创新性、资源与局限

见[逐篇相关工作与贡献边界](PAPER_NOVELTY_AND_RELATED_WORK.md)。可主张可复现集成、分层公平评估、明确操作点和失败边界；自适应采样、C11健康规则、公共ChangeAnalyzer、deadband、Stateless编码、共同优化概念均有先例或是已有组件。不存在全新通用最优算法的证明。

[资源模型](TAIS_RESOURCE_COST_MODEL.md)只采用实测软件计数和无量纲参数敏感性，未赋予假定焦耳数，计算额外开销未知。字节下降不能等比例转换为无线能耗下降。![条件成本](../results/tais-paper/test/analysis/resource_sensitivity.png)

无采样覆盖的事件不可见；同通道完全遮蔽不能恢复；稳定偏移与缓慢环境变化存在歧义；额外采样可增加误报；减少上传会提高普通数据年龄。没有自然故障真值、真实农业事件效果、真实无线链路、电流或电池寿命实验。所有主结果来自同一个合成生成器，不能称真实数据泛化。历史H层和均衡替代NO-GO保持原结论。

## 论文及核验

- [英文LaTeX初稿](../papers/tais/manuscript.tex)、[PDF](../papers/tais/manuscript.pdf)、[BibTeX](../papers/tais/references.bib)、[编译与复现说明](../papers/tais/README.md)。
- [中文概要与成熟度](TAIS_PAPER_SUMMARY_ZH.md)、[审稿人质量审查](TAIS_PAPER_QUALITY_REVIEW.md)。
- [表格数据核验](../papers/tais/tables/data_audit.csv)、[数据来源说明](../results/tais-paper/DATA.md)、[结果指纹manifest](../results/tais-paper/test/manifest.json)、[核验报告](../results/tais-paper/checks/verification-test.json)。完整逐帧/信号归档保存在ignored results/traces/tais-paper，可确定性重建。

```sh
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-build-isolation
python -m pytest -q
python scripts/verify_paper.py
python scripts/reproduce_paper.py --output results/scratch/paper-reproduction-01 --workers 4
python scripts/build_paper.py
cd papers/tais && tectonic manuscript.tex --keep-logs
```

完整复现拒绝覆盖现有目录，不重新调参，要求最终逐运行metrics精确指纹一致。首次需C11编译器；TeX首次构建可下载依赖。CI执行全套原回归、独立基线单元测试、已提交证据核验和新的端到端smoke，不在CI内重复耗时的全20种子测试。正式测试运行、图表、原生/接收端指标均已保存。
'''
(ROOT/'docs/TAIS_PAPER_EVIDENCE.md').write_text(text)
short=[]
for m in ['GateOnly','JO-SU-20','JO-SU-40','Delta-budget-SU40+C11','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']:
 r=get(m);short.append([m,pct(r.recall),pct(r.f1),integer(r.samples),integer(r.binary_v1_bytes),integer(r.fault_induced_false),pct(get(m,'profile:short').recall)])
zh=f'''# TAIS 中文论文概要

英文题目：Trust-Aware Adaptive Sampling and Communication for Resource-Constrained IoT Monitoring: A Simulation-Based Evaluation。

## 研究问题与证据

在传感器故障与真实环境变化可能混淆的情况下，集成健康信息、事件感知采样和完整状态上传，能取得怎样的质量/资源/数据年龄权衡？全部主实验为合成仿真，20个新种子×45场景，不能冒充自然故障现场或真实无线验证。

研究贡献应定位为可运行集成、可复现系统比较和设计边界分析。不能把已有C11、ChangeAnalyzer、deadband、stateless编码或共同优化概念写成本文原创算法。

## 实际结果

{comparisons}

{table(['方法','Recall','F1','采样','字节','诱发误报','短事件Recall'],short)}

独立预算结果全部见[证据报告](TAIS_PAPER_EVIDENCE.md)；原生与统一检测器视图不同，不能将检测门控的收益误归给采样。接收端指标独立解码得到，不用发送端内部状态代替。

## 不能写进摘要的说法

- “TAIS全面优于独立算法/相同预算下普遍最优”：本轮数据不支持普遍命题，实际匹配与不利对照必须逐一说明。
- “首次提出自适应采样/健康诊断/联合采样通信/新压缩理论”：已有研究及外部组件不允许该主张。
- “字节减少X%，实际电耗也下降X%”或“电池寿命已提高”：没有电流、无线状态或能耗系数测量。
- “真实温室故障诊断及短事件效果已验证”：本轮无外部真实效能数据。
- “忠实复现Rao完整算法”：实际为明确Inspired工程简化，保留了所有差异说明。
- “已通过同行评审、保证SCI录用”：这是未投稿初稿。

## 成熟度判断

**B：完整初稿和可复现独立基线已完成，仍建议补充关键实验。** 最需要的是第二个独立定义的信号/故障生成族（扩大事件时序和参数分布），以及一个适用单节点场景的文献忠实复现。若目标包含实际节能或部署结论，还必须另外补真实节点/链路/电流实验。当前主张适合仿真系统研究、应用型IoT设计权衡、可复现性短论文/研讨会类别的初步选题；不支持以全新检测算法或广泛真实环境优效为卖点。具体venue尚未筛选，不能据此保证录用。

主要局限：同生成器、温度单通道注故障、短事件采样盲区、稳定偏移/漂移不可辨识、无自然真值、无真实无线/功率、Inspired实现差异、开发集搜索和多重比较。

## 交付入口

[英文源码](../papers/tais/manuscript.tex)、[PDF](../papers/tais/manuscript.pdf)、[参考文献](../papers/tais/references.bib)、[质量审查](TAIS_PAPER_QUALITY_REVIEW.md)、[一键复现](../scripts/reproduce_paper.py)。八篇论文的DOI注册元数据逐项归档，Rao方法全文已读；部分其他论文仅能依据公开摘要/方法信息，不宣称全部完整复现。
'''
near=[]
for _,r in b[b['view']=='native'].iterrows():
    near.append(f"- {r.target} 对 {r.method}：实际采样差 {r.test_gap*100:+.2f}%，{'符合近似匹配' if r.within_5pct else '不符合近似匹配，不能称相同预算'}；TAIS−对手F1 {(r.target_f1-r.f1)*100:+.2f}pp，95%CI {cis(r.target,r.method)}。")
zh=zh.replace('## 不能写进摘要的说法','## 相近预算的实际结论\n\n'+'\n'.join(near)+'\n\nGateOnly预算下Rao-inspired质量更高，而SU40预算下只对Variance的F1差区间完全大于零；不支持“普遍优于独立方法”。\n\n## 不能写进摘要的说法')
(ROOT/'docs/TAIS_PAPER_SUMMARY_ZH.md').write_text(zh)
print('generated evidence report and Chinese summary')

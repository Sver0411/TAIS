#!/usr/bin/env python3
"""Incremental G2 entry/summary/reviewer conclusions, literal results preserved."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/tais-transfer'
d=pd.read_csv(OUT/'summary.csv').set_index('method');ci=pd.read_csv(OUT/'test/analysis/paired_intervals.csv');ev=pd.read_csv(OUT/'test/analysis/events_grouped.csv')
def pct(x):return f'{100*x:.2f}%'
def interval(a,b,k='f1'):
    r=ci[(ci.A==a)&(ci.B==b)&(ci.group=='overall')&(ci.metric==k)].iloc[0];return f'[{100*r.ci95_low:+.2f}, {100*r.ci95_high:+.2f}] pp'
def er(m,g,k='recall'):return ev[(ev.method==m)&(ev.group==g)].iloc[0][k]
su=d.loc['JO-SU-40'];high=d.loc['JO-SU-20'];var=d.loc['Variance-budget-SU40+C11'];fix=d.loc['Fixed-20+C11'];gate=d.loc['GateOnly'];trust=d.loc['AdaptiveSense+TrustLog']
review=f'''**最终判断：B——论文完整，但部分结果不稳健。** 第二生成器改变了值得发表的理由：G1中“SU40在近似预算下对Variance具有F1优势”不能推广到G2；应改为可复现的有条件系统权衡、竞争基线和失败边界研究。G2中SU40 F1为{pct(su.f1)}，Variance为{pct(var.f1)}，实际采样差{100*(var.samples/su.samples-1):+.2f}%，SU40−Variance F1差{100*(su.f1-var.f1):+.2f}pp，95%CI {interval('JO-SU-40','Variance-budget-SU40+C11')}，包含零；Recall差的区间{interval('JO-SU-40','Variance-budget-SU40+C11','recall')}完全低于零。Fixed-20的F1为{pct(fix.f1)}，采样差{100*(fix.samples/su.samples-1):+.2f}%，也不支持SU40等采样质量优越（固定点未预声明配对区间，此处是描述性比较）。

SU40相对GateOnly的F1差区间{interval('JO-SU-40','GateOnly')}仍支持这一生成机制内的条件改善，但增加{int(su.samples-gate.samples):,}次采样和{int(su.fault_induced_false-gate.fault_induced_false)}次诱发误报，且Recall差区间{interval('JO-SU-40','GateOnly','recall')}跨零。相对TrustLog的F1区间{interval('JO-SU-40','AdaptiveSense+TrustLog')}为正，采样增加{100*(su.samples/trust.samples-1):+.2f}%，不能延用G1中采样同时降低的说法。SU40相对Variance的字节降低{100*(1-su.binary_v1_bytes/var.binary_v1_bytes):.2f}%、诱发误报降低{100*(1-su.fault_induced_false/var.fault_induced_false):.2f}%，同时P95年龄{var.pooled_age_p95_s:.0f}→{su.pooled_age_p95_s:.0f}s；这是资源/信息权衡，部分来自可共享的U模块。

SU20 F1/Recall为{pct(high.f1)}/{pct(high.recall)}，相对SU40采样增加{100*(high.samples/su.samples-1):.2f}%，FI {int(su.fault_induced_false)}→{int(high.fault_induced_false)}。SU20短事件Recall仅{pct(er('JO-SU-20','duration:short'))}，虽然覆盖率达{pct(er('JO-SU-20','duration:short','coverage'))}；SU40短事件Recall {pct(er('JO-SU-40','duration:short'))}还低于GateOnly {pct(er('GateOnly','duration:short'))}。全支持被替换的{int(ev[(ev.method=='JO-SU-40')&(ev.group=='fully_overwritten')].iloc[0].events)}个事件在Gate/SU20/SU40中均未检出。稳定偏移无专用类型位，温湿度也不应被假定同等诊断效果。

该研究仍有可考虑投稿的内容：端到端可复现、真正独立调度基线、完整字段通信与独立接收端审计，以及跨机制负面证据。不能以新检测理论、普遍优效、真实田间泛化或实际节能为卖点。保持Simulation-Based Evaluation标题和系统权衡贡献定位；进入作者/单位、篇幅、目标格式与投稿叙事定稿即可。本轮计划内补充实验结束，不建议继续围绕测试结果优化算法或追加生成器选择。具体venue尚未筛选，不承诺审稿结果。'''
p=ROOT/'docs/TAIS_CROSS_GENERATOR_REPORT.md';s=p.read_text();marker='<!-- REVIEW_CONCLUSION -->';s=s.replace(marker,'<!-- REVIEW_START -->\n'+review+'\n<!-- REVIEW_END -->');p.write_text(s)
# Current synopsis: attach the G2 supplement, preserving the complete G1 text.
headers='| 方法 | P | R | F1 | FI | 采样 | 上传 | Binary字节 | Age P95/max(s) |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |'
methods=['AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-SU-20','JO-SU-40','Fixed-20+C11','Fixed-40+C11','Delta-budget-SU40+C11','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']
table=headers+'\n'+'\n'.join('| '+' | '.join([m,pct(d.loc[m,'precision']),pct(d.loc[m,'recall']),pct(d.loc[m,'f1']),f"{d.loc[m,'fault_induced_false']:,.0f}",f"{d.loc[m,'samples']:,.0f}",f"{d.loc[m,'uploads']:,.0f}",f"{d.loc[m,'binary_v1_bytes']:,.0f}",f"{d.loc[m,'pooled_age_p95_s']:.0f}/{d.loc[m,'pooled_age_max_s']:.0f}"])+' |' for m in methods)
block=f'''## 最新：第二生成机制冻结迁移（G2）

新分支`research/tais-cross-generator-validation`，冻结提交`3f3991aa26cf`。14个冻结方法×46场景×20个未用种子（700–719）已全部运行，未重新调参。G2采用分段均值回归背景、AR(1)/时变/重尾噪声、12–240秒多形状事件和双通道七类故障；事件与故障独立计时。完整支持真值区别于G1的内区间标签，两套实验分别汇总，不能合并成真实泛化样本。

{table}

{review}

[完整G2报告](TAIS_CROSS_GENERATOR_REPORT.md) · [冻结协议](TAIS_CROSS_GENERATOR_PROTOCOL.md) · [全部14方法及分组](../results/tais-transfer/summary.csv) · [对比图](../results/tais-transfer/figures/quality_comparison.png) · [当前英文稿](../papers/tais/manuscript.tex)。一键复现：`.venv/bin/python scripts/reproduce_transfer.py --workers 4`。旧12页G1稿已保存于`papers/tais/history`；原始G1结果不变。下方保留的旧结果与开发/预算结论均专指G1。
'''
def insert(path,block):
    p=ROOT/path;s=p.read_text();start='<!-- TRANSFER_CURRENT_START -->';end='<!-- TRANSFER_CURRENT_END -->'
    if start in s:s=s.split(start)[0]+s.split(end,1)[1]
    head,tail=s.split('\n',1);p.write_text(head+'\n\n'+start+'\n'+block+'\n'+end+'\n'+tail)
insert('docs/TAIS_PAPER_SUMMARY_ZH.md',block)
insert('docs/TAIS_PAPER_EVIDENCE.md',block)
# Remove obsolete prospective advice while retaining old result numbers and audit rows.
p=ROOT/'docs/TAIS_PAPER_SUMMARY_ZH.md';s=p.read_text();s=s.replace('## 成熟度判断','## G1阶段成熟度判断（历史）');s=s.replace('最需要的是第二个独立定义的信号/故障生成族（扩大事件时序和参数分布），以及一个适用单节点场景的文献忠实复现。','当时指出第二个独立生成族与忠实文献复现的不足。前者已在上述G2完成，后者仍需限制比较主张，当前不再将新增算法或生成器实验作为本计划的下一步。');p.write_text(s)
p=ROOT/'docs/TAIS_PAPER_QUALITY_REVIEW.md';s=p.read_text();s=s.replace('Judgment: **B — draft/evidence complete, key external-validity experiments still recommended.**','Current judgment: **B — complete manuscript; important quality gains are distribution-dependent.**')
s=s.replace('Remaining submission weaknesses: a single synthetic family with narrow temporal geometry, temperature-only fault injection, detector sharing, lack of a faithful applicable literature-method reproduction, no natural annotated field data, no MCU or wireless energy measurements. A second independently specified generator and a reproducible suitable paper algorithm would be the most direct additions for a stronger comparative submission. Hardware experiments are necessary only for hardware/energy claims, which the present paper does not make.', 'The completed G2 supplement addresses single-generator and temperature-only coverage without establishing field validity. Remaining weaknesses are two project-defined mechanisms with different truth geometry, shared detector components, an inspired rather than faithful literature implementation, no natural annotated field data, and no MCU/wireless energy measurements. The present planned experiments are complete. The next work is manuscript/venue preparation with appropriately restricted claims, rather than post-test optimization or another generator-selection cycle. Hardware claims remain unsupported and are excluded.')
p.write_text(s)
insert('docs/TAIS_PAPER_QUALITY_REVIEW.md','## Final cross-generator reviewer audit\n\n'+review+'\n\n- All fourteen methods/all46 cases retained; no test-set adjustment.\n- The near-budget Variance reversal and stronger Fixed20 quality are explicit in abstract/results/discussion.\n- G2 budget gaps requalified, correct-type health separated, sender/decoded receiver and missed clears audited.\n- Original G1 tables/results and historical NO-GO conclusions remain unchanged; G1-only paper archived.\n- New numerical cells have a separate CSV audit; all eight existing DOI records remain verified.\n- Actual compilation/rendering and CI evidence are under results/tais-transfer/checks; author/affiliation placeholder remains explicit.')
print('Updated current evidence/Chinese synopsis/reviewer audit from CSVs')

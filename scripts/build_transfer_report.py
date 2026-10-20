#!/usr/bin/env python3
"""Chinese evidence report generated from G2 CSVs; no hand-entered outcomes."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/tais-transfer'
def main():
    d=pd.read_csv(OUT/'summary.csv').set_index('method');groups=pd.read_csv(OUT/'test/analysis/summary.csv');events=pd.read_csv(OUT/'test/analysis/events_grouped.csv');ci=pd.read_csv(OUT/'test/analysis/paired_intervals.csv');budget=pd.read_csv(OUT/'test/analysis/budget_comparisons.csv');diag=pd.read_csv(OUT/'test/analysis/fault_diagnostics.csv');directions=pd.read_csv(OUT/'test/analysis/cross_generator_directions.csv')
    methods=d.index.tolist();lines=[]
    def add(s=''):lines.append(s)
    def pct(v):return 'N/A' if pd.isna(v) else f'{100*v:.2f}%'
    def integer(v):return f'{v:,.0f}'
    def number(v):return 'N/A' if pd.isna(v) else f'{v:.2f}'
    def table(headers,rows):
        add('| '+' | '.join(headers)+' |');add('| '+' | '.join(['---']*len(headers))+' |')
        for r in rows:add('| '+' | '.join(map(str,r))+' |')
        add()
    add('# TAIS 第二生成机制与冻结策略迁移报告');add()
    add('## 1. 目的、冻结与执行范围');add()
    add('检验已有策略在不同信号形成机制下的可迁移收益和分布依赖。两套机制都由本项目定义，因此这是跨生成机制压力测试，不能称为真实农业或外部自然故障验证。基准0170196；生成器/参数/评分/分析冻结提交3f3991aa26cf1ac7f8f8cd0fe188136b0311c9bd，正式种子700–719，工程种子690/691。全部14方法×46场景×20种子=12,880次正式系统运行，所有实例和失败均保留。无测试后调参或再校准。')
    add();add('## 2. 机制、真值与旧环境区别');add()
    table(['环节','G1（保留）','G2（本轮）'],[
        ['背景','固定小振幅正弦','随机分段目标的均值回归，两通道相关性分段变化'],['噪声','独立高斯','AR(1)、分段强度、少量t3重尾扰动'],['环境事件','固定梯形/26或180秒，故障后固定延迟','step/recovery、smooth、asymmetric三形状；12–240秒；与故障独立的随机时刻'],['故障','温度、固定剖面','温/湿度均有七类故障、随机时长/强度/正负/恢复；漂移分段斜率'],['真值','原有物理幅度内区间标签','完整外生物理支持区间；不读取检测器输出'],['场景','45场景，600事件/方法','46场景，包含多事件及双通道clean，完整事件数见下表'],['参数','G1开发选择','全部直接转移，Rao仍为24°C/45%RH中心'],['统计','20个610–629种子，独立汇总','20个700–719种子，独立汇总；不合并显著性']])
    add('完整生成方程、所有参数、场景矩阵与预声明示例见[冻结协议](TAIS_CROSS_GENERATOR_PROTOCOL.md)和[配置](../configs/tais-transfer.json)。G2没有调用G1生成过程；仅复用Trace/Fault和冻结评分接口。环境、噪声、事件族、故障通道使用SHA256派生独立随机流。按故障类型比较时保持同一无故障序列；counterfactual直接复制noisy而不重新生成，缓存键包含完整序列和真值哈希。在线接口只暴露observed，隐藏中心/日程/标签不可见。');add()
    add('物理区间[start,end)与评分[start,end−1]、采样覆盖和接收报告时间分别保存。与G1标签几何差异明确，不把两套绝对Recall当作相同任务。实际前后/重叠关系由独立日程分类，不按算法表现筛选。替换故障的完全遮蔽组保留；“fully_overwritten”描述动态支持被替换，卡死起点可能仍包含已有物理信息，不能把偶然容差命中写成恢复了被删除真值。');add()
    add('## 3. 全部主要方法与资源');add()
    table(['方法','P','R','F1','Rx F1','TP/FP/FN','FI','采样','上传','Binary v1字节','B/Tx','Age均值/P95/max(s)'],[[m,pct(r.precision),pct(r.recall),pct(r.f1),pct(r.rx_f1),f'{int(r.tp)}/{int(r.false_reports)}/{int(r.missed)}',integer(r.fault_induced_false),integer(r.samples),integer(r.uploads),integer(r.binary_v1_bytes),f'{r.average_upload_bytes:.2f}',f'{r.age_mean_s:.2f}/{r.pooled_age_p95_s:.0f}/{r.pooled_age_max_s:.0f}'] for m,r in d.iterrows()])
    add('P/R/F1为sender-on-upload；Rx为实际Binary v1解码后false→true边沿独立评分。所有独立方法均显式+C11，诊断只记录、不门控策略。每次实际编码的len之和是字节指标，没有用JSON估计，没有删健康/时间戳/null/事件字段。来源为[summary.csv](../results/tais-transfer/summary.csv)；所有本地、发送、接收计数见[完整分组](../results/tais-transfer/test/analysis/summary.csv)。');add()
    table(['方法','Receiver TP/FP/FN','事件/健康边沿遗漏','事件/健康最大已送延迟(s)','条件事件延迟 sender/rx(s)'],[[m,f'{int(r.rx_tp)}/{int(r.rx_false_reports)}/{int(r.rx_missed)}',f'{int(r.event_edges_unreported)}/{int(r.health_edges_unreported)}',f'{r.event_edge_delay_max_s:.0f}/{r.health_edge_delay_max_s:.0f}',f'{r.event_delay_s:.2f}/{r.rx_event_delay_s:.2f}'] for m,r in d.iterrows()])
    add('延迟仅对命中事件条件化；所有miss均在FN/Recall保留。[共同命中延迟差](../results/tais-transfer/test/analysis/common_event_delays.csv)避免把不同命中子集直接解释为更快。');add()
    add('## 4. 采样预算和配对不确定性');add()
    table(['独立预算点','实际采样','SU40采样','实际差','±5%内','F1','SU40 F1'],[[r.method,integer(r.samples),integer(r.target_samples),f'{r.relative_gap*100:+.2f}%',r.within_5pct,pct(r.f1),pct(r.target_f1)] for _,r in budget.iterrows()])
    add('预算名称只标明G1开发选择目标，不保证G2预算匹配。超出±5%不得声称等预算。');add()
    table(['固定+C11','相对SU40实际采样差','±5%内','F1','SU40−固定F1（描述性）'],[[m,f"{100*(d.loc[m,'samples']/d.loc['JO-SU-40','samples']-1):+.2f}%",abs(d.loc[m,'samples']/d.loc['JO-SU-40','samples']-1)<=.05,pct(d.loc[m,'f1']),f"{100*(d.loc['JO-SU-40','f1']-d.loc[m,'f1']):+.2f}pp"] for m in [f'Fixed-{p}+C11' for p in [5,10,20,30,40,60]]])
    add('固定点比较保留全部周期，不只列对TAIS有利的点；固定点未预声明配对区间，此处不额外宣称推断性优效。');add()
    table(['A−B','指标','差值','种子配对95%CI'],[[r.A+' − '+r.B,r.metric,f'{r.difference*(100 if r.metric in ["precision","recall","f1","rx_f1"] else 1):+.2f}'+('pp' if r.metric in ['precision','recall','f1','rx_f1'] else ''),f'[{r.ci95_low*(100 if r.metric in ["precision","recall","f1","rx_f1"] else 1):+.2f}, {r.ci95_high*(100 if r.metric in ["precision","recall","f1","rx_f1"] else 1):+.2f}]'] for _,r in ci[(ci.group=='overall')&ci.metric.isin(['recall','f1','samples','binary_v1_bytes','fault_induced_false'])].iterrows()])
    add('5,000次配对bootstrap以整个种子为簇，保留同种子全部场景；不是按秒独立抽样。区间为描述性，未对多重比较建立全局优效检验。');add()
    add('## 5. 跨生成器方向、边界与失败');add()
    table(['A−B','指标','G1差','G2差','方向'],[[r.A+' − '+r.B,r.metric,f'{r.g1_difference*(100 if r.metric in ["recall","f1"] else 1):+.2f}'+('pp' if r.metric in ['recall','f1'] else ''),f'{r.g2_difference*(100 if r.metric in ["recall","f1"] else 1):+.2f}'+('pp' if r.metric in ['recall','f1'] else ''),r.direction] for _,r in directions.iterrows()])
    add('计数差是各自生成器内部总差；场景/事件组成不同，不能用两套总数之比宣称跨环境资源收益。');add()
    selected=['AdaptiveSense+TrustLog','GateOnly','JO-SU-20','JO-SU-40','Delta-budget-SU40+C11','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']
    table(['方法','事件组','n','Recall','覆盖率','有覆盖时成功率','Rx Recall'],[[r.method,r.group,int(r.events),pct(r.recall),pct(r.coverage),pct(r.covered_success),pct(r.rx_recall)] for _,r in events[(events.method.isin(selected))&events.group.isin(['duration:short','duration:medium','duration:long','fully_overwritten','no_sample_coverage'])].iterrows()])
    table(['方法','故障通道组','Recall','F1','FI','任意标志检出'],[[r.method,r.group,pct(r.recall),pct(r.f1),integer(r.fault_induced_false),pct(r.fault_detection_rate)] for _,r in groups[(groups.method.isin(selected))&groups.group.isin(['fault_channel:temperature','fault_channel:humidity','fault:stable_offset','fault:drift','relation:same','relation:cross','no_events'])].iterrows()])
    add('无事件组Recall=N/A，保留环境误报。未故障通道的错误报告也保存在完整汇总no_fault_channel_false_*字段，不只展示故障通道。');add()
    table(['SU40故障','通道','episodes','任意标志率','对应类型率','任意/类型条件延迟(s)'],[[r.kind,r.channel,int(r.episodes),pct(r.any_detection_rate),pct(r.type_detection_rate),number(r.any_delay_s)+'/'+number(r.type_delay_s)] for _,r in diag[diag.method=='JO-SU-40'].iterrows()])
    add('stable_offset没有C11类型位，类型率N/A，任何其他标志不能算对应类型成功。missing/invalid同用既有invalid bit16，不声称二者可被C11区分。各方法的完整健康诊断见[fault_diagnostics.csv](../results/tais-transfer/test/analysis/fault_diagnostics.csv)，原始每故障检出/延迟见[faults.csv](../results/tais-transfer/test/faults.csv)。');add()
    add('## 6. 图表、原创性与资源解释');add()
    for file,caption in [('generator_traces.png','预声明输入示例'),('fault_timelines.png','故障与事件日程'),('quality_comparison.png','分生成器Recall/F1'),('tradeoffs.png','离散质量/采样/字节/FI操作点'),('fault_false_reports.png','故障类型诱发误报/运行'),('duration_recall.png','实际持续时间分组Recall')]:add(f'![{caption}](../results/tais-transfer/figures/{file})');add()
    add('第二机制增加的是可审计压力覆盖和对结论分布依赖的检验，不是一个新检测算法。C11、ChangeAnalyzer、deadband、二进制协议和采样通信协调均已有先例；原有[相关工作](PAPER_NOVELTY_AND_RELATED_WORK.md)八项核实文献保持不变。可主张可运行系统集成、独立对照、透明反事实/接收端测量和结构性边界的复现证据。');add()
    add('采样、上传、Binary字节是实测软件计数。没有新硬件能耗系数；原有条件模型仅在给定权重及处理成本假设下成立。本地理想字节链路不测无线空中时间、重传、MCU RAM/时间、电流或电池寿命，不能把字节百分比等同电能百分比。');add()
    add('## 7. 最终研究判断与论文状态');add()
    add('判断和对投稿理由的影响见下列人工复审结论；它必须与以上真实CSV和配对区间一致。论文增量保留G1并单列G2方法/结果/预算/讨论/限制，旧12页稿在papers/tais/history和基准Git提交保存。');add()
    add('<!-- REVIEW_CONCLUSION -->');add()
    add('主要局限仍包括：两套本项目定义的合成机制、外生标签几何差异、共享基础检测器、仅Inspired文献适配、无自然故障或农业现场效果、无真实无线和功率测量。事件落在采样间隔、完全替换、稳定偏移与慢变化歧义仍是结构性限制。此次是计划内最后补充实验，后续应限缩主张、整理作者/单位和投稿格式，不再追加算法优化或生成器选择循环。');add()
    add('## 8. 复现与证据');add()
    add('```sh\n.venv/bin/python scripts/reproduce_transfer.py --workers 4\n.venv/bin/python scripts/transfer_figures.py\n.venv/bin/python scripts/build_paper.py\ncd papers/tais\ntectonic manuscript.tex --keep-logs\n```');add()
    add('完整复现使用新scratch目录，核对每个CSV逐字节相等；不会覆盖正式结果或重新调参。只检查提交材料可加--check-only。新源码、配置、协议、运行清单、结果、数据审计、PDF检查及CI位于本分支。原G1结果目录保持逐文件只读；旧验证器仅调整对新增G2模块的文件清单处理，不变更旧算法、旧评分或锁定文件哈希。')
    target=ROOT/'docs/TAIS_CROSS_GENERATOR_REPORT.md'
    # Keep a manually reviewed, result-dependent conclusion across rebuilds.
    old=target.read_text() if target.exists() else '';marker='<!-- REVIEW_CONCLUSION -->'
    if '<!-- REVIEW_START -->' in old:
        conclusion=old.split('<!-- REVIEW_START -->',1)[1].split('<!-- REVIEW_END -->',1)[0]
        text='\n'.join(lines).replace(marker,'<!-- REVIEW_START -->'+conclusion+'<!-- REVIEW_END -->')
    else:text='\n'.join(lines)
    target.write_text(text+'\n');print('Generated evidence report from actual CSVs')
if __name__=='__main__':main()

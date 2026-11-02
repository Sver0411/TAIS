#!/usr/bin/env python3
"""Audience-neutral public Phase4 results from verified saved tables only.

Personalized reports and their templates must be authored outside Git.
"""
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from benchmark_phase4 import ROOT,OUT
from verify_phase4 import verify


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(str(v) for v in row)+' |' for row in rows])


def main():
    verify(OUT)
    analysis=OUT/'test/analysis';summary=pd.read_csv(analysis/'summary.csv');s=summary[summary.group_type=='overall'].set_index('method')
    effects=pd.read_csv(analysis/'paired_effects.csv');gates=pd.read_csv(analysis/'default_gates.csv')
    raw=pd.read_csv(OUT/'test/metrics.csv');ev=pd.read_csv(OUT/'test/events.csv');fr=pd.read_csv(OUT/'test/forensics.csv.gz')
    main_methods=['A0','A1','A2','A3','A4','A5','A6','A7','Fixed-5','Fixed-20','Fixed-60',
                  'Delta-budget-SU40','Variance-budget-SU40','GateOnly','JO-SU-20','JO-SU-40']
    main_methods += [f'{kind}-T{t}-U{u}' for kind in ['Robust','Risk'] for t in (0,1) for u in (0,1)]
    all_table=table(['Method','P %','Recall %','F1 %','Rx F1 %','TP/FP/FN','Samples','Messages','Binaryv1 bytes','FI'],
                    [[m,f'{100*s.loc[m,"precision"]:.2f}',f'{100*s.loc[m,"recall"]:.2f}',f'{100*s.loc[m,"f1"]:.2f}',
                      f'{100*s.loc[m,"receiver_f1"]:.2f}',f'{int(s.loc[m,"tp"])}/{int(s.loc[m,"fp"])}/{int(s.loc[m,"fn"])}',
                      f'{int(s.loc[m,"samples"]):,}',f'{int(s.loc[m,"uploads"]):,}',f'{int(s.loc[m,"bytes"]):,}',
                      int(s.loc[m,'fault_induced_false'])] for m in main_methods])
    focus=['A5','A7','Robust-T1-U1','Risk-T1-U1','Fixed-20','JO-SU-20','JO-SU-40']
    opportunity=table(['Method','Pre-onset coverage %','Finite event coverage %','First sample delay s','Fast gap share %','Maximum fast/120s','Fast samples outside truth','Mean actual interval s'],
                      [[m,f'{100*s.loc[m,"precoverage"]:.2f}',f'{100*s.loc[m,"finite_event_coverage"]:.2f}',
                        f'{s.loc[m,"first_observation_delay_s"]:.2f}',f'{100*s.loc[m,"fast_share"]:.2f}',int(s.loc[m,'fast_window_max']),
                        int(s.loc[m,'fast_outside']),f'{s.loc[m,"mean_interval_s"]:.2f}'] for m in focus])
    timing=table(['Method','Detected delay mean/median/P95 s','Restricted loss s (all events)','Finite value age mean s','Mean run P95 age s'],
                 [[m,f'{s.loc[m,"delay_mean_s"]:.2f}/{s.loc[m,"delay_median_s"]:.2f}/{s.loc[m,"delay_p95_s"]:.2f}',
                   f'{s.loc[m,"restricted_delay_s"]:.2f}',f'{s.loc[m,"finite_age_mean_s"]:.2f}',f'{s.loc[m,"mean_run_p95_age_s"]:.2f}'] for m in focus])
    comparisons=effects[(effects.method.isin(['Robust-T1-U1','Risk-T1-U1'])) &
                        (effects.reference.isin(['A5','A7','Robust-T1-U1','Robust-T0-U1','Risk-T0-U1'])) &
                        effects.metric.isin(['f1','recall','samples','precoverage','fast_outside','fault_induced_false'])]
    stats=table(['Method - reference','Endpoint','Mean seed difference','95% descriptive CI','Holm p'],
                [[r.method+' - '+r.reference,r.metric,
                  f'{r.mean_seed_difference*(100 if r.metric in ("f1","recall","precoverage") else 1):+.3f}'+(' pp' if r.metric in ('f1','recall','precoverage') else ''),
                  f'[{r.ci95_low*(100 if r.metric in ("f1","recall","precoverage") else 1):+.3f},{r.ci95_high*(100 if r.metric in ("f1","recall","precoverage") else 1):+.3f}]',f'{r.p_holm:.4f}']
                 for r in comparisons.itertuples(index=False)])
    gate_table=table(['Candidate','Gate','Estimate','95% CI','Required bound','Pass'],
                     [[r.method,r.gate,f'{r.estimate:.4f}',f'[{r.ci95_low:.4f},{r.ci95_high:.4f}]' if pd.notna(r.ci95_low) else 'deterministic',
                       str(r.direction)+' '+str(r.criterion),str(bool(r.passed))] for r in gates.itertuples(index=False)])
    selected=summary[(summary.group_type=='scenario')&summary.group.isin(['low_frequency','high_frequency','slow_change','noisy_none','noisy_events','multi_range','multi_stuck','multi_drift'])&summary.method.isin(focus[:4])]
    groups=table(['Scenario','Method','Recall %','F1 %','FP','Samples','Fast outside truth'],
                 [[r.group,r.method,f'{100*r.recall:.2f}' if pd.notna(r.recall) else 'N/A',f'{100*r.f1:.2f}' if pd.notna(r.f1) else 'N/A',
                   int(r.fp),int(r.samples),int(r.fast_outside)] for r in selected.itertuples(index=False)])
    same=ev[(ev.side=='sender')&ev.same_fault_overlap]
    same_table=table(['Method','Actually overlapping same-channel events','TP','FN','Recall %'],
                     [[m,len(same[same.method==m]),int(same[same.method==m].matched.sum()),
                       int((~same[same.method==m].matched).sum()),f'{100*same[same.method==m].matched.mean():.2f}'] for m in focus[:4]])
    verdict='；'.join(f'{m}：{g.decision.iloc[0]}' for m,g in gates.groupby('method'))
    ranking=effects[(effects.method=='Risk-T1-U1')&(effects.reference=='Robust-T1-U1')&(effects.metric=='f1')].iloc[0]
    noisy={m:summary[(summary.group_type=='scenario')&(summary.group=='noisy_none')&(summary.method==m)].iloc[0] for m in focus[:4]}
    answers=[]
    for kind in ['Robust','Risk']:
        m=kind+'-T1-U1'
        answers.append(f'{kind}：强噪声无事件采样相对A7变化{100*(noisy[m].samples/noisy["A7"].samples-1):+.2f}%；'
                       f'事件前覆盖率{100*s.loc[m,"precoverage"]:.2f}%（A7为{100*s.loc["A7","precoverage"]:.2f}%，A5为{100*s.loc["A5","precoverage"]:.2f}%）；'
                       f'总采样相对A5变化{100*(s.loc[m,"samples"]/s.loc["A5","samples"]-1):+.2f}%。')
    txt=f'''# TAIS Phase4：自适应采样机制研究结果

本报告面向通用项目技术评审。所有数字来自已完成的合成回放，不代表农业实机、自然故障、真实无线或能耗保证。
研究基准c71e621；新功能为独立可选路径，原始AdaptiveSense、C11、Upload、MA-1及默认策略不变。

## 1. 实际完成与历史保护

完成MA-1全部43,520条通道事件的诊断，以及两个采样候选的实现、因果/滞回/冷却/预算/缺失值/编码/模块不变量测试。
独立正式实验20种子920–939×66场景×24方法＝31,680次评分运行；每方法4,160个通道级事件，
发送与接收共199,680行事件观察和99,840行逐事件归因。工程940/941只用于实现检查。
冻结59份有效源码/配置/分析/测试/协议快照；保护台账覆盖1,521个原有文件及上游版本。

首轮诊断将部分T关闭时的公共恢复处理误归为健康暴露，已在新目录纠正。首轮工程的数字CSV字符串排序导致
时间线乱序，修复后在engineering-v2重跑；3,168行指标完全一致。两次原始工程数据、源码和失败说明均保留，
未依据工程或正式结果搜索阈值。正式开始后没有修改算法、参数、数据定义或主分析。

## 2. 机制审查与MA-1归因

现有算法已有滞回，问题不是简单“缺少双阈值”。固定噪声底上的STD/ROC可能长期高于活动边界；稳定梯级可等待60秒，
事件后高频无法恢复缺失的首次观测。C11样本窗口、公共时钟、恢复重置和EMA检测又相互影响。
MA-1 A7有647个机会不足、1,263个有限覆盖但检测失败、41个健康/重置暴露、1个确认候选受门控的漏检。
A7事件前20秒覆盖40.40%、首次采样平均延迟24.61秒；固定组为100%、10.08秒。
具体证据见[审查](PHASE4_AUDIT.md)与[逐事件诊断](../results/phase4/diagnosis-v2/events.csv)。
C_exposure只是暴露，不证明门控导致漏检；上游未记录的候选时刻保持未知，不能补造。

## 3. 两种候选与公平条件

Robust采用历史中位数/MAD、同通道同方向的采样持续性、有界5秒探测、冷却和滚动预算，静默40秒。
Risk增加过去样本拟合的稳健斜率、当前预测残差和30秒趋势风险，静默30秒、WATCH15秒。
两者最多每120秒6次实际快速采样，读取当前/过去已采集值；延迟到达的源时刻不虚耗快速名额。
新采样器的独立诊断需求20秒，原生策略仍保持其历史60秒规则。C11健康语义、检测门控和评分器没有被替换。

所有旧54场景保留；12个干净事件补充独立交叉幅度0.75/1.5、三档持续时间、噪声1/3倍。
T关闭沿用中性健康占位，T开启为原C11门控；U关闭全样本发送，U开启原Upload。U不反馈给采样/预算。
每种采样均有T/U开关，同时保留全部MA-1基线。实际资源与相同输入配对，不提供免费观测或测试后预算校准。
Risk与Robust还存在静默间隔、窗口长度等束式差异，本轮不能把全部差异独立归因于趋势预测项。

## 4. 全部方法主结果

下表为66条件合并微平均点估计；P/R/F1用相同120秒截止计分，Rx为实际解码后重建的事件边沿。
FI是操作性反事实故障诱发误报，包含同样的截止与120秒恢复归因窗口；不是物理因果识别。
应用字节是实际编码长度，非RF能耗。所有结果都保留，方法名中的旧budget不保证新样本预算相等。

{all_table}

## 5. 采样、及时性和鲜度

{opportunity}

{timing}

成功延迟条件化在检出子集上，必须同时看FN/Recall与含漏检的受限损失。漏检计120秒是评价损失，不是实际观察的延迟。
事件前覆盖严格取开始之前20秒内实际采样；开始时刻恰好采样属于后观测。有限事件覆盖和门控/阈值失败并不是同一件事。
有限接收值年龄跨null帧继续增长；新鲜的故障值也可能不正确。P95年龄为各运行P95的均值，未冒称合并源秒P95。

## 6. 配对统计与直接比较

整个随机种子是聚类单位，保留场景与通道相关性；5,000次bootstrap、20,000次双侧sign-flip，136项预声明检验统一Holm。
下表推断量是种子微平均指标的平均差，与合并F1不同。95%区间为描述性，不能只看是否跨0。
sign-flip依赖差的对称/可交换零假设，临界p还存在有限蒙特卡洛误差。所有136项及分布均可从保存的CSV重建。

{stats}

Risk−Robust的种子平均F1差为{100*ranking.mean_seed_difference:+.2f}pp，95%CI[{100*ranking.ci95_low:+.2f},{100*ranking.ci95_high:+.2f}]，
Holm p={ranking.p_holm:.4f}。这项比较不替代采样、字节、漏检和默认门槛，也不构成预测项独立有效的证明。

明确区分统计结论：两候选相对A7的F1改善有校正后支持；Risk相对Robust的F1更高也有支持，但需要更多样本和字节。
Risk相对A5的种子F1差+2.68pp、CI[−0.98,+6.37]、Holm p=1，不能宣称优于A5。
Robust相对A5的F1点估计下降、未通过非劣工程门槛；其未校正区间不跨0，但Holm p=0.875，不能写成多重校正后显著退化。
Risk中T的F1改善约+1.41pp有校正后支持，Robust中T的F1变化没有；两者操作性FI下降均有支持。

## 7. 重点问题与场景差异

{answers[0]}

{answers[1]}

高频预算与“无效高频”分别用真实间隔、窗口计数、真值外快速样本和无本地事件上升沿的快速段统计，
这些是离线操作性代理，不能把真值送入在线触发器。T的作用随采样窗口、故障类型而变，须看上述配对效应和完整故障分组。
U四对新组合的样本/健康/检测序列一致，重要已采样边沿在本理想链接条件下无遗漏；这不恢复未采集事件。

{groups}

强噪声有事件组保留一个重要代价：A7 Recall79.17%，Risk54.17%、Robust44.17%。减少高频采样同时失去了部分检出，
不能把所有高频都叫作无效开销。低频组Risk55%、Robust50%，均高于A7的40%，但低于A5的65%；这些分组只作描述。
慢变组四个代表方法主Recall均为0，Robust还产生5个FP，说明采样优化未解决固定检测器的慢变边界。

按实际时间和通道重叠而非场景名字筛选的同通道故障事件如下；不据此额外进行未预声明的显著性主张：

{same_table}

低频与缓慢事件、不同噪声、同通道/双通道故障全部保留。如果慢变仍未在期限内检出，应解释为当前检测器与标签窗口的边界，
不能把调度成功代替检测成功，也不能把期限后报告写成从未检出。原生无截止TP/FP仍在原始指标中。

## 8. 预声明默认策略门槛

结果：{verdict}。
各候选必须同时满足与A5的F1/Recall非退化、至少5%采样节省、字节/FI/鲜度/事件前覆盖约束，
噪声资源上界、相对A7的校正后F1改善、全部重要边沿与快速预算。门槛是预声明工程容差，不是经过验证的农业要求。

{gate_table}

只要有一项未通过，就不作为默认替代。即便通过也仅表示值得下一阶段独立验证，不自动改默认或证明田间可用。
本轮只实现可选Python路径；ESP32-S3还需C移植、内存/执行时间/传感器时序/电流测量和独立真实数据验证。
不能仅因新算法是本轮目标而建议进入实际监控部署。

## 9. 复现、图表与下一步

见[结果索引与一条批量/分析命令](../results/phase4/README.md)、[冻结协议](PHASE4_PROTOCOL.md)、[公式与状态图](PHASE4_ALGORITHM_DESIGN.md)。
`python scripts/analyze_phase4.py`从保存的观察表重建所有统计与12幅PNG/PDF图，不读取预测展示数据、不重跑策略。
图1/2为全方法F1/Recall资源点云，图3/4为预声明seed920实际时间线，图5覆盖率，图6快速预算，图7诊断归因，
图8条件延迟与受限损失，图9独立交叉噪声，图10可靠性交互，图11鲜度与字节，图12全方法整种子分布。

下一阶段先把首次观测机会、已覆盖但未通过EMA/持久性检测、可靠性暴露分开；在新未用种子上拆开趋势项与静默间隔的贡献。
明确应用允许的数据年龄/漏检代价，再考虑检测器的慢变机制。不能继续在920–939上调参。
上述指标不测真实无线丢包、自然故障准确率、实测能量或农作物价值；人为支持标签可早于显著物理偏移，
66条件混合不代表真实发生率。保留历史NO-GO、失败过程和全部不理想结果。
'''
    (ROOT/'docs/PHASE4_RESULTS_ZH.md').write_text(txt)
    # Frame decoding and reconstructed receiver-edge matching are different.
    # Every frame actually passed codec and CoreReceiver checks in the frozen
    # campaign. There is no assigned report frame for an unmatched truth event.
    decode=ev[ev.side=='sender'][['seed','scenario','method','channel','truth_start','report_time','matched']].copy()
    decode['assigned_report_frame_decoded']=decode.matched.map({True:True,False:None})
    rx=ev[ev.side=='receiver'][['seed','scenario','method','channel','truth_start','matched']].rename(columns={'matched':'receiver_edge_matched'})
    decode=decode.merge(rx,on=['seed','scenario','method','channel','truth_start'],validate='one_to_one')
    path=OUT/'checks/event_decode_outcomes.csv.gz';path.write_bytes(gzip.compress(decode.to_csv(index=False).encode(),mtime=0))
    bindings=dict(source_tables={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [analysis/'summary.csv',analysis/'paired_effects.csv',analysis/'default_gates.csv']},
                  report_sha256=hashlib.sha256((ROOT/'docs/PHASE4_RESULTS_ZH.md').read_bytes()).hexdigest(),
                  generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  decode_table_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  decode_scope='All assigned sender frames verified by actual frozen codec/CoreReceiver; missing assignment is N/A, receiver edge matching separate')
    (OUT/'checks/report-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    print('Generic Chinese report regenerated; personalized content is not authored in this repository')


if __name__=='__main__':main()

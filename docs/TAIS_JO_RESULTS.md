# TAIS-JO：实际实现完成，整体替代判定 NO-GO

基于Core `48b68655f95eaefbcdb7624e9de0e75a030ddf95`，新分支`research/tais-joint-optimization`。**保持GateOnly为Core默认。** 三层新策略可运行且得到部分收益，但联合挑战失败；没有追加机制、重选测试配置或把JO-S结果冒充Full结果。

开发500–509（预定九场景，1620运行）、验证510–519（全部45场景，2700运行）、最终520–549（全部45场景，8100运行）。完整历史种子审计无碰撞。配置在开发集选择，验证集已出现健康层负效应，仍原样冻结于 **`4cd19c37f3848cadf3f5510bcdec68cdaf6abd71`** 后仅执行一次最终测试。所有结果是同一合成生成器下的新随机证据，不是真实环境外部验证。选择20秒空闲上限、趋势斜率0.005单位/秒、上传心跳120秒；[协议](TAIS_JO_PROTOCOL.md)与[选择锁](../results/tais-joint/selection.json)保留全部六个候选和不利结果。

| 方法 | Precision | Recall | F1 | 故障诱发误报 | 采样 | 上传 | Binary v1字节 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AdaptiveSense | 31.42% | 51.67% | 39.08% | 650 | 101,149 | 49,902 | 1,457,134 |
| AdaptiveSense+TrustLog | 31.42% | 51.67% | 39.08% | 650 | 101,149 | 49,902 | 1,756,546 |
| GateOnly | 35.93% | 51.33% | 42.27% | 433 | 76,091 | 47,569 | 1,673,548 |
| JO-S | 40.98% | 69.89% | 51.66% | 489 | 151,019 | 52,928 | 1,859,913 |
| JO-HS | 36.04% | 59.22% | 44.81% | 559 | 140,684 | 64,177 | 2,259,547 |
| JO-Full | 36.04% | 59.22% | 44.81% | 559 | 140,684 | 36,571 | 1,283,513 |

表中均为同一新测试集、同一实际v1编码。AdaptiveSense不含健康元数据，其故障诊断指标为N/A。每方法900个事件；不将旧BM-1绝对值当本轮对照。未要求这些操作点采样/上传预算相等，**这不是预算匹配优效结论**。

## 目标兑现与代价

- Full对Gate：Recall51.33%→59.22%，**+7.89pp**，种子簇配对95%CI[+3.00,+12.78]pp；Precision35.93%→36.04%，+0.11pp，CI[−1.74,+2.07]pp；F142.27%→44.81%，**+2.54pp**，CI[−0.14,+5.24]pp。Recall挑战达到，F1+3pp未达到，Precision未证明改善。
- 短事件（profile short）TP134/450→230/450，漏检316→220，减少96（30.38%）；短事件Recall29.78%→51.11%，差CI[+12.22,+30.67]pp。干净短事件7/30→28/30。全体事件有采样覆盖698/900→900/900；本地和上传匹配TP同为462→533，新增采样覆盖不保证有效识别。
- 漂移类故障诱发误报258→172，**−33.33%**，配对计数差−86，CI[−100,−72]；漂移事件TP85/120→97/120，Recall差CI跨零。改善不是整体误报改善：所有故障诱发误报433→559，**+29.10%**，差CI[+102,+151]；严格未匹配824→946。稳定偏移诱发175→375，事件TP118/120→55/120，是主要失败；尖峰诱发0→12。全部八类与45场景保留于CSV。
- Full采样76,091→140,684（**+84.89%**），高于TrustLog101,149约39.09%，采样挑战失败。上传47,569→36,571（−23.12%）；字节1,673,548→1,283,513（−23.31%），也低于TrustLog1,756,546和无健康AS1,457,134。它是上传决策变化，不是再次压缩协议或删健康字段。
- 事件条件平均延迟24.615→18.413s，差CI[−9.489,−3.308]s，但短事件条件延迟增加2.791s（CI[+1.693,+3.923]）；不同检出集合造成选择效应，不能声称每个事件都更快。
- 接收端平均数据年龄28.714→48.359s；真正合并所有秒的P9558→110s，最大79→134s。重要事件/健康标志边沿上传延迟Full为0（指实际采样检出后，同次上传），不代表物理事件发生后零延迟。温度MAE4.9504→4.9551°C，湿度MAE0.3909→0.3477%RH；RMSE见完整CSV。温度误差包含故障读数，不能把故障值的完整传输误称为正确环境重构。空值期间覆盖率独立报告，不用最近有限值偷偷代替已收到的null。主summary的P95是各运行P95平均；[pooled_age.csv](../results/tais-joint/test/analysis/pooled_age.csv)才是合并分布P95。

## 原始健康判断和辅助怀疑

C11源码、参数和规则未改。每个新测试采样时刻的原始state/score/flags独立记录；新增测试对照独立C11上下文逐条一致。**采样计划改变，诊断表现仍会改变，不能称为诊断效果不受影响。**

全故障检出672/1260→759/1260（53.33%→60.24%，配对差CI[+5.71,+8.26]pp），但漂移原始DRIFT检出90/180→87/180，条件DRIFT延迟278.09→324.00s。辅助APP怀疑180/180，条件延迟51.95s；这不是180个物理故障被证明。无故障的90个控制运行有25个也出现APP怀疑（clean_none1、clean_event22、clean_short2），且恢复后/其他故障期间存在9967个不在漂移注入窗口的怀疑采样，不能全算有效新增诊断。

应用位`APP_SUSPECT_DRIFT=32`不冲突C11位0–4（mask31）；uint32 v1 flags可无损携带。state/score仍是C11，原flags保留在`joint[channel].raw_c11`，诊断指标只读原flags。接收端完整flags可用mask31与bit32区分，界面明确显示APP来源。v1格式没有改。旧接收软件能解码32，若未提供新映射只会显示未知扩展位，不应当成原生DRIFT。CRC不是认证。

## 消融决定

- **采样层S贡献了主要召回收益**：Recall51.33%→69.89%（+18.56pp，CI[+13.78,+23.33]），F1+9.39pp，但151,019采样、1,859,913字节均高于TrustLog，故不能直接推荐为综合替代方案。
- **趋势/健康层H当前净负效应**：相对S损失96个事件，Recall−10.67pp（CI[−14.00,−7.89]），尽管漂移诱发报告下降。趋势与真实缓变/阶跃、稳定偏移及候选残差相互作用，跨通道事件也受新增趋势怀疑影响：跨通道TP400/420降至353/420。这不是故障温度直接关闭湿度的全局门，而是湿度自身真实变化被辅助趋势规则误判。**不推荐进入默认判断路径；应停止调当前H阈值，把它保留为失败实验/可选诊断记录。**
- **独立上传层U有最明确的工程收益**：HS→Full的采样、TP、P/R/F1全部相同，上传64,177→36,571，字节2,259,547→1,283,513（−43.20%），配对差CI[−995,065.2,−957,384.95]字节；代价是数据年龄增加。没有实施双端有状态预测，也没有Wirev2依赖放大。尚未测试“S+U但去掉H”的新组合，不用本测试结果拼出一个未预先评价的新获胜策略。

因此本轮整体NO-GO，保留GateOnly默认。值得保留的是有界复查与独立上传组件，健康判定路径暂不推广。后续若要组合S+U，须另行审计新种子/冻结方案；本轮不继续在520–549上调参。

## 实际Core演示和失败时间线

```sh
.venv/bin/python examples/tais-core/run.py --policy tais-jo \
  --scenario clean_short --seed 20 --pace .01 --ui live --verify \
  --out results/scratch/jo-live-new-01
# 默认仍等价 --policy gateonly。CSV/逐条JSONL和layout1/2/3均可用。
```

[实际日志目录](../results/tais-joint/core/)包含六场景×两策略的真实收发流程；seed20已使用，仅作软件演示。[短事件/漂移时间轴](../results/tais-joint/timelines.png)与[每个采样点、候选、C11、APP、上传原因和字节CSV](../results/tais-joint/case-timeline.csv)均由这些日志生成，不是静态伪造界面。

- 干净短事件：Gate采样600/660错过634–656真值；Full640后复查，650上传，**670又有未匹配报告**，未隐藏额外告警。
- drift_none_long：Gate660、1240报告，C11首次DRIFT820；Full APP615，C11 DRIFT965，只剩1195恢复附近错误报告。不能称恢复误报已经修好；真实结束1172，只用于离线归因。
- 全部漂移的严格未匹配温度报告：Gate原DRIFT前91、恢复120s内179；Full原DRIFT前23、之后14、恢复151。它们是严格未匹配计数，**不与反事实排除后的258/172诱发计数混同**。
- drift_same_long演示Full多了一个未匹配报告，range_same_long两者仍0/1，完全擦除的信息未解决。missing_cross_long两者检出1/1，Full未匹配1→0且字节1285→774，不能以此一个案例抵消全体跨通道不利结果。

## 复现、保护与测试

详见[结果README](../results/tais-joint/README.md)。完整记录与逐帧hex保存在新忽略目录`results/traces/tais-joint`；Git保留所有指标、输入/结果指纹、事件匹配、选择锁、CI表和演示收发日志。开发首轮统计脚本错误（AS没有health字典）在读取首批对照时退出，原失败manifest/log仍在`development-attempt1`，修复后仅重新执行开发，不涉及最终数据；辅助分析初次导入路径错误也保留。算法冻结后未更改策略、配置、runner或主分析脚本。

实际全套测试 **700 passed, 2原有严格xfail, 0failed**；新增36项。另对12420个评分运行、471467个实际上传帧完成编码长度/无损解码/事件匹配/同输入核验。原832个普通跟踪文件、两个子模块及五个C0原始文件均核验未变；唯一现有文件改动是Core入口增加显式可选策略，原GateOnly输出全部45场景回归通过。保护检查[JSON](../results/tais-joint/checks/delivery-verification.json)。

## 参考思想与外部数据范围

- Lu等，*Adaptive Sampling for Spatiotemporal Anomaly Monitoring in Wireless Sensor Networks*，[arXiv2607.15235v1](https://arxiv.org/abs/2607.15235)，官方页面注明ISSC2026 accepted。参考采样可见性与风险分配；没有实现KF、GLR、邻域唤醒或免费连续哨兵。
- Arnaiz等，*Energy and relevance-aware adaptive monitoring method…*，Integration94(2024)102097，[出版方](https://www.sciencedirect.com/science/article/pii/S0167926023001396)。核对了动态采样与双预测协同思想；本文只采用采样/上传解耦，无PI电能目标或硬能量保障。出版社摘要可读，首次大学PDF入口403，不声称复现其完整算法。
- Bifet/Gavaldà，[ADWIN作者稿](https://www.cs.upc.edu/~gavalda/papers/adwin06.pdf)、[正式DOI](https://doi.org/10.1137/1.9781611972771.42)；[River Page-Hinkley源码](https://raw.githubusercontent.com/online-ml/river/main/river/drift/page_hinkley.py)。核对“分布变化检测不等于物理故障”的使用边界；没有实现ADWIN或Page-Hinkley，实际是9点稳健斜率/残差。
- Dias/Bellalta/Oechsner，*The impact of dual prediction schemes…*，Computer Communications112(2017)58–72，[出版方](https://www.sciencedirect.com/science/article/pii/S0140366417308435)。借鉴预测误差触发通信思想；实际上传只用last-sent deadband和完整独立帧，不冒称双预测复现。

Hull [v2官方入口](https://data.mendeley.com/datasets/54htxm94bv/2)仍未解除C1日期/聚合时间语义阻断。原Full Data只读校验未变，实际严格导入已执行并拒绝未核实的Date/Time映射；[失败记录](../results/tais-joint/checks/hull-import-attempt.txt)。提供`scripts/import_joint_csv.py`导入具有独立核实数字秒时间轴的用户记录，原始值不插值/修日期。**未完成真实温室性能实验**，不报告自然故障准确率、真实5–10秒检测、实测电能或LoRaWAN包数改善。

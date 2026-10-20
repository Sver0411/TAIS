# TAIS 论文学术大修记录

基准：`db23a95ef95fd025553b70754625af7b42b5682e`；修订分支：`docs/tais-paper-major-revision`。本轮只修改论文、展示/构建/检查脚本、文档及只读统计，不修改算法、生成器、原始CSV、真值、归档或冻结协议。没有新的大规模仿真实验。

## 逐项回应审稿意见

| 意见/旧稿状态 | 实际修改及核验 |
|---|---|
| 跨生成器差异可能被误读为单独的分布效应 | 标签差异的说明原本已在Methods/Discussion中存在，但摘要和“did not transfer”等短句不够精确。现统一为跨合成任务设定，前置signal/fault/timing/ground-truth interval差异，明确不可分离归因。 |
| “未证明优于”与“证明更差”需区分 | 旧稿已报告F1区间跨零，并未发现明确声称总体F1显著更差；现进一步明说两方向的总体F1结论都未建立。Recall的负区间单独报告，保留多重比较限制。 |
| 主线被重复数字掩盖 | 以质量、资源、信息时效为研究问题，明确三项系统评估贡献；正文仅两张主要结果表与架构/两张关键结果图，完整操作点、健康/接收端诊断、敏感性和次要区间移入附录。 |
| 摘要过长 | 自动生成约187词，保留两任务、独立基线、关键F1差/区间与范围限制，未堆叠全部指标。精确词数在结果目录abstract.json。 |
| 统计解释和事后预注册风险 | 明确原仓库冻结计划定义过指标族、对比列表、种子和5%规则，但没有独立注册的唯一确认性primary endpoint；本轮强调F1/Variance/Fixed20是事后叙事选择。区间均为未校正逐项描述性区间，不新增确认性检验或p值。 |
| 预算容差稳健性不足 | 新只读脚本保留60个现有control-target组合，检查2/5/10%；三阈值敏感性是事后分析，5%只是复现原规则，不能据此重新预注册或重选参数。 |
| Fixed20不利比较不够突出 | 新讨论小节和六指标黑白图：同时呈现其更高质量点估计、近采样量、更多字节/FI和更低年龄；不作无预声明区间的总体优效断言。 |
| 通信贡献可能归错模块 | G2 Gate+U与G1独立+C11+U消融证明部分收益是公共U规则；native对比与common调度隔离分开解释。 |
| trust/FI/budget/resource定义较晚 | trust和resource在Introduction首次使用处定义；FI、预算资格在Methods首次正式使用处给出窗口、反事实和近似含义。 |
| Fig2题注重复、Fig3缺图、18–19页乱码 | 对原19页PDF作视觉核验：这些疑似缺陷未发现，不能把文本提取或相同真实数值当作图像问题。真实问题是密集小字号、冗长正文及浮动顺序。修复与最终页数见布局审查。 |
| 表格拥挤与黑白打印 | 主表重组，完整长表采用9pt并保留跨页表头；阻止方法组只剩一两行孤立跨页。新关键图用空心圆/叉和实心/斜线纹理区分，不依赖颜色。 |
| 引用、归属和作者信息 | 保留8项已核实DOI，保护CLARA/DSRA大小写，Rao-inspired名称持续明确；依赖归属保留。姓名/单位占位符未填造；AI披露和人类确认写入投稿清单。 |

## 关键英文前后对照

旧句（原生成摘要）：

> Performance varied substantially across generation mechanisms.

新稿不把差异单独归因于生成分布，Methods明确写为：

> G1/G2 differ jointly in dynamics, noise, fault processes, event shapes, timing and ground-truth interval definitions.

旧句（原生成摘要）：

> The near-budget quality advantage observed on G1 did not transfer.

新句（生成的Discussion）：

> SU40's near-budget detection-quality advantage observed in G1 was not retained under the independently specified G2 synthetic task, which differs in signal dynamics, fault processes, event timing, and ground-truth interval definitions.

新稿对区间的解释：

> This interval includes zero: it does not establish either an F1 advantage for SU40 or an overall F1 disadvantage.

旧稿“at equal acquisition cost”改为“at approximately matched acquisition totals”；相近计数不再被写成完全等成本。正文不使用“统计显著改善”“真实泛化成功”或字节等于能耗的说法。

## 可重复构建链

`scripts/build_paper.py`继续生成原G1/G2数字绑定，再调用`scripts/paper_review_artifacts.py`，后者读取冻结汇总/区间/事件表，并调用只读`scripts/analyze_budget_sensitivity.py`。新正文表、数值段落、187词摘要、黑白图和60行资格表均可重复生成。禁止通过手改自动表格实现一次性修订。

`review_data_audit.csv`提供新数值的source/row/column映射；`review_source_fingerprints.json`和`results/tais-paper-review/protection.json`分别绑定输入和202个原始源码、配置及结果文件。旧PDF视觉证据留在原结果目录，本轮新PDF证据独立存放，不覆盖历史指纹。

# OSP-1：真实背景上的离线空间参照探索

**这是基于真实温室背景和受控干预的离线探索性实验，不是实际在线 LoRaWAN 系统或自然故障诊断的确认性验证。** [协议](../../docs/OFFLINE_SPATIAL_PILOT_PROTOCOL.md)在效果运行前提交；[配置](../../configs/offline_spatial_pilot.json)固定全部节点、时间块、方法和敏感性设置。[完整结果解释](../../docs/OFFLINE_SPATIAL_PILOT_REPORT.md)区分净报告变化、新增/消失报告、局地召回和信息边界。旧C0/C1/C1.1及v0.1/v0.2/BLOCKED结果保持原样。

## 输入与许可

Singh、Rahmani、Weyn、Berkvens，*Joint Communication and Sensing: a Proof of Concept and Datasets for Greenhouse Monitoring using LoRaWAN*，Zenodo v1.0，数据 DOI [10.5281/zenodo.5793685](https://doi.org/10.5281/zenodo.5793685)，论文 DOI [10.3390/s22041326](https://doi.org/10.3390/s22041326)。数据 [CC BY4.0](https://creativecommons.org/licenses/by/4.0/)；本项目输出为明确标识的治理统计及受控副本实验，不暗示作者背书。原始工作簿不重新分发。

Greenhouse-1.xlsx 固定 SHA-256 为 `9b5f48b5f37ebc90052658649de7471b298da7dd4581bf47d0d8ec404cadff19`。[C1.1](../../docs/C1_1_DATASET_SELECTION.md)包含官方文件入口及MD5。只读原文件；解析账本保存原单元格、表名、行号、原值和质量原因；代理时间排序/数值掩码不修改源文件。

## 安装与重新生成

Python 环境使用仓库的 `requirements-lock.txt`；此模块不新增第三方依赖，也不需openpyxl。所有算法研究代码在独立 `src/tais_spatial/`，旧调度器未变。

```bash
git clone --branch research/offline-spatial-pilot --recurse-submodules https://github.com/Sver0411/TAIS.git
cd TAIS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-build-isolation
python -m pytest tests/test_offline_spatial.py -q
```

准备一个已经下载/校验且不会覆盖的原始文件路径，和**不存在**的仓库外缓存目录。以下变量需由执行者设置为自己的绝对路径；prepare 检查源哈希并拒绝覆盖输出。不要把工作簿放到 Git 跟踪目录。

```bash
export TAIS_WORKBOOK='/absolute/path/Greenhouse-1.xlsx'
export TAIS_CACHE='/absolute/new/path/pilot-prepared'
python scripts/offline_spatial.py prepare --workbook "$TAIS_WORKBOOK" --output "$TAIS_CACHE"
```

`source-ledger.jsonl.gz` 和 `observations.npz` 保留在该外部目录，`quality.json` 固定源/账本/缓存指纹。完整原始记录与大派生账本不提交Git。提交的 [source-quality.json](source-quality.json)是实际质量检查摘要，不是新的事件真值。

可先做小规模流程调试（仅开发集，1日期×3节点×2物理量×13场景×4方法=312条计分结果；其日期数门槛预期不通过，不能当完整验证）：

```bash
python scripts/offline_spatial.py run --cache "$TAIS_CACHE" --split development --smoke --output results/scratch/my-pilot-smoke
python scripts/offline_spatial.py analyze --output results/scratch/my-pilot-smoke
```

完整复现使用新 scratch 子目录，不覆盖本文已归档的结果。所有输出目录必须不存在：

```bash
python scripts/offline_spatial.py run --cache "$TAIS_CACHE" --split development --output results/scratch/my-pilot/development
python scripts/offline_spatial.py analyze --output results/scratch/my-pilot/development
python scripts/offline_spatial.py run --cache "$TAIS_CACHE" --split validation --output results/scratch/my-pilot/validation
python scripts/offline_spatial.py analyze --output results/scratch/my-pilot/validation
python scripts/offline_spatial.py freeze --development results/scratch/my-pilot/development --validation results/scratch/my-pilot/validation --output results/scratch/my-pilot/freeze.json
python scripts/offline_spatial.py run --cache "$TAIS_CACHE" --split test --freeze results/scratch/my-pilot/freeze.json --output results/scratch/my-pilot/test
python scripts/offline_spatial.py analyze --output results/scratch/my-pilot/test
```

freeze会拒绝未通过的开发/验证门槛；test会拒绝冻结后代码/配置变化。不要为了“通过”门槛而改变时间块或参数。重新运行同一冻结实验是可复现性检查，不是新的独立验证。原保留数据只在首轮冻结后用于一次探索评估，不按其结果回调模型。

## 输出与统计口径

每个实际运行分区的 `manifest.json`列出源SHA、完整配置、代码SHA、日期、节点、计分结果数量和全部输出哈希。

| 输出 | 内容 |
| --- | --- |
| `node-metrics.csv.gz` | 每日期/目标/物理量/场景/方法/阈值/对齐点的指标；每条是完整运行的汇总，不是独立无线包 |
| `interventions.jsonl.gz` | 独立于检测输出的干预计划、名义幅度/起止、参考节点、受控饱和与固定轮询覆盖；非自然标签 |
| `summary.csv` | 全部节点的分母、事件窗口/增量响应召回、漏检、机会覆盖、漂移净变化/新增报告、成本 |
| `paired-differences.csv` | Spatial分别减HistoryShort、HistoryExtended、NullSpatial；完整日期cluster配对95%区间及各日差值 |
| `example-traces.jsonl.gz` | 预定AF29、首日期、温度、主倍率/对齐的所有13场景；数值、行号、代理可用时间、score、趋势门控和报告；未按结果选图 |
| `cost-recall.png` | 三阈值点的局地快事件增量召回与假设应用请求；参考RPC计入 |
| `time-sensitivity.png` | 全九个预定对齐假设下的Spatial−HistoryExtended差值；不是最优对齐筛选 |
| `example-trajectories.png` | 所有13个预定场景的AF29轨迹和报告；重叠标记表示多个方法可能同刻报告 |
| `gate.json` | 日期/覆盖与可解释差异门槛；通过不等于算法优效 |

净报告数减少可来自压制原背景报告，不能直接称误报改善。新增报告、消失报告与净差分别保留。自然严格误报率和自然故障召回均不可计算。窗口召回可能碰巧匹配背景报告，主要同时考察相对无该事件的配对控制**新增**报告召回；事件恢复边缘也可能触发绝对变化报告，延迟会如实反映，不能把它说成及时起点检测。

分母包括没观测机会、参考缺失和数值饱和的请求；另列实际机会。所有日期、节点、阈值和对齐均保留，未挑选有利点。区间按日期而非节点重抽样；日期数少、仅一温室、正向固定形状干预、静态校准和未知时间语义限制推广。

## 成本解释

目标为本地固定轮询；参考每槽每tick为10字节请求+26字节响应（缺失也有状态），每环境报告18字节，均为假设二进制应用载荷，不是实际LoRaWAN包/功耗。Spatial和NullSpatial参考预算严格相等；历史缓存方法没有这笔网络成本。读取次数、不同原行数和缓存复用分别记录；没有声称改变原部署的实际采样频率或已测得节能。

## 审计与限制

源文件及旧跟踪文件的前后指纹检查、原有测试和新增测试结果列于研究报告。初始192通过/2预期失败属于旧基线；新增23项通过后完整套件为215通过/2旧预期失败。后续如果检查有失败，保留原日志，不覆盖为成功。

正式在线NO-GO未解除；没有联系作者、实现新在线调度器、修改上游、向自然数据赋故障真值或合并main。固定计划下的信息证据与之后的闭环预算研究是两个不同阶段。

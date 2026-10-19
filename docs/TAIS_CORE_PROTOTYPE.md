# TAIS Core：冻结基线的端到端软件原型

默认 **GateOnly、SensorTrust原始C11、Stateless Binary v1、倍率1.0**。新增的是流入口、字节链路、接收端、终端监测与工程验证，不是新检测算法或旧成果改名。基准为`2ea17b39a502e32136333b0987d72c613cccbd70`，分支`research/tais-core-prototype`。

保留[BM-1确认机制NO-GO](BUDGET_MATCHED_EXPERIMENT_REPORT.md)、[观测歧义](FAULT_EVENT_OBSERVABILITY_REPORT.md)、[ReferenceGate NO-GO](INDEPENDENT_REFERENCE_BUDGET_REPORT.md)、[v1无损编码](WIRE_PAYLOAD_EXPERIMENT.md)和[v2丢包失步代价](WIRE_PAYLOAD_V2.md)。GateOnly的默认选择依据已使用的历史合成结果，是工程选择，不是新独立验证。没有启用确认机制、空间参照或v2。

## 运行与信息边界

```sh
.venv/bin/python examples/tais-core/run.py --scenario missing_cross_long \
  --seed 20 --pace .01 --ui live --verify --out results/scratch/core-new-01
.venv/bin/python examples/tais-core/view_run.py results/scratch/core-new-01 --tail 80
```

安装、CSV、逐条JSONL、独立接收进程及受控链路命令见[运行说明](../examples/tais-core/README.md)。已有输出目录拒绝覆盖。

```text
当前源记录 → 到期读取 → 冻结Scheduler(confirmation=False)
                         └─ 原C11健康判断 + 原变化评分/事件/采样/上传决策
           → 原业务envelope → 原v1 encode → 实际bytes本地链路
           → 独立decode → 带时间戳的接收状态 + 终端界面 + JSONL历史
```

源时间轴、实际读取、实际上传、收到/拒绝的帧均单独记录。调度器只收到到期时的当前观测，不接收轨迹、真值或未来值。稀疏输入使用到期后首条可用记录，不插值补造秒级观测。CSV/JSONL无核实真值时，所有真值指标为N/A，额外标签列不自动视作真值。物理单位由输入方保证，温度°C、湿度%RH。

界面分开发送端本地状态与接收端状态，显示值、健康状态/评分/标志、环境事件、本次采样/上传、当前帧与最近帧字节、累计采样/上传/字节及收到的故障/恢复时间线。年龄是相对源时间轴的数据年龄，不是实测网络延迟。未上传的内部状态不出现在接收端；无新帧时保留旧值但始终标注其时间/年龄。

在线路径内存有界：C11/原评分窗口、单个待乱序帧、最新状态及12条界面历史；完整历史流式刷入磁盘。离线合成生成器和EOF后的可选验证可以使用有限完整轨迹。计数中的采样是处理一组通道观测的周期，源行数另列；输入源已采集的数据不能被回溯节省物理采集成本。

v1通道映射预配置，原测量浮点精度、时间、完整健康字段、事件布尔与null语义保留。实际字节按`len(encoded_bytes)`计，日志hex长度不计作载荷。CRC是误码检查，不是认证。没有免费序号/ACK、重传、状态增量或丢失历史恢复。乱序帧可以解码存档但不得回滚最新状态；损坏/配置不符拒绝；新接收端可从任意合法完整帧恢复当前快照。帧边界/设备路由为本地预配置，未实现生产网络协议。

## 实际验收运行

以下都是已使用seed20上的软件演示，不是新增独立算法验证。合成真值只在EOF后离线评分；表中的TP/真值、未匹配报告属于**发送端报告**，不冒充丢包接收端的检测指标。

| 场景 | 源行 | 采样 | 上传 | v1字节 | 接收合法帧 | 发送端TP/真值 | 未匹配 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| clean_none | 1800 | 32 | 30 | 1077 | 30 | 0/0，Recall N/A | 0 |
| missing_cross_long | 1800 | 77 | 40 | 1285 | 40 | 1/1 | 1 |
| range_same_long | 1800 | 34 | 31 | 1053 | 31 | **0/1** | 0 |
| drift_none_long | 1800 | 95 | 48 | 1725 | 48 | 0/0，Recall N/A | **2** |
| spike_same_long | 1800 | 84 | 38 | 1365 | 38 | 1/1 | 1 |
| 缺失跨通道 + 受控链路故障 | 1800 | 77 | 40 | 1285 | 32 | 1/1，仅发送端 | 1 |
| 手工CSV格式示例 | 7 | 7 | 6 | 198 | 6 | N/A | N/A |
| 逐条刷新管道输入，同一示例 | 7 | 7 | 6 | 198 | 6 | N/A | N/A |

每个合成验收运行的全部采样记录与报告序列均对照原`tais.replay.run(...,'GateOnly',1.0)`，健康、事件、采样间隔、上传触发及原JSON计数一致；实际TX均重编码核对，全部合法RX字段/浮点位与已发送帧一致。损坏及丢帧不反馈或改变发送决策。

链路故障使用每7帧丢失、每11帧损坏、相邻对反序的明确模拟：40帧中丢5帧，收到35帧，其中3帧CRC拒绝、32帧独立解码；14帧属于旧时间戳而未回滚最新状态，18帧更新状态。**8条原信息因丢失/损坏不可恢复**，后续快照不补造它们。独立进程另用无损链路的40个真实TX帧重放，得到同样接收状态/计数；这不是对丢失帧的恢复。

实际终端时间线摘录（合成缺失跨通道）：

```text
665s  temperature FAULT   score=45  flags=MISSING event=False
670s  humidity    HEALTHY score=100 flags=NONE    event=True
835s  humidity    HEALTHY score=100 flags=NONE    event=True
1185s temperature HEALTHY score=100 flags=NONE    event=False RECOVERED
```

此处835s报告未匹配物理事件窗口，仍计入严格未匹配。`range_same_long`真实事件被量程故障完全遮蔽，GateOnly无法恢复被擦除的信息。`drift_none_long`产生2个错误环境报告。`spike_same_long`的一秒尖峰未落在实际读取点上，故故障检出0/1；不能把连续时间注入误认为节点实际看见。这些限制不因端到端集成而消失。

[正常TUI实际终端输出](../results/tais-core/acceptance/normal/terminal-final.txt) · [原始PTY记录](../results/tais-core/acceptance/normal/terminal.ansi) · [故障/恢复时间线](../results/tais-core/acceptance/fault-event/timeline.txt) · [完整流JSONL](../results/tais-core/acceptance/fault-event/journal.jsonl) · [失败示例](../results/tais-core/acceptance/known-failure/summary.json)。运行manifest记录父提交及执行源码SHA，源码SHA用于核实当时执行的新代码。

## BM-1历史复核，不能称为新验证

只读取冻结170–199、45场景，核对5400个原归档运行和191,623个实际上传envelope，逐帧调用原v1编码/解码，合计6,744,258字节；每运行与原JSON/Binary字段逐项对应。未重跑策略、重选阈值或修改旧文件。保留GateOnly的.75/1/1.5全部原操作点。TrustLog1不是与GateOnly资源匹配的对照，不借此重启新的优效主张。

| 方法/倍率 | Precision | Recall | F1 | 故障归属误报 | 采样 | 上传 | Binary v1字节 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AdaptiveSense+TrustLog /1 | 30.7167% | 50.0000% | 38.0550% | 678 | 101428 | 49834 | 1754467 |
| GateOnly /.75 | 33.1106% | 49.5556% | 39.6974% | 531 | 78869 | 47705 | 1678263 |
| GateOnly /1 | 35.5906% | 50.2222% | 41.6590% | 456 | 76097 | 47481 | 1670781 |
| GateOnly /1.5 | 27.7383% | 21.6667% | 24.3294% | 340 | 71374 | 46603 | 1640747 |

默认点两者故障检出均684/1260=54.2857%，条件检出延迟119.7558s；健康状态不是经过概率校准的故障概率，flag检出也不证明唯一物理原因。稳定偏移检出均0/180。

GateOnly−TrustLog的描述性配对Bootstrap：30个种子簇、10,000次重采样。默认Recall差+0.2222个百分点，95%CI[−0.5556,+1.0000]；Precision差+4.8738pp[4.2562,5.4644]；F1差+3.6040pp[2.9504,4.2557]；故障归属误报差−222[−241,−205]；Binary字节差−83,686[−88,712.3,−78,765.95]。区间不是新增确认性检验；三点校正区间及所有分组也保留。

**不利结果**：同通道事件TP142→135/420；漂移组TP82→81/120，故障归属误报190→256。高阈值1.5的总体Recall只有21.6667%。这些场景没有删除。完整45场景、分组诊断/延迟和所有三点不确定性见[历史复核CSV](../results/tais-core/bm1-review/summary.csv)、[配对区间](../results/tais-core/bm1-review/paired_intervals.csv)、[逐帧归档核验](../results/tais-core/bm1-review/manifest.json)。

## 测试、保护与能力范围

新增55项测试，覆盖45场景冻结行为、真实codec、全部布局、接收端丢帧/损坏/乱序/重复/冲突/重启、无未采样读取、链路不反馈、CSV/逐条输入、失败部分记录和独立接收进程。全套本地实际结果：**664通过、2项原有严格xfail，0失败**。首轮51通过/3失败来自新文件名`inspect.py`遮蔽标准库；更名`view_run.py`后原断言全部通过，失败日志保留。

实际运行了连续TUI、CSV入口、逐条刷新的生产者管道、独立解码进程、受控链路与EOF后一致性检查。它们仍是合成/手工输入和本地软件链路；采样计数不是实测ADC操作，字节不是实测无线开销或能耗。真实传感器驱动、设备时钟/到达延迟、自然故障标签、网络分帧/认证/重传、LoRaWAN/MQTT及电流测量均未实现或验证。GateOnly的综合基线地位仅来自既有合成研究；集成不修复其算法边界。

历史保护和实际检查见[结果目录](../results/tais-core/README.md)。不合并main，不改上游、冻结配置、历史CSV/manifest/图表或原研究结论。

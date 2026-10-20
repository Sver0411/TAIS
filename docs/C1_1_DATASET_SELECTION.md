# TAIS C1.1：替代真实数据集调查与可行性决策

日期：2026-10-18（Asia/Shanghai）。基准：`7872d5401ced7cf7806adbffe21a1b515dcb79d3`；分支：`research/blocked-rearm-fix`。

## 1. 直接结论

**下一轮首选 Singh 等人的 LoRaWAN Greenhouse-1，作为真实多测点背景上的受控半合成研究候选；当前为 CONDITIONAL GO，尚无可以直接启动正式效果实验的 GO 数据集。** 其优势是农业场景、可核对的 AF16–AF42 相对布局、逐节点温湿度及接收时间说明，并且数据许可已由多个一手元数据入口核实为 CC BY 4.0。它不能验证自然漂移诊断正确，也不能证明原有秒级判据或实测节能。

最大的待补证项是 **Date/Time 的接收环节、时钟与可用性语义，以及公开记录和实际节点生命周期之间的关系**。正式分析前须明确：时间在网关、网络服务器还是 MQTT 后端生成，时区/回拨怎样解释，同时间记录怎样处理，能否在指定处理位置只使用已经收到的历史。不能将接收时刻冒充采集时刻，不能由约五分钟的间隔推断网络延迟。

NEON 土温产品可作为**跨环境、聚合尺度的补充候选**，维护问题日志还提供后续核验自然故障案例的线索；但它有发布延迟、后处理质量标记及本次原始包未获取的限制。2016 故障基准和用户提供的 GitHub 数据不是同一发布物，两者均不适合作为空间主数据。

| 候选 | 当前决定 | 可考虑的下一用途 | 尚未具备的能力 |
| --- | --- | --- | --- |
| A1：Greenhouse-1，Zenodo 5793685 / v1.0 | **CONDITIONAL GO**：优先补证及独立数据治理/协议准备 | 接收端约五分钟尺度的真实背景＋受控漂移/局地变化；接收消息通信特征描述 | 可信处理时钟的细节、停机逐例归因、完整自然事件/故障真值、真实闭环采样效果 |
| A2：同记录的 Greenhouse-2 | **NO-GO 空间主比较**；可条件准备第二温室背景 | 字段一致性的复核，未来在位置获证后作外部环境补充 | 19 节点的可核对位置映射、早期日期来源、同等时间语义保证 |
| B1：de Bruijn 等，SENSORNETS 2016 基准 | **NO-GO 当前使用/空间主比较** | 获取和许可补齐后，可考虑固定人工故障模型的补充基准 | 本次可下载且有许可的原始发布包、节点位置/时间对应；自然故障真值 |
| B2：tmoulahi GitHub / Zidi 等 2018 数据 | **NO-GO 空间主比较及当前公开复现使用** | 权限获证后才考虑既定特征向量分类任务 | 原始时间序列、空间映射、完整时间语义、明确使用许可；不是自然故障基准 |
| C：NEON Soil temperature，DP1.00041.001 | **CONDITIONAL GO 补充审计**，即时在线主比较 NO-GO | 已发布聚合数据的跨环境半合成回放；维护案例证据核查 | 本次未取得数据包；测量完成时的实时到达证据、独立密集故障/事件真值 |

这里的 CONDITIONAL GO 只批准“值得继续补证和准备协议”的选型结论，**不表示已经通过正式实验门槛**；任何遗留阻断未关闭，不启动算法或效果实验。未修改 [C1 草案](REAL_DATA_EXPERIMENT_PREREGISTRATION.md) 的 NO-GO 或未冻结状态。

## 2. 开工、范围和证据标准

开工时 HEAD/分支与预期一致，工作区干净。已阅读 [研究决策](NEXT_RESEARCH_DECISION.md)、[C0 审计](REAL_DATA_INTAKE_AUDIT.md)和 [C1 协议](REAL_DATA_EXPERIMENT_PREREGISTRATION.md)，复核 C0 原始清单及五个文件的大小/SHA-256，未重新下载或覆盖它们。

实际基准含 **399 个普通文件及 2 个子模块条目**：用户所述 398 个文件之外还有 C1 新增的协议。本阶段保护全部 399 个文件和两个固定上游，仓库中只新增本文。辅助脚本、来源响应和候选下载保存于仓库外：

`/Users/mac/Documents/TAIS-external-data/C1_1-20261018-evidence/`

没有改变 C0/C1 清单、原始数值、算法、配置、测试、既有结果或 CI。没有计算相关性排名、最佳滞后、效果差异，没有训练、注入或调参。本次的数量、日期、空值和间隔统计只用于结构/质量审计，不用于选择最好测点或时间窗。

证据等级沿用 C1：`RESOLVED` 为直接一手证据足以回答该具体问题；`PARTIALLY_RESOLVED` 为只解决一部分；`UNRESOLVED` 为证据不足。格式能解析、网页可访问和论文一般性描述，均不能替代实际文件与部署语义。下文每项引用来源 ID，完整 URL 与版本列于 §8。

## 3. A：LoRaWAN 温室数据

### 3.1 版本、DOI 与许可的实际核查

官方 Zenodo 记录 **5793685，version 1.0，发布 2021-12-30，元数据修改 2022-02-13**；本次版本 API 返回一个版本。论文为 Singh、Rahmani、Weyn、Berkvens，*Joint Communication and Sensing: A Proof of Concept and Datasets for Greenhouse Monitoring Using LoRaWAN*，Sensors 22(4), 1326，2022-02-09，DOI `10.3390/s22041326`。[A0–A4]

**许可：RESOLVED。** 网页文本提取曾只显示空的 License 标题，但实际 HTML 的 `license-cc-by-4.0-1` 和内嵌 rights、官方旧 API 的 `metadata.license.id`、官方 JSON 导出的 `metadata.rights`、DataCite 的 `rightsList` 均指向 **CC BY 4.0**。不能把文本提取漏项解释为“没有许可”，也没有仅凭 Open Access 标签推定使用权。[A0–A2]

依 [CC BY 4.0 正式条款](https://creativecommons.org/licenses/by/4.0/legalcode.en)，在适当署名、链接许可、说明变更且不暗示背书等条件下，允许分享、修改和派生分析，允许公开研究输出。未来引用应保留四位创建者、数据标题、版本 DOI、许可和所做处理；论文引用另列。TAIS 的 MIT 源码许可不覆盖这些数据。当前没有向 Git 提交任何工作簿、候选派生数据或实验输出。[A5]

**DOI 差异：RESOLVED，证据是版本关系，不能直接称笔误。** 论文 §1.2 写 `10.5281/zenodo.5793685`；Data Availability 写 `10.5281/zenodo.5793684`，但链接到记录 5793685。官方记录明确 `doi=...5793685`、`conceptdoi=...5793684`；DataCite 分别给出 `IsVersionOf` 与 `HasVersion`，Zenodo 导出的 parent DOI 也是 5793684。这足以确认后者是概念 DOI、前者是固定版本 DOI。复现固定 **5793685**，不跟随概念 DOI 的未来最新版本；没有推测作者当时选择两种引用的动机。[A0–A3、A6]

### 3.2 官方文件清单与实际取得

网页描述写 `.csv`，实际官方文件是三份 `.xlsx`，不能据描述捏造 CSV 下载。先核查上述许可，才下载两份逐节点工作簿；未下载转换表。下载回执保存来源、版本、完成 UTC 时间、字节数、发布方 MD5 和本地 SHA-256；原文件只读。[A0、A7]

| 官方文件 | 官方字节数 / MD5 | 本次结果 / SHA-256 |
| --- | --- | --- |
| `Greenhouse-1.xlsx` | 32,052,236；`4bf157516b3b576abe30550c65ce75d9` | HTTP 200，大小/MD5 匹配；`9b5f48b5f37ebc90052658649de7471b298da7dd4581bf47d0d8ec404cadff19` |
| `Greenhouse-2.xlsx` | 36,705,010；`08901111dce781dbe40904292eb847fd` | HTTP 200，大小/MD5 匹配；`82a882d0dce0044458c1ac3d787b62c9434fbce48f2ebaa3c55d9330e6c810eb` |
| `Greenhouse-1-Transformed_Data.xlsx` | 2,576,133；`c48e7c17a909dd79fe08344d973576cf` | **未下载**。官方说明为均值及植株高度等转换数据，不作为原始空间主输入；没有本地 SHA |

两个文件分别在 `A-raw/` 独占创建，未覆盖其他文件。下载完成 UTC 为 2026-10-17 17:43:16、17:42:47（当地均为 2026-10-18）。实际下载入口来自官方清单：

- [Greenhouse-1 内容](https://zenodo.org/api/records/5793685/files/Greenhouse-1.xlsx/content)
- [Greenhouse-2 内容](https://zenodo.org/api/records/5793685/files/Greenhouse-2.xlsx/content)

### 3.3 实际字段与位置

Greenhouse-1 有 27 个 AF16–AF42 节点表；Greenhouse-2 有 19 个 AF49–AF67 节点表及 `TEMP`、`RSSI`、`SNR`、`HUMIDITY`、`START-END` 五个辅助表。两者所有 AF 表的前六列完全一致：[A7]

```text
Date | Time | Onboard Temperature | Onboard Humidity | RSSI | SNR
```

节点标识在 **工作表名**，不是每行的设备序列号/DevEUI。Date/Time 是 Excel 日期、时刻值，未编码时区。温度/湿度在论文中按 ℃/% 展示，RSSI 以 dBm 展示；工作簿表头本身没有单位字典，SNR 的单位与具体解码定义仍应确认，不用习惯代替字典。实际前六列没有网关 ID、电池电压、帧计数器、采集时间、接收链路各阶段时间或故障标签。[A3、A7]

Greenhouse-2 的多数节点表右侧含 `Row Labels`、`Average of ...` 等透视汇总列，列数/位置各异；AF63 没有这部分。跨节点宽表没有显式的逐记录 Date/Time，**相同行号不是同步证据**，不能作为空间参照输入。`START-END` 是生命周期摘要，不能替代逐条记录或实际停机原因。Greenhouse-1 的 AF41 有额外空列，未被读作传感器字段。[A7]

**27 节点相对拓扑：RESOLVED；精确坐标/设备更换映射：UNRESOLVED。** 论文 Figure 7 和 Table 2 明确标出三排九列；Table 2 的 AF 标签与原始表名逐项对应，无需根据相关性猜测：[A3、A7]

| 图中的排 | 从左至右的 AF 标签 |
| --- | --- |
| Top | 16、19、22、25、28、31、34、37、40 |
| Middle | 17、20、23、26、29、32、35、38、41 |
| Bottom | 18、21、24、27、30、33、36、39、42 |

这支持按排/相对邻接定义候选，不能换算未提供的精确米制距离、地理方位或传播延迟。论文另说明网关近 AF40、出口近 AF42。没有找到 19 节点温室的同等位置表，不把 AF49–67 的序号直接排成网格。[A3]

### 3.4 只读质量审计的实际结果

使用捆绑 Python/openpyxl 只读遍历 AF 表的前六列，保留原表行号；非空行与空 Time 数另外用 ZIP/XML 独立解析对照。**工作表 max_row 含格式空行，不等于消息数。** 以下范围只是组合 Excel Date/Time 的字面结果，未指派时区或改写日期。间隔在各节点已可解析的时间排序副本上描述，不意味着恢复了真实接收顺序。[A7]

| 检查 | Greenhouse-1 | Greenhouse-2 |
| --- | --- | --- |
| AF 表前六列非空行 | 668,368 | 360,203 |
| 可组合日期/时刻的行 | 668,355 | 360,201 |
| 空 Time | 13 | 2 |
| 同节点重复可解析 timestamp | 0 | 0 |
| 源行顺序的 timestamp 回退 | 91,678 | 46,109 |
| 各节点正间隔中位数的范围 | 306–316 s | 308–315 s |
| 最大正间隔 | 4,821,586 s | 1,908,622 s |
| 字面最早/最晚记录 | 2020-04-10 13:46:06 / 2020-11-23 05:31:00 | 2020-06-22 10:51:57 / 2020-12-27 23:20:00 |
| AF 表中整行前六列为空的格式行 | 68,629 | 115,255 |

这些非空行的温湿度/RSSI/SNR 未见空单元格，前六列未见公式；这不证明数值准确，也没有对异常赋自然故障标签。空 Time 原样保留为不确定，不能填成午夜或插值补时间。源行回退不能归因为网络乱序或时钟回拨，可能原因需导出过程解释；没有改写/重排原文件。

官方描述与文件范围不能无声统一：Zenodo 描述分别为 April–August、July–November；论文 §2.1 描述的采集范围更长；本次工作簿又包含第二温室 AF64 的 2020-06-22 早期记录。第一温室官方另明确 4 月 10 日在房间开机，4 月 17 日 06:38 才移入温室。以上均须作为部署阶段/记录范围问题核实，不因论文某个建模子集看起来整齐而裁成它的范围。[A0、A3、A7]

论文提到电池/硬件导致提前停机、移除及电池更换，也提到帧计数器用于消息损失分析。但公开前六列没有这些生命周期逐例标签或计数器，**长间隙不能直接换算丢包率，也不能把全部空档认作硬件故障**。不沿用论文历史丢包数字充当本次复算结果。[A3、A7]

### 3.5 统一十维判定

| 维度 | 等级与证据 | 对研究的约束 |
| --- | --- | --- |
| 空间结构 | A1 相对布局 `RESOLVED`；A2 位置 `UNRESOLVED`。[A3 Figure 7/Table 2、A7] | A1 可按图中拓扑准备参照，不能捏造坐标；A2 不作邻域空间主比较 |
| 时间可信度 | `PARTIALLY_RESOLVED`：A0 明说 receiving time；A3 给网关→TTN→MQTT→MongoDB 架构；实际 Date/Time 无时区/字段生成代码。[A0、A3、A7] | 尚不能区分网关/服务器/后端接收时刻，不能宣称采集同步或测得端到端延迟 |
| 原始性 | `PARTIALLY_RESOLVED`：AF 表有逐记录测量，另有明显辅助汇总；公开表不是完整无线包/ADC原始日志。[A3、A7] | 仅 AF 前六列候选；不把透视/宽表当原始同步信号 |
| 分辨率 | 名义 5 min `RESOLVED`，实际不规则/长缺口也已核实。[A3、A7] | 适合分钟至小时尺度另行设计；不支持原 5–10 s 判据验证，不插造隐藏样本 |
| 故障真值 | `UNRESOLVED`：有停机概述，没有逐点独立故障标签。[A3、A7] | 只考虑用途1，严格自然故障误报/召回不可计算 |
| 局地事件 | `PARTIALLY_RESOLVED`：有多位置温湿度背景；没有独立局地事件表。[A3、A7] | 未来可独立预登记局地干预，不能把空间不一致本身当事件/故障真值 |
| 缺失和可靠性 | `PARTIALLY_RESOLVED`：缺时刻、异步上线、长空档可见；停机/换电/丢包原因映射不明。[A3、A7] | 保留缺口，不默认持续在线，不用完整案例删掉不利时期 |
| 许可 | `RESOLVED`：数据 rights 为 CC BY 4.0，多入口一致。[A0–A2、A5] | 允许有署名的研究与派生输出；不代表全部时间语义已解决 |
| 复现性 | 两工作簿版本、下载、发布方 MD5 及 SHA `RESOLVED`；转换表未取。[A0、A7] | 固定版本 DOI 和指纹，不跟随概念 DOI；审计程序/统计在仓库外 |
| 研究价值 | `PARTIALLY_RESOLVED`：场景/拓扑/接收信息匹配问题，但缺少时钟与真值。[A0、A3、A7] | A1 最值得补证；目前没有效果、自然诊断或能耗结论 |

**可以考虑的因果范围**：若确认 Time 是指定接收处理点的时间，未来可以把该点作为算法运行位置，只用 `receive_time ≤ decision_time` 的消息，不需要假装知道采集时刻或未知网络延迟；参考测量年龄只能先定义为“距接收时间”，不能称真正样本年龄。该设计仍需解决时钟、回拨、导出顺序和过期参考规则。若处理点是后端而字段来自网关，则后端额外传输延迟仍未知，不可直接套用。此为待核实的协议方向，尚未冻结或实施。

## 4. B：两条不同的故障基准来源

### 4.1 B1：SENSORNETS 2016

de Bruijn、Nguyen、Bucur、Tei，*Benchmark Datasets for Fault Detection and Classification in Sensor Data*，SENSORNETS 2016，185–195，DOI `10.5220/0005637901850195`。本次实际取得 Groningen 官方存档全文，结合 Waseda 作者机构记录核对。[B0、B1]

论文使用 Intel Lab、SensorScope 和 Smart Santander 的真实背景，先人工查看并选择/清理子序列，再注入 random、malfunction、bias、drift、polynomial drift 及混合故障。它同时说明 non-interpolated 和 interpolated 两种版本；**non-interpolated 不等于从未清理**，因为更早步骤已移除短故障并用邻值插补。论文也承认清理背景不能保证完全无故障。[B1 §1、§4、§5]

公开基准入口在论文中是 `http://tuananh.io/datasets`。本次 HTTP 请求返回 502，HTTPS 请求发生 SSL EOF，未取得可核实发布包/许可。沿论文引用的旧站分别尝试 HTTP/HTTPS：SensorScope 的 `sensorscope.epfl.ch` 均返回 404；Smart Santander 的 `www.smartsantander.eu` 返回 HTTP 502 / HTTPS SSL EOF，浏览工具也报 502；Intel 的来源是已经审计且仍 NO-GO 的官方日志，未重新下载。**这些是本次访问失败，不是断言全世界再也无法获取。** 未采用 ResearchGate 上的 Dropbox 链接或未验证镜像替代作者发布链。[B1、B3]

Smart Santander 在原论文中被称为此前未发表的 16 节点温度数据，不能把今天的项目首页当作已取得那份精确子集。没有下载到数据包，故实际列名、节点坐标、原时序对应及文件 SHA 均未核实。公开论文及其版权说明不等于数据/Java工具使用许可，不能仅凭“publicly available”就宣布允许公开派生复现。[B1]

### 4.2 B2：tmoulahi GitHub

固定检查 commit **`a36f90b55b30ba3552747430fb508735025ca80b`**；根树只有 README 和 `Gain.rar`、`Offset.rar`、`Out of bound.rar`、`Stuck-at.rar`。GitHub API 的 license 为 null，树中无 LICENSE；README 欢迎研究使用并请求引用，但没有明确修改、再分发和原数据转授权条款，不能据此确认公开派生复现的完整权限。**未下载这些压缩数据，也未发布其派生物。** 公共可读、可 fork 与允许修改/再分发并非同一项授权。[B2、B4]

README 指向另一来源：Suthaharan 等 ISSNIP 2010 的 TelosB 室外多跳背景，及 Zidi、Moulahi、Alaya 2018 的 SVM 故障分类研究；它没有声称自己发布 B1。README 描述 281,280 个 12 维向量、每组 4,688 条，三连续时刻各两温度/两湿度，另注入 offset/gain/stuck-at/out-of-bounds，标签 ±1。原始热水蒸汽干预也是受控事件，不是独立记录的自然故障。上述仅核实到仓库自己的说明，未把它升级为本次实际解压字段审计。[B2 README]

### 4.3 统一十维判定

| 维度 | B1：2016 基准 | B2：2018 相关仓库 |
| --- | --- | --- |
| 空间结构 | `UNRESOLVED`：背景节点数有论文说明，未取得可核实位置/发布包对应。[B1] | `UNRESOLVED`：向量含两组测量不等于节点位置已知。[B2] |
| 时间可信度 | `PARTIALLY_RESOLVED`：论文称保留 timestamp 的版本存在；无实际字段与到达语义核验。[B1] | `UNRESOLVED`：三时刻打包，无原始绝对时间/到达顺序证据。[B2] |
| 原始性 | `RESOLVED`：清理后再注入、另有均匀化版本，不是未经处理原始流。[B1] | `RESOLVED` 于 README 描述层：转换特征向量＋人工注入，不是原始流。[B2] |
| 数据分辨率 | `UNRESOLVED`：不能用一套背景的名义间隔代替三套发布子集的实际采样。[B1、B3] | `PARTIALLY_RESOLVED`：README 声称原始5 s/6 h；打包后间隔/交叠和乱序未核实。[B2] |
| 故障真值 | `RESOLVED` 于来源类别：注入标签，不是独立自然故障真值。[B0、B1] | `RESOLVED` 于来源类别：人为注入标签；标签文件未解压验证。[B2] |
| 局地事件 | `UNRESOLVED`：不能由清理/故障标签获得独立局地环境事件表。[B1] | `PARTIALLY_RESOLVED`：有原始蒸汽干预叙述，但与公开向量及注入标签的对应未核实。[B2] |
| 缺失和可靠性 | `PARTIALLY_RESOLVED`：有原时标/均匀化两版，但清理已改变背景缺失/故障证据。[B1] | `UNRESOLVED`：原始掉线、停机和缺失证据是否保留未确认。[B2] |
| 许可 | `UNRESOLVED`：数据和工具许可未取得。[B1、B3] | `UNRESOLVED`：无明确 LICENSE；引用请求不能替代许可。[B2、B4] |
| 复现性 | `UNRESOLVED`：未取到固定发布包/版本/校验值。[B3] | `PARTIALLY_RESOLVED`：commit/树可固定，数据因许可未下载，未验证内容 SHA。[B2] |
| 研究价值 | `PARTIALLY_RESOLVED`：将来可作既定注入模型的故障检测补充；不解除 Intel 时间阻断。[B1] | `PARTIALLY_RESOLVED`：可能支持特征分类补充，不能支撑空间参照/闭环时间流主张。[B2] |

两者当前均 NO-GO。不能将 B1 人工清理后的背景称绝对健康，也不能把 B2 当 B1 的镜像。就本研究而言，获得更多“已标注样本”不等于获得可信的多测点在线时间序列。

## 5. C：NEON Soil temperature（只追加这一套候选）

选择这一补充候选是因为官方产品 DP1.00041.001 同时有位置索引、窗口文档、固定发布版本和问题日志；没有为了数量再列不适合的数据。它是野外生态土温，**不是空气温湿度温室**，不与 A 合并为同一分布。[C0–C3]

本次官方产品 API 和文档实际 HTTP 200。当前产品 API 列出的新版 Quick Start 为 **NEON.QSG.DP1.00041.001v2**，已取得并阅读；初读 v1 后另核查 v2，后者明确说明 Level 1 数据未作 gap fill 或漂移/换传感器造成的 shift 校正，质量检查全面但不穷尽，不把 QF=1 自动判故障。[C0、C1]

发布版本候选 **RELEASE-2026**，产品 DOI `10.48443/zwvk-ph71`，由官方产品 API 给出。尚未选任何研究站点、深度或时间块；用于访问测试的 SRER/2021-01 只是官方教程示例，不是效果筛选或最终研究集。该月数据清单请求返回 **HTTP 403**；官方 2026-06-30 教程说明下载现需账户 API token。本次没有 token，也没有创建账户、寻找凭据或下载第三方数据副本。[C0、C3、C5]

| 维度 | 等级与官方证据 | 限制 |
| --- | --- | --- |
| 空间结构 | `PARTIALLY_RESOLVED`：每站五个土壤样地、多深度；HOR.VER 可与带有效期、偏移量/参考坐标的位置表连接。[C1、C3] | 本次未取实际包；相同 VER 编号不保证不同样地的实际深度相同，必须按真实位置/有效期匹配 |
| 时间可信度 | `PARTIALLY_RESOLVED`：ISO/UTC、窗口开始/结束和文件生成时间分别有定义；产品 API 明说月数据次月第二完整周发布。[C0、C2、C3] | 发布时刻/文件生成时间不等于测量当刻网关到达；不能默认窗口结束立即可得 |
| 原始性 | `RESOLVED` 于产品类别：Level 1、1/30 min 平均，有 QA/QC；0.1 Hz 采集不是本次拿到的公开完整高频流。[C0、C1] | 已处理聚合值和缺失不能冒充未经处理 ADC 样本；不能直接套原 TAIS 秒级配置 |
| 数据分辨率 | `RESOLVED` 于名义尺度：10 s 测量，发布1/30 min平均。[C1] | 实际缺口/覆盖未审计；只研究产品支持的尺度 |
| 故障真值 | `PARTIALLY_RESOLVED`：QF、science review 和具体维护问题日志存在。[C0、C1] | 自动 QF不是独立真值，维护叙述不等于逐点已标注故障；仍不能算完整自然故障准确率 |
| 局地事件 | `PARTIALLY_RESOLVED`：多个样地和站点事件产品 DP1.10111.001 提供核查路径。[C1、C3] | 未取得完整局地事件标签或对应数据，不能先验假设全部样地同时变化 |
| 缺失和可靠性 | `PARTIALLY_RESOLVED`：空值/QF/位置变化/issue log 有规范。[C0–C3] | QA过程可能移除观测；未取包，不能计算实际缺失、故障覆盖或保留比例 |
| 许可 | `RESOLVED`：官方现行 Data Usage Policy 为 CC BY 4.0（RTE物种例外不涉及此土温产品）。[C4] | 引用 NEON、固定产品和 release DOI、记录处理；软件包许可另核，不假定都是数据许可 |
| 复现性 | `PARTIALLY_RESOLVED`：年发布版本和 DOI 可固定。[C0、C2、C4] | 本次仅元数据/文档取得，原始数据包失败，无数据 SHA；需取得授权 token 后下载固定 release 并核对 |
| 研究价值 | `PARTIALLY_RESOLVED`：跨位置聚合背景和维护案例核验有意义。[C0–C3] | 与温室不同物理过程；仅已发布历史回放/有依据的可用性模型，不是即时在线部署验证 |

官方 issue log 的具体例子说明为何值得继续核查：ID 301 记录 ABBY 的 001.508 在降雨中疑似损坏、自动标记遗漏早期退化，随后人工标记并下线待换；ID 1826 记录 HEAL 特定位置早期故障未被自动标记；还有位置索引互换和冻胀位移记录。[C0 `changeLogs`]

这些是**独立于 TAIS 的维护/审查线索**，比仅凭数值异常更有证据，但“疑似”、宽时间区间和事后人工标记不提供精确物理起点，也不覆盖所有正常/异常时段。需核验原始维护证据、数据是否仍保留、标签是否依赖同一数值规则，才能决定是否构成用途2的有限案例；当前不能宣布自然故障标签已充分。

结论为 **CONDITIONAL GO 补充审计，当前 NO-GO 即时在线空间主实验**。若将来只研究已发布聚合回放，必须另行界定处理时钟、后处理标记是否在当刻已知，以及不可使用的未来人工审查信息；不能暗中放松 C1 的因果约束。

## 6. 用途分层及当前不可支持的主张

| 用途 | A1/A2 | B1/B2 | C：NEON |
| --- | --- | --- | --- |
| 1：真实背景＋受控干预 | A1 首选候选，先关闭时间/治理阻断；A2 缺位置映射 | 来源已有人工注入；取得许可/原序后才考虑补充，不再称自然故障 | 可考虑聚合尺度补充；先下载固定 release 并审计后处理信息 |
| 2：自然事件/故障验证 | 没有独立密集真值；严格自然误报/召回不可计算 | 人工标签不转化为自然真值；蒸汽是受控干预 | 维护日志可作有限核查起点，不是完整标签；当前严格总体指标不可计算 |
| 3：通信/资源 | 有接收记录、RSSI/SNR；无公开计数器/完整包/电流。可描述收到消息，丢包率与真实成本尚不能全算 | 变换子集不适合恢复真实通信；B2向量也不能直接换算上传 | 公开聚合发布不是射频日志，不能据此估算实际网络能耗 |

因此尚不能声称：空间参照已有效、自然漂移可被逐例识别、局地召回得到保持、减少了实测能耗、低频数据支持现有秒级条件，或公共背景本身绝对无故障。本文没有产生这些效果结果。

## 7. 维护者询问草稿与进入下一阶段的条件

**只起草，未发送任何邮件或消息。**

对 A 维护者：

1. 请给出版本 5793685 的 Date/Time 生成字段/导出代码：来自设备、网关、TTN还是 MongoDB？时区、时钟校准/夏令时/回拨、精度和接收队列延迟是什么？原文件时间回退是何种导出排序？
2. AF 名称能否稳定映射到 DevEUI/硬件及安装有效期？是否有更换、换电、上线/下线清单、原帧计数器、网关 ID 和原始消息用于独立核验？空 Time 的含义是什么？
3. 19 节点温室是否有可公开的布局及 AF49–67 映射？AF64 6月记录、跨出页面描述的日期、START-END 与逐记录范围如何解释？A1 4月17日搬入温室边界采用什么时区？
4. 是否存在独立控制、维护和环境事件记录？SNR等字段的单位、有效性/哨兵定义及采集到发送是否有缓冲/平均？没有时也请明确。

对 B1 维护者：请求可核实的固定发布包、数据/Java工具许可、原始来源权限、原行/时间/节点/位置映射、清理与插补日志及注入种子；不请求其把人工标签称自然真值。对 B2 维护者：确认数据许可与原来源再发布权限、原始时间与节点位置、打包/重叠规则及向量到原始干预的映射。

对 NEON：通过官方账户获取 token 的合法流程和固定 release 数据；确认所需位置有效期、原始维护证据及故障段是否保留；若研究接收端预算，还需原采集/入库可用性证据。不要把公开月发布当实时馈流。

下一阶段按证据依次进行：

1. **先补 A1 时间/身份与生命周期说明**；若得不到足够证据，A1 正式实验仍 NO-GO，不用假定网关时间绕过。
2. 在效果分析前，另立可冻结的数据治理/协议，固定输入列、可信处理点、缺时刻/回拨/启动阶段/不可用参考规则、位置范围和版本指纹。保留不确定记录和排除账本，不按表现筛节点。
3. 确定真实背景/半合成/自然案例分别能计算的指标；严格真值缺失标 N/A。参照获取、缓存与通信不免费，接收消息数不等于源端全部采样或发送数。
4. 根据可信时间预定开发→验证→最终块、窗口/事件/注入隔离及健康初始化边界；不沿用论文的有利建模子集，不在本阶段填写最终日期或选择参考。
5. 保持 C1 的假设和预算对照纪律；所有种子0–149视为已用，未来新种子先审计再冻结。固定计划信息实验与之后闭环预算实验分开授权、冻结和验证。
6. A1 不能获证则停止正式空间开发；NEON 只在明确缩小到聚合历史回放、取得原包及处理语义后考虑独立补充，不用另一套数据包装成农业主验证。

## 8. 来源与可复现核查索引

以下来源均于 2026-10-18 核查（回执采用 UTC）。浏览器错误与直连错误分别记录，不把一方失败概括为资料全不可达。

| ID | 一手来源、具体支持范围 |
| --- | --- |
| A0 | [Zenodo 记录](https://zenodo.org/records/5793685)、[官方 API](https://zenodo.org/api/records/5793685)、[版本清单](https://zenodo.org/api/records/5793685/versions)：文件、描述、许可、版本、概念 DOI |
| A1 | [官方 JSON 导出](https://zenodo.org/records/5793685/export/json)：rights、parent DOI、版本及文件信息；HTML 内嵌元数据交叉核查 |
| A2 | [版本 DataCite](https://api.datacite.org/dois/10.5281/zenodo.5793685)、[概念 DataCite](https://api.datacite.org/dois/10.5281/zenodo.5793684)：rights 与 IsVersionOf/HasVersion |
| A3 | [论文 DOI](https://doi.org/10.3390/s22041326)、[Europe PMC 正式全文 XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8963007/fullTextXML)、[出版方 PDF](https://mdpi-res.com/d_attachment/sensors/sensors-22-01326/article_deploy/sensors-22-01326.pdf)：§2/§3、Figure 7/Table 2、Data Availability；本次全文 XML 包未列 supplementary-material |
| A4 | [PubMed 记录](https://pubmed.ncbi.nlm.nih.gov/35214228/)：正式文献身份；不代替字段/时间证据 |
| A5 | [CC BY 4.0 正式法律文本](https://creativecommons.org/licenses/by/4.0/legalcode.en)：分享/改编授权及署名等条件 |
| A6 | [Zenodo DOI versioning 官方说明](https://zenodo.org/help/versioning)：概念与版本 DOI 的区别 |
| A7 | §3.2 两个实际官方工作簿、回执；仓库外 `A-structure-quality.json`、`A-xml-cross-check.json`、只读程序：实际字段、数量、时间、空值核查，不包含效果分析 |
| B0 | [Waseda 机构记录](https://waseda.elsevierpure.com/en/publications/benchmark-datasets-for-fault-detection-and-classification-in-sens/)、[出版方记录](https://www.scitepress.org/Papers/2016/56379/)：作者、论文身份与注入背景 |
| B1 | [Groningen 官方全文](https://pure.rug.nl/ws/portalfiles/portal/128994363/SENSORNETS_2016_14.pdf)：清理、插值、注入及发布入口；PDF取得，不重新分发全文 |
| B2 | [固定 commit](https://github.com/tmoulahi/Dataset-for-WSN-fault-detection/tree/a36f90b55b30ba3552747430fb508735025ca80b)、[README](https://github.com/tmoulahi/Dataset-for-WSN-fault-detection/blob/a36f90b55b30ba3552747430fb508735025ca80b/README.md)、[完整树 API](https://api.github.com/repos/tmoulahi/Dataset-for-WSN-fault-detection/git/trees/a36f90b55b30ba3552747430fb508735025ca80b?recursive=1)：来源与文件类别，无 LICENSE |
| B3 | 论文作者入口 `http://tuananh.io/datasets`、`https://tuananh.io/datasets`，SensorScope `https://sensorscope.epfl.ch/`、Smart Santander `https://www.smartsantander.eu/`：本次失败回执；Intel来源仍为 C0/C1 已审计记录，未重复下载 |
| B4 | [GitHub 许可官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)：公共可读不自动授予改编/再发布许可 |
| C0 | [NEON 产品 API](https://data.neonscience.org/api/v0/products/DP1.00041.001)、[产品页](https://data.neonscience.org/data-products/DP1.00041.001)、[RELEASE-2026 DOI](https://doi.org/10.48443/zwvk-ph71)：产品、延迟、release及 changeLogs |
| C1 | [Quick Start v2](https://data.neonscience.org/api/v0/documents/quick-start-guides/NEON.QSG.DP1.00041.001v2)：测量、平均、位置、维护、质量及漂移未校正规则 |
| C2 | [官方格式规范](https://www.neonscience.org/data-samples/data-management/data-formats-conventions)：UTC、时间字段、HOR/VER、生成时间、缺失和标记 |
| C3 | [官方土壤传感器教程](https://www.neonscience.org/resources/learning-hub/tutorials/soil-sensors-intro)：2026-06-30 更新，位置有效期/深度、下载令牌要求；教程例子不作为本次数据获取成功证据 |
| C4 | [现行数据使用政策](https://www.neonscience.org/usage-policies)、[引用规范](https://www.neonscience.org/data-samples/guidelines-policies/citing)：CC BY 4.0、NEON署名及产品/release引用 |
| C5 | [本次尝试的数据清单](https://data.neonscience.org/api/v0/data/DP1.00041.001/SRER/2021-01)：403，未取得候选原始数据包 |

A3 的 MDPI HTML/PDF入口最初在浏览工具返回429，PMC网页返回浏览器检查页；官方 Europe PMC XML 实际200，出版方 `mdpi-res.com` PDF也可由浏览工具读取。没有使用搜索摘要替代全文。B0 DOI跳转在浏览工具报错，已取得 B1 官方全文。C 的产品 API/政策/最新版指南可取得，数据清单403的事实单独保留。

主要元数据/文献响应 SHA-256（完整 URL、获取 UTC、大小、错误及指纹见仓库外逐项 `*.receipt.json`）：

| 响应 | SHA-256 |
| --- | --- |
| A0 Zenodo API | `46e0583704affc0421e466153debd20d5c799909e7bbcb98b88cc62fbd33e098` |
| A1 官方导出 | `8b391fe5a202561525f2c15d1a8442859a30eeae5aae75ae1cf11dcd7cd1a56d` |
| A2 版本/概念 DataCite | `472bf38143ba42a4c4f158bf4f90510aa59656b0df2a802f99d5c83e11098354` / `05716f5ebcabea2a7d075d92a633f45c159dec4e88e4538452799b6a781c3357` |
| A3 正式全文 XML | `a7299f42b75f4bcb48d022cf50d3379c0592adf425c346f836f5bfc0f2f7c6a9` |
| B1 官方论文 PDF | `6ed8c860ac403bd36836a318ecd0aaa90f74a96b0feb2a6312f5457724e162d4` |
| B2 README | `5c51dcabb458ce1e4564c6d49ebd8a9b32801f1381e2642942d5229206ae5500` |
| C0 产品 API | `6a375846cf392c2aba4f8fb8ed176bb9290160363bfd9fbfb5b955866e4a6c6e` |
| C1 最新指南 v2 | `cac352033435630acf88c31017250842e7b9860eddf7a31acc388ab14b7c6ba8` |

## 9. 范围与版本控制检查

提交前后检查 399 个既有普通文件指纹、两个上游 SHA/工作区、C0 manifest/五个原始文件及证据指纹；两份新工作簿在只读审计后重新校验 SHA/发布方 MD5。检查本地文档链接、`git diff --check` 和相对基准的唯一新增路径。应用测试和效果实验不运行，不引用旧通过数量作为本阶段结果。

文档提交使用 **`[skip ci]`** 避免触发包含基线/开发集 smoke 实验的现有工作流；不修改工作流，CI跳过不记为通过。提交只推送 `research/blocked-rearm-fix`，不合并 `main`。

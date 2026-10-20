# TAIS 主分支整合审计与发布门槛

审计日期：2026-10-20，Asia/Shanghai。本报告审查的是 **main 到整合候选的全部累积成果**，不是仅最近一次 README 修改。审计期间没有修改算法、生成器、默认参数、冻结协议、历史 CSV/图表/归档、原始输入或上游源码，没有新调参或重跑大规模算法矩阵。

本报告是发布前审计快照：**本地门槛通过，允许创建整合 PR；实际合并仍须最终 PR 头部 CI 全部通过、最新 main 不出现未审查变化且完整差异一致。** 此处不预写尚未发生的合并或最终 CI 成功。最终发布事实以该 PR 的合并记录和 main 的 Actions 为准；仓库发布不等于论文录用或硬件产品正式验证。

## 1. 远端、历史与完整差异

开工时工作区干净，当前分支 `docs/repository-readme-and-structure`。通过 GitHub API 逐页重新取得全部 **17** 个远端分支，而不是仅使用缓存；所有返回的提交对象已存在于完整本地 Git 中，并逐一刷新远端跟踪引用。HTTPS `git fetch` 连接超时，因此明确采用 API 获取最新引用、本地 Git 读取完整对象的组合，没有用 compare API 的前300条文件记录代替审计。

| 项目 | 审计初始值 |
| --- | --- |
| main | `68af4b6d9df7ed145a237defc4ab920600823373` |
| 候选 | `3fb89beaa7dd5aa64cb5c17f6088905b99f1709e` |
| merge-base | 与上述 main 相同 |
| 候选领先 / 落后 | 53 / 0 个提交 |
| 差异 | 1,226个文件：新增1,223、修改3、删除0 |
| 原main普通文件 | 118个；除README、`results/README.md`、`docs/LIMITATIONS.md`外115个逐字节不变 |
| 上游 gitlink | AdaptiveSense `f7ec30fd4721aa1a7c308f879050a83936e60067`；SensorTrust `2ce98dd043bb01ea99052eda218c68a172499a4c`，均未变更且工作树干净 |

完整提交在 [commits.json](main-release-audit/commits.json)，完整逐文件状态、旧/新Git对象、大小、行数、SHA256和审计依据在 [files.csv](main-release-audit/files.csv)。[scope.json](main-release-audit/scope.json)记录约471MB完整本地文本diff的SHA256；大diff本身仅保存在忽略的scratch中，没有再提交一份巨型补丁。使用的核心命令是 `git merge-base`、`git rev-list --left-right --count`、`git log --reverse`、`git diff --no-renames --full-index`、`git diff --numstat`、`git ls-tree -rz -l`。

| 类别 | 初始累计变更文件数 | 审查方式 |
| --- | ---: | --- |
| src | 34 | 新增代码/状态边界、AST、包导入、完整测试及冻结分支对照 |
| scripts | 73 | 入口/参数/读写路径、AST、代表性执行；未盲目导入会写远端的历史发布脚本 |
| tests | 15 | 当前完整pytest执行，保留两个严格预期失败 |
| configs | 10 | 语法/输入、冻结快照和模式语义 |
| examples | 7 | Core模式、输入、字节链路和独立接收进程 |
| results | 967 | 全CSV结构、JSON/图像/日志格式、manifest、研究快照及有限原始归档验证 |
| papers | 68 | 数值绑定、引用/交叉引用、编译、渲染与历史身份 |
| docs | 46 | 当前与历史结论、NO-GO、路径/链接及表述边界 |
| .github | 3 | 三个新增工作流与原research工作流共同审查 |
| 根目录 | 3 | 首页、贡献规则及shallow-CI来源钩子 |

约503MB是这些变更文件的工作树大小，不是声称网络下载恰好为503MB。最大单文件是约55.6MB的G1测试metrics.csv；没有超过100MB的文件。大量CSV是既有实验的有意归档，不是本轮意外生成的日志。**这是可维护性与克隆体积风险**，未来可另做存储策略设计，但本次不迁移/删减冻结证据。

本次发布补充只有本报告、机器审计侧车和三处入口文档的main发布措辞；初始1,226文件清单固定绑定3fb89be，不伪装成包含自身的递归指纹。最终新增路径和Git对象将在PR前后的本地完整diff中另行核对。

## 2. 系统源码、模式与接口

没有覆盖main已有的调度、replay、指标、C11桥接或原配置；新研究通过隔离包、包装器和显式模式入口增加。`tais_v02`、`tais_rearm`、`tais_spatial`分别服务原冻结研究，不因代码相似就删除，也不自动启用。历史实验失败与软件不能运行不是同一件事。

| 功能/模式 | 本次实际检查 | 判断 |
| --- | --- | --- |
| GateOnly | 原默认、到期读取、原始C11、实际v1收发和冻结replay parity | 通过；仍默认 |
| GateOnly+U | 显式CLI、原采样/本地检测与U上传分离、字节/接收状态 | 通过；普通数据年龄代价保留 |
| SU20 / SU30 | `tais-su high/balanced`，分别实际得到20/30候选，冻结parity | 通过；balanced名称不代表通过质量门槛 |
| SU40 | 现有`SUSender(cap=40)`，与原`benchmark_su.replay`逐记录对照 | 通过；没有编造Core CLI的40参数 |
| CSV / 逐条JSONL | 手工例子及逐条flush输入；无真值时truth指标为N/A | 通过；不补造时间轴 |
| 接收端 | 只输入实际字节的独立进程；与原理想接收计数一致 | 通过；不把sender active冒充RX知识 |
| 链路故障 | 丢弃、损坏、成对乱序；不反馈修改sender，不加入重传 | 通过；不冒称真实无线 |
| 独立基线 | Fixed复用、Delta/Variance采样历史、Rao-inspired明确简化，共享组件边界 | 测试与源码边界一致；不是完整独立端到端文献复现 |
| 导入/语法 | 37个源码子模块全部导入；127个新增Python文件及全部脚本/示例/测试AST检查 | 未发现阻断性导入/语法问题 |

参见 [core-checks.json](main-release-audit/core-checks.json)。Core CLI只选择gateonly/gateonly-u/tais-su/tais-jo；Fixed、Delta、Variance、Rao-inspired属于benchmark接口。旧help对balanced候选范围的概括不能当成实际SU40选择器，当前Quick Start已准确说明selection中的30。没有为修文字而破坏冻结入口文件指纹。

未执行全部历史脚本的顶层导入：部分`publish_*.py`会更新远端，部分历史verifier独占创建既有审计文件或要求旧快照。它们不是日常程序入口；当前脚本导航已标明。没有发现需要通过删除失败研究代码才能发布的缺陷，也没有声称完成正式的全代码安全证明。

## 3. 实验结果、原始证据和指纹

对v0.2、Rearm、OSP、Binary v1/v2、BM-1、FO-1、IRB、Core、JO、SU、G1、G2的发布分支快照逐一使用本地Git比较。已存在的源码、配置、子模块和实验数据没有后续修改；允许的根结果README属于导航。原main三处文档变更分别是首页重组、结果索引扩充、旧局限说明追加后续失败边界。

本次逐项格式扫描覆盖 **289个CSV、1,202,826个数据行、306个JSON、105个PNG**；扫描CSV列结构，不把格式通过当成每个统计推断正确的证明。还解析45个JSONL、76,490条记录，对其中1,343个实际TX帧核验长度和v1重新编解码，读取40个已提交gzip的压缩头。没有把同一运行每秒记录视为独立实验。见 [formats-checks.json](main-release-audit/formats-checks.json)。

**178项可解析的manifest指标/输出/图像哈希匹配，0个未解释数据哈希失败；234项归档/产物的首部、中部、尾部样本匹配，0个缺失样本。** 这些manifest合计声明的560,329项归档/产物指针存在重叠，不代表本轮全部重放或全部重新解码。没有重跑历史算法矩阵，也没有宣称所有原始档案逐个完整验证。G2另运行现有`verify_transfer.py --archives sample`，BM-1额外完整核验如下。详见 [evidence-checks.json](main-release-audit/evidence-checks.json)。

### 两个明确的历史元数据限制

1. `results/SHA256SUMS`的72个非索引项匹配；唯一已解释差异是被有意改写的`results/README.md`。旧清单不重写，旧索引可从94a80a1取得并验证其原始哈希。这不是CSV或图表变化。
2. **BM-1 analysis/manifest.json的outputs[manifest.json]无效。** 冻结分析器在`open('x')`之后枚举目录，此时自身仍为空，故记录了SHA256(empty)。该文件与最初5b06d2f提交逐字节相同；不能宣称它的自引用项验证通过。其余九个输出哈希均匹配。本轮另外运行原独立BM verifier：**10,800个最终运行、13,590项归档、完整原指标重新计算通过，不重跑策略**。新[独立侧车](main-release-audit/bm1-manifest-note.json)固定旧manifest本身及全部非自引用输出，并保留这个缺陷。没有修改历史生成器或伪造旧manifest。

因此这两个问题被判定为**已解释、非数值篡改的历史元数据局限**，不是阻断Core发布的未解释数据覆盖。未来若修正旧工具，应单独版本化，不能覆盖原证据。扫描结果刻意使用`PASS_WITH_DOCUMENTED_HISTORICAL_METADATA_LIMIT`，不把全体历史记录笼统标为无缺陷。

C0仓库外五个原始文件全部仍存在、大小/原始SHA256身份保持；本次复核五个完整SHA，并核对C1.1两个Greenhouse工作簿的原始SHA（含OSP实际输入），见 [external-inputs.json](main-release-audit/external-inputs.json)。未将这些原文件加入Git。OSP的正式在线时钟语义阻碍及held-out覆盖NO-GO不因本次文件核对解除。

源代码/结果按各自cohort阅读：JO健康层失败、SU balanced替代NO-GO、BM/ReferenceGate NO-GO、空间覆盖失败均保留。发送端与独立RX指标分开；FI是操作性归因而非严格物理因果。G1/G2的信号、故障、时序和真值窗口共同变化，不合并统计，也不当成真实田间泛化。二进制字节不是实测无线能量。

## 4. 论文、引用与导航

重新执行G1/G2/major-revision数值及来源检查，8个引用键/DOI的已核实元数据与正文一致。没有虚构作者/单位、资助或人类审批。当前英文稿的17页TeX在**scratch副本**成功编译，零相关LaTeX警告；全部页文字与仓库PDF相同，重新渲染17页的图像SHA全部与既有视觉审核相同，关键结果页5–8再次视觉抽查。原PDF、TeX、图表及其指纹未修改。见 [paper-checks.json](main-release-audit/paper-checks.json)。

G2的SU40−Variance F1区间跨零，稿件未把“未建立优势”误写成“已证明总体劣势”；Fixed20更高F1点估计、SU40更少字节/FI但更老数据、公共U收益均保留。G2报告旧阶段B与最终major revision的窄范围A指的是不同阶段/定义，当前导航指向最新解释，没有改旧数字。旧v0.1下载403、C0后续取得文件、C1正式在线NO-GO、OSP独立假设的时间线已区分。

对初始全部82份仓库Markdown检查759个本地链接/锚点，处理了尾斜杠目录与递归子模块的检查语义后全部有效；并非将检查器误报写成文件缺失。主要入口Markdown经过lint，Mermaid使用真实解析器检查；没有声称已做GitHub浏览器界面截图。发布修改将首页clone命令改为默认main，并去掉“main仍旧版”的过渡说明；新增本报告导航。最终增加的链接会再次检查。

## 5. 测试与CI门槛

本次新执行结果，而不是复制旧成功记录：

| 检查 | 实际结果 |
| --- | --- |
| 完整pytest | 892 passed，2 xfailed，约130.5秒；两个既有严格预期失败未删除/放宽 |
| AdaptiveSense隔离副本 | 235个Python测试通过、69项配置parity通过 |
| SensorTrust隔离副本 | 27个Python测试通过；独立C11编译，21 tests /404 checks通过 |
| Core模式和输入/RX | 通过，全部新输出在本轮scratch中 |
| 四个现有论文检查 | check_paper_artifacts、verify_paper_revision、verify_paper、verify_transfer sample通过 |
| BM-1最终保存结果独立重算 | 10,800行、13,590归档核验通过，无策略重跑 |
| 内容扫描 | 没有被Git跟踪的.venv/cache/raw/traces/scratch误入；有限token/私钥模式未命中，不冒充全面安全审计 |
| Tectonic | scratch编译/17页文本和渲染身份检查通过 |

锁定环境及最小命令来自已测试Python3.14/真实C11接口，未改依赖/参数。上游测试在临时副本运行，避免旧`reproduce_baseline.py`的固定输出覆盖历史证据。全量大规模仿真、全560,329项档案重放、自然故障/真实无线/功耗实验不属于本次执行范围。

CI流程保持四组：research、paper、transfer、paper-revision。初始3fb89be的四组运行是实际成功记录，但**不能替代本发布头部和PR合并树的CI**。最终PR须全部四组通过，不能仅看无必需检查配置就提前合并；合并后还需验证main的新SHA及其push CI。具体运行URL与合并SHA在发布PR和最终交付中记录，报告不对未来结果预填成功。

## 6. 其他分支的处理

完整17分支SHA、merge-base、左右独有提交/文件和建议见 [branches.json](main-release-audit/branches.json) 及 [远端原始快照](main-release-audit/remote-branches.json)。除main/候选本身外，**14个其他分支已是候选祖先**，不需要再次合并；包括major revision和13条研究分支。负面路线的文件进入main是为可复现，不是将它们设为默认。

| 分类 | 分支/建议 |
| --- | --- |
| 1：已经包含 | docs/tais-paper-major-revision；v0.2、Rearm、Core、JO、SU、G1、G2、Binary v1/v2、BM、FO、IRB、OSP等所有对应研究分支；保留原分支指针 |
| 3：已包含但主要作为失败/边界证据 | BM-1、ReferenceGate、OSP、JO默认替代等；不能因整合而改成GO |
| 2并需4类独立处理 | docs/tais-research-portfolio，独有2fefb73一提交；三点diff为32路径，其中31个portfolio文件及根README入口。共享58项来源哈希与现候选一致，但其材料固定在f21bc2f、用途为日英研究展示，未包含后续JO/SU/G1/G2/最新论文；不能盲目合并旧首页或视为最新论文 |

Portfolio有有效的独有说明、日英PDF、图与审查材料，应保留原分支。其整体PDF/渲染器/旧快照保护逻辑未纳入本轮正式发布验证，因此**不复制进main、不删除分支**。这不是认定资料无效，也不是假定与候选等价；如以后发布该作品集，需独立适配其快照标识和校验范围。本次不批量合并任何研究分支。

## 7. 风险、修复与最终判断

本轮必要修复是默认main使用的入口措辞、clone命令和审计导航；没有运行时或科研数值修复。初始所有文件逐项有机器清单和类别审计依据，不以一个CI绿灯代替完整范围审查。

保留风险：仓库体积较大；旧脚本有固定输出/历史保护范围；本地原档案不随clone分发；旧自引用manifest无效；研究结论来自项目定义的合成任务；论文作者/人类终审/渠道适配尚未完成；无真实无线、硬件时延/RAM或功率测量。详见各报告，不对外宣称产品部署、普遍最优或实际电池寿命收益。

**发布方案：建议将候选完整累积成果与本轮审计侧车进入main，保持GateOnly默认，保留所有负面证据和隔离研究包；portfolio继续独立。** 未发现阻断性的Core功能、未解释历史覆盖、上游异常或数据篡改。本地审计门槛已满足。执行时必须再次取得最新main和候选SHA、创建以原候选分支为源的PR、核对完整本地diff、等待最终PR CI、以匹配的head SHA进行普通merge（保留研究提交历史），禁止force/reset或管理员跳过失败检查。若发现新变化/冲突/必要检查失败即停止。

合并后重新读取PR状态、main SHA和main CI；保留全部研究分支，不进行分支清理。可复现入口仍为[Quick start](QUICKSTART.md)、[脚本](../scripts/README.md)、[结果](../results/README.md)与[论文](../papers/tais/README.md)。

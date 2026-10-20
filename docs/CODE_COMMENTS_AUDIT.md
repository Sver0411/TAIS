# PR #2 冻结源码兼容性修复审计

本报告描述修复后的最终文件状态，取代 `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` 中“92 个源码文件保留注释、CI 因源码冻结失败”的旧交付结论。旧提交保留在历史中，不强制推送或重写。

## 结论与范围

开始时实际确认：工作区干净，当前分支 `docs/code-comments-maintenance`，HEAD 和远程 PR #2 均为 `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b`；本地与最新远程 main 均为 `80914638ab1d3d0ccca135a05de76be137779b1a`。merge-base 为该 main，PR 领先 1 个提交、落后 0 个，PR OPEN/Draft、目标 main。未切换分支、合并、改写历史或操作远程 main。

当前 main 基线有 1,357 个条目（1,355 个普通文件和 2 个 vendor gitlink），自有代码 145 个（144 Python、1 C，无自有头文件）。原注释提交改动其中 92 个源码文件。本次逐项诊断后：

- **82 个受保护源码文件恢复为指定 main 的精确字节**；不是恢复到任意旧研究版本。
- **10 个未受相应冻结保护的文件保留原 PR 的英文 docstring**，与原注释提交逐字节一致，没有再次编辑或改变逻辑。
- 其余 **53 个自有代码文件原本就未改动**。
- 82 个文件的有用解释完整迁至 6 篇英文 Markdown，包含接口、单位、状态、协议、边界、统计与副作用说明。
- 修订本报告、inventory.csv、checks.json；新增 freeze-diagnosis.csv。相对 main 最终仅 10 个注释源码文件与 10 个文档/审计文件存在差异。

不修改测试期望、断言、skip/xfail、冻结配置、历史指纹、实验数字、论文或第三方源码。验证器中保留的差异仅为原 PR 已有 docstring；没有修改其执行语句。

## 失败追踪：不同断言承担不同职责

诊断不是将所有失败概括为“注释不影响行为”。重新取得原提交 4 个 PR CI 的失败日志，并核对对应 4 个 push CI；具体保护链如下。

| 断言/工具 | 类型和预期值来源 | 原 PR 的具体失败/潜在后续失败 | 修复方式 |
| --- | --- | --- | --- |
| `test_prototype.py::test_pinned_sources` | 检查两个 vendor 的提交 SHA，不是本文件内容哈希 | 原 CI 没在此失败；两个 SHA 正确。本测试文件另被 G1 historical-protection 保护 | 保持子模块；恢复该文件，重跑测试 |
| `conftest.py::pytest_sessionstart` | CI 浅克隆中补取固定 IRB commit；本地不取网络；自身被 G1 historical-protection 保护 | 不是原两个失败断言，但原 docstring 改变历史完整性表中其字节 | 恢复 main；不变更取 commit 逻辑或网络边界 |
| `test_old_freeze_is_unchanged` | `benchmark_transfer.inherited()` 对 `results/tais-paper/selection.json` 的 sources 做当前文件 SHA-256 校验 | G1 锁定源码被注释修改 | 恢复所有被引入的锁定文件 |
| `test_disabled_exact_legacy_and_frozen_sources` | 先比较 disabled-v0.2 与 legacy 运行输出，再遍历 `results/v0.2/legacy_source_hashes.json` | 输出比较未失败；后续源码哈希失败 | 恢复预期源码，保留测试与指纹 |
| `verify_paper.py` | G1 selection sources；随后 historical-protection.files 检查既有文件 | 原 CI 首先停在 sources；恢复该层后还必须满足广泛历史完整性表 | 同时处理两层保护，而非只处理首个失败文件 |
| `verify_transfer.py` | G2 selection 中 inherited_sources、sources、operating points、提交中的 selection，以及 BASE 目录差异约束 | 原 transfer CI 先在 inherited 测试中停止，后续保护同样适用；src 不能任意保留注释 | 恢复 G1/G2 相关文件及所有受目录约束的 src |
| `verify_paper_revision.py` | `results/tais-paper-review/protection.json` 的 protected_files，另有 src/config/vendor/result 的 Git diff 断言 | 原 CI 首个报告 `src/tais/budget_eval.py`，并非只有这个文件受保护 | 恢复全部相关源码；保护表和目录断言不变 |
| `check_paper_artifacts.py` | 保存的来源哈希、引用键/DOI 缓存、CSV 单元格、预算表和 PDF 存在性 | 原 PR 此检查可通过，不属于源码注释冲突 | 只读重跑；不调用会写 bibliography 的 references 工具 |
| 其他 historical manifests/source maps | 不同研究时点的独立精确快照 | 某些旧快照本就与当前 main 不同，不能当作本轮新失败或强迫 main 退回那个版本 | 逐文件记录来源与旧快照差别，仅恢复指定 main |

完整逐文件诊断表：[freeze-diagnosis.csv](code-comments-audit/freeze-diagnosis.csv)，包括路径、是否字节保护、所有扫描到的保护来源、基准/注释哈希、与 main 一致或不同的历史记录数、原失败原因和处理方案。原始日志确认：research 为 890 passed/2 failed/2 xfailed；transfer 为 68 passed/1 failed；paper 与 revision 分别在上述指纹处失败。它们属于旧提交，不作为本次成功证明。

进一步检查了 JSON 锁和 manifest 中的路径哈希、源码/配置目录差异规则，以及验证器的导入链。10 个保留文件未出现于这些精确来源列表或目录约束；其中论文 writer 的副作用说明保留，但没有导入或执行这些 writer。实际运行的 3 个验证器及 artifact checker 均确认默认调用只读，没有传入写报告/写历史目录选项。

## 文件最终状态

[完整 inventory.csv](code-comments-audit/inventory.csv) 以 main 为基准逐条记录 1,357 个原条目，给出基准、原注释 PR、最终哈希，恢复/保留状态，以及迁移文档。新建审计/迁移文件在 [checks.json](code-comments-audit/checks.json) 单独列出，避免清单自身哈希的循环依赖。

| 目录 | 恢复为 main | 保留注释 | 原本未改 |
| --- | ---: | ---: | ---: |
| 根目录 | 1 | 0 | 0 |
| examples/tais-core | 5 | 0 | 0 |
| scripts | 28 | 10 | 41 |
| src/tais | 23 | 0 | 1 |
| src/tais_rearm | 5 | 0 | 0 |
| src/tais_spatial | 6 | 0 | 1 |
| src/tais_v02 | 6 | 0 | 0 |
| tests | 8 | 0 | 10 |
| 合计 | 82 | 10 | 53 |

### 保留英文 docstring 的 10 个文件

- `scripts/analyze_budget_sensitivity.py`。
- `scripts/build_paper.py`。
- `scripts/build_paper_report.py`。
- `scripts/build_transfer_paper.py`。
- `scripts/paper_review_artifacts.py`。
- `scripts/update_transfer_docs.py`。
- `scripts/verify_paper.py`。
- `scripts/verify_paper_references.py`。
- `scripts/verify_paper_revision.py`。
- `scripts/verify_transfer.py`。

### 恢复原样的 82 个文件

- `.`：`conftest.py`。
- `examples/tais-core`：`historical_review.py`, `receiver.py`, `run.py`, `verify_delivery.py`, `view_run.py`。
- `scripts`：`analyze_budget_matched_results.py`, `analyze_paper.py`, `analyze_su.py`, `audit_budget_seeds.py`, `benchmark_joint_optimization.py`, `benchmark_paper.py`, `benchmark_su.py`, `benchmark_transfer.py`, `build_report.py`, `diagnose_joint_history.py`, `greenhouse.py`, `import_joint_csv.py`, `offline_spatial.py`, `paper_metrics.py`, `publish_blocked_branch.py`, `publish_exact_git_objects.py`, `publish_research_branch.py`, `rearm_run.py`, `rearm_verify.py`, `run_budget_matched_experiment.py`, `run_experiments.py`, `summarize_results.py`, `transfer_metrics.py`, `v02_run.py`, `v02_verify.py`, `verify_artifacts.py`, `verify_independent_reference_budget.py`, `verify_su.py`。
- `src/tais`：`budget_eval.py`, `config.py`, `core_stream.py`, `joint_policy.py`, `joint_sampling.py`, `joint_upload.py`, `metrics.py`, `observability_eval.py`, `observability_signals.py`, `paper_baselines.py`, `reference_metrics.py`, `reference_policy.py`, `reference_signals.py`, `replay.py`, `scheduler.py`, `signals.py`, `su_policy.py`, `transfer_signals.py`, `trust.py`, `trust_bridge.c`, `wire_codec.py`, `wire_link.py`, `wire_v2.py`。
- `src/tais_rearm`：`__init__.py`, `config.py`, `evidence.py`, `replay.py`, `scheduler.py`。
- `src/tais_spatial`：`analysis.py`, `data.py`, `interventions.py`, `io.py`, `methods.py`, `pilot.py`。
- `src/tais_v02`：`__init__.py`, `config.py`, `evidence.py`, `forensics.py`, `replay.py`, `scheduler.py`。
- `tests`：`test_offline_spatial.py`, `test_paper_baselines.py`, `test_prototype.py`, `test_reference_budget.py`, `test_transfer_benchmark.py`, `test_transfer_signals.py`, `test_wire_codec.py`, `test_wire_v2.py`。

恢复文件均与 main 字节相同，不再计为本 PR 最终修改源码。原 `src/tais/paper_baselines.py` 模块头的独立性说法也保持冻结字节；更精确的“独立采样决策类与复用公共组件的适配器不同”说明保存在外置文档，不能用恢复的旧头部推出更强的独立性结论。

### 迁移说明位置

| 新文档 | 对应内容 |
| --- | --- |
| [core-stream.md](code-comments-audit/core-stream.md) | Core 的实际采样、返回值、journal、帧发送、接收端状态与示例 |
| [health-diagnostics.md](code-comments-audit/health-diagnostics.md) | C11 score/state/flags、秒与毫秒、opaque context 所有权和调用前置条件 |
| [wire-protocol.md](code-comments-audit/wire-protocol.md) | v1 数值/null/布局，v2 连续性、会话、恢复和协议测试辅助语义 |
| [sampling-policies.md](code-comments-audit/sampling-policies.md) | GateOnly/JO/SU/U、空闲上限、候选/BLOCKED/rearm、进程内 patch 边界 |
| [experiment-evaluation.md](code-comments-audit/experiment-evaluation.md) | G1/G2、参考/空间干预、独立/装饰基线、真值、指标、预算、bootstrap 与资源模型 |
| [frozen-source-contracts.md](code-comments-audit/frozen-source-contracts.md) | 源码冻结职责、conftest、工具/测试契约、导入即写入或远程发布的历史工具警示 |

每篇文档链接实际源码；每个恢复文件至少对应一节。迁移保留原 PR 新增/修订 docstring 和新增关键注释，而不是空索引。说明没有变成新算法、参数调整、真实现场或无线能耗主张。

## 历史保护与行为保持

- 82 个恢复文件：最终内容与 main **逐字节一致**。
- 10 个保留文件：最终内容与 `89c7c404` **逐字节一致**；相对 main 的差异仍仅为英文 docstring。AST 去除真正的首个 docstring 后一致，有效代码 token 一致；不忽略普通字符串、常量或测试语句。
- 135 个自有代码文件最终与 main 字节相同，另 10 个只有上述注释差异。全部 144 个 Python 文件编译语法；C11 适配器恢复原文后严格编译，并运行原版 native tests。
- 1,345 个原普通文件和两个子模块与 main 保持相同（1,355 普通文件减去 10 个保留注释文件）。配置、results、papers、README、workflows、vendor 无差异，历史报告/协议和参考文献未改。
- 没有修改原始 selection、source hash、protected_files、manifest、测试期望或断言。验证器执行逻辑也未修改。
- 所有维护输出在独立 `results/scratch/pr2-freeze-repair-20261021/`、pytest 临时目录或忽略的 build/cache 内；没有重写历史结果。

## 本次实际验证

| 检查 | 本次实际结果 |
| --- | --- |
| Python 编译语法 | **通过：144 文件** |
| C11 严格编译及原版 native tests | **通过：21 tests、404 checks** |
| 针对性冻结/组件测试 | **22 passed、0 failed** |
| 完整 pytest | **892 passed、0 failed、2 xfailed，394.55 秒**；没有新增失败 |
| `verify_paper.py` | **PASS**：73,800 既存评分行；sources、历史表、视图/预算一致。仅 README 两个既有导航差异由原断言原样允许 |
| `verify_transfer.py` | **PASS**：12,880 既存评分行、26,880 event rows、14,868 fault rows；冻结来源通过 |
| `verify_paper_revision.py` | **PASS**：202 保护文件、60 预算配对、506 审稿数值单元格及交叉引用 |
| `check_paper_artifacts.py` | **PASS**：8 个引用、909 单元格、5 来源指纹及已存 PDF |
| 源码字节身份 | **通过**：82 恢复文件等于指定 main；10 保留文件等于原注释 PR |
| 执行语义 | **通过**：原 92 个注释差异重新溯源；保留 10 文件 AST/有效 token 与 main 一致；另 135 自有代码文件字节相同 |
| 英文说明、证据/子模块、diff 空白 | **通过** |
| Markdown/路径 | **通过**：7 份文档、123 个本地链接、82 文件迁移覆盖；MD013 关闭，MD024 按同级标题检查 |
| 远程 CI | 本提交发布前尚未执行；本地必要检查通过后才推送。最新 SHA 的 4 条工作流最终状态与链接由 PR 检查区及最终交付单独记录 |
| 未执行项 | 完整 G1/G2、调参、历史绘图、论文编译、全部忽略档案重验及有历史写入/远程发布副作用的工具 |

三个历史验证器检查的是已存在的 73,800 个 G1 评分行、12,880 个 G2 评分行及 202 个修订保护文件等证据，**没有重新运行这些研究实验**。没有启用全部原始 archives 核验；不能将这次通过描述成所有忽略大日志的重新完整复验。论文引用核验使用保存的 Crossref metadata/DOI 缓存和正文键值，不联网重建参考文献。

### 检查命令和副作用边界

```sh
python -m pytest -q tests/test_transfer_benchmark.py::test_old_freeze_is_unchanged tests/test_v02.py::test_disabled_exact_legacy_and_frozen_sources tests/test_prototype.py::test_pinned_sources tests/test_paper_baselines.py
python scripts/verify_paper.py
python scripts/verify_transfer.py
python scripts/verify_paper_revision.py
python scripts/check_paper_artifacts.py
python -m pytest -q
cc -std=c11 -Wall -Wextra -Werror -fsyntax-only -I vendor/SensorTrust/core src/tais/trust_bridge.c
git diff 80914638ab1d3d0ccca135a05de76be137779b1a --check
git diff 80914638ab1d3d0ccca135a05de76be137779b1a -- configs results papers vendor README.md .github
```

Python 全源码语法通过在内存中 compile 执行；上列 C 命令之外，还将原版 `sensor_trust.c` 和 `tests/test_core.c` 编译到独立 scratch 并实际执行。新文档链接和 Markdown 另行检查。最后一条受保护路径差异应无输出。

没有调用 `verify_paper_references.py`（会写参考文献），没有导入或执行 `publish_exact_git_objects.py` 或其他历史远程 publisher，也没有运行历史 proof writer、完整 G1/G2、参数搜索、历史绘图或论文编译。

## 未解决事项和合并前约束

- 当前精确源码保护与注释维护的冲突通过外置说明解决，不放宽保护规则。未发现仍需改变保护机制才能解决的当前 CI 失败；以最终实际检查为准。
- 原有两个高阈值 rearm xfail 保留，不能把预期失败当作算法问题已经修复。
- 外置契约需要随将来的合法算法变更同步审阅；它不是运行时接口自动验证，也不是原始论文方法忠实复现证明。
- 未重新证明自然农业事件、自然故障、真实到达时钟、无线可靠性或电流/电池寿命；既有研究局限和 NO-GO 均保留。
- 历史快照可能针对不同旧提交，不能要求所有旧工具在当前 main 上无条件成立。当前涉及本 PR 的冻结断言、四条工作流与必要回归均需要实际验证。
- PR #2 始终保持 OPEN、base 为 main。本任务不合并或推送 main；仅全部必要检查通过后才可将 Draft 调整为 Ready for review。提交前的本地结果写入本报告；发布后最新 SHA 的 CI 链接和状态在 PR 检查区及最终交付中核验，不能用旧提交状态替代。

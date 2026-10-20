# 全仓库代码注释与可读性维护审计

本轮基于远程及本地一致的 `main`：`80914638ab1d3d0ccca135a05de76be137779b1a`，在干净工作区创建 `docs/code-comments-maintenance`。原始目录有 1,357 个 Git 跟踪条目；自有代码实际为 144 个 Python 文件、1 个 C 文件，没有自有头文件。源码、运行脚本、示例、测试辅助代码与 vendor、配置、证据和论文边界均按当前 Git 清单重新检查。

维护范围已完成：92 个源码文件仅增改英文注释/docstring，53 个自有代码文件检查后保留。没有改动算法、签名、CLI 参数、阈值、配置、随机种子、实验 CSV、历史记录、论文内容或子模块引用。新增本报告及两份审计清单；现有 README、研究报告、论文和协议均未修改。分支仅供 PR 审查，不合并 main。

## 文件审计

完整逐文件清单：[inventory.csv](code-comments-audit/inventory.csv)。包括每个基准条目的类别、检查深度、修改状态、docstring/comment 标记、前后 SHA-256 或 gitlink、语义一致性结果。目录统计和检查摘要：[checks.json](code-comments-audit/checks.json)。新增审计文件本身不属于原始清单。

| 目录 | 自有代码 | 增改说明 | 保留 | docstring 文件 | 注释文件 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 根目录 | 1 | 1 | 0 | 1 | 0 |
| examples/tais-core | 5 | 5 | 0 | 5 | 1 |
| scripts | 79 | 38 | 41 | 38 | 0 |
| src/tais | 24 | 23 | 1 | 22 | 7 |
| src/tais_rearm | 5 | 5 | 0 | 5 | 0 |
| src/tais_spatial | 7 | 6 | 1 | 6 | 0 |
| src/tais_v02 | 6 | 6 | 0 | 6 | 1 |
| tests | 18 | 8 | 10 | 8 | 0 |
| 合计 | 145 | 92 | 53 | 91 | 9 |

同一个文件可以同时补充 docstring 和注释；上表两列不可相加作为修改文件总数。C 文件记入注释而非 Python docstring。

检查深度：全部自有代码执行语法/AST、现有模块说明、公共接口和入口副作用梳理；核心状态机、协议、指标与关键适配器结合源代码和测试详细核对。没有声称形式化证明所有研究工具的每条公式，也不要求每个显而易见的辅助函数都添加 docstring。保留文件已有的模块定位、直观辅助实现或测试断言足以满足其本轮用途。没有尚未完成的结构/接口检查文件。

### 已增改文件

- `.`：`conftest.py`。
- `examples/tais-core`：`historical_review.py`, `receiver.py`, `run.py`, `verify_delivery.py`, `view_run.py`。
- `scripts`：`analyze_budget_matched_results.py`, `analyze_budget_sensitivity.py`, `analyze_paper.py`, `analyze_su.py`, `audit_budget_seeds.py`, `benchmark_joint_optimization.py`, `benchmark_paper.py`, `benchmark_su.py`, `benchmark_transfer.py`, `build_paper.py`, `build_paper_report.py`, `build_report.py`, `build_transfer_paper.py`, `diagnose_joint_history.py`, `greenhouse.py`, `import_joint_csv.py`, `offline_spatial.py`, `paper_metrics.py`, `paper_review_artifacts.py`, `publish_blocked_branch.py`, `publish_exact_git_objects.py`, `publish_research_branch.py`, `rearm_run.py`, `rearm_verify.py`, `run_budget_matched_experiment.py`, `run_experiments.py`, `summarize_results.py`, `transfer_metrics.py`, `update_transfer_docs.py`, `v02_run.py`, `v02_verify.py`, `verify_artifacts.py`, `verify_independent_reference_budget.py`, `verify_paper.py`, `verify_paper_references.py`, `verify_paper_revision.py`, `verify_su.py`, `verify_transfer.py`。
- `src/tais`：`budget_eval.py`, `config.py`, `core_stream.py`, `joint_policy.py`, `joint_sampling.py`, `joint_upload.py`, `metrics.py`, `observability_eval.py`, `observability_signals.py`, `paper_baselines.py`, `reference_metrics.py`, `reference_policy.py`, `reference_signals.py`, `replay.py`, `scheduler.py`, `signals.py`, `su_policy.py`, `transfer_signals.py`, `trust.py`, `trust_bridge.c`, `wire_codec.py`, `wire_link.py`, `wire_v2.py`。
- `src/tais_rearm`：`__init__.py`, `config.py`, `evidence.py`, `replay.py`, `scheduler.py`。
- `src/tais_spatial`：`analysis.py`, `data.py`, `interventions.py`, `io.py`, `methods.py`, `pilot.py`。
- `src/tais_v02`：`__init__.py`, `config.py`, `evidence.py`, `forensics.py`, `replay.py`, `scheduler.py`。
- `tests`：`test_offline_spatial.py`, `test_paper_baselines.py`, `test_prototype.py`, `test_reference_budget.py`, `test_transfer_benchmark.py`, `test_transfer_signals.py`, `test_wire_codec.py`, `test_wire_v2.py`。

### 检查后保留文件

- `scripts`：`analyze_fault_event_observability.py`, `analyze_independent_reference_budget.py`, `analyze_joint_optimization.py`, `analyze_transfer.py`, `audit_observability_seeds.py`, `audit_reference_budget.py`, `audit_transfer_seeds.py`, `audit_wire_health.py`, `benchmark_wire_codec.py`, `benchmark_wire_v2.py`, `build_transfer_report.py`, `check_paper_artifacts.py`, `inspect_joint_cases.py`, `inspect_v02_results.py`, `joint_secondary_audit.py`, `paper_publication_figures.py`, `rearm_audit_seeds.py`, `rearm_diagnose.py`, `rearm_plot.py`, `rearm_report.py`, `rearm_summarize.py`, `replay_joint_frozen.py`, `report_fault_event_observability.py`, `report_independent_reference_budget.py`, `report_offline_spatial.py`, `reproduce_baseline.py`, `reproduce_paper.py`, `reproduce_transfer.py`, `run_fault_event_observability.py`, `run_independent_reference_budget.py`, `transfer_figures.py`, `v02_forensics.py`, `v02_identifiability.py`, `v02_report.py`, `v02_seed_audit.py`, `v02_summarize.py`, `verify_budget_matched_experiment.py`, `verify_fault_event_observability.py`, `verify_joint_delivery.py`, `verify_offline_spatial.py`, `verify_wire_v2_results.py`。
- `src/tais`：`__init__.py`。
- `src/tais_spatial`：`__init__.py`。
- `tests`：`test_budget_matched.py`, `test_core_stream.py`, `test_greenhouse_helper.py`, `test_joint_policy.py`, `test_observability.py`, `test_paper_revision.py`, `test_rearm.py`, `test_reporting.py`, `test_su_policy.py`, `test_v02.py`。

### 跳过的受保护条目

完整路径均在清单中，标为 `skipped_protected`；这里只检查边界/完整性，不为覆盖率修改这些内容：

- `vendor/AdaptiveSense`、`vendor/SensorTrust`：第三方 gitlink 和干净状态保持不变，未修改第三方源码、头文件或许可证。
- `results/`：跟踪的历史 CSV、图表、manifest、SHA256SUMS、失败记录、NO-GO 和其他证据。
- `papers/`：论文、PDF、BibTeX、图表、表格和生成材料。
- `configs/`：冻结配置与实验参数。
- 现有 `docs/`、README、引用库、CI 工作流和其他非代码文件。
- 忽略的原始数据/历史大日志、缓存及生成文件：没有进行注释改写，也没有重新生成历史图表或大规模研究结果。未对全部忽略的原始档案重新计算哈希；不能把本轮检查描述为所有本地大日志的完整复验。

## 可读性改进

1. **Core 链路**：实际采样前只检查时间戳；稀疏输入采用到期后的第一行，不插值。区分本地事件、首次上传报告、真实编码帧和接收端已解码状态；明确跳过行返回 None、关闭 C 上下文、重复/乱序/冲突帧的处理。
2. **健康与事件**：C11 score 是启发式评分，flags/state 不等于真实物理故障或环境事件。说明稳定偏移无专用类型位、恢复重置不能恢复被故障遮蔽的信息。
3. **采样/上传模式**：GateOnly、JO-S、H/U 消融和 SU 的共享关系；20/30/40 是空闲上限，不是固定周期。`balanced` 读取保存候选，名称不证明质量门通过；CLI 和 API 的 SU40 可达性不同。U 基于最后发送值及状态边沿，score-only 不强制发送，心跳只在采样时检查。
4. **状态与恢复**：v0.2 候选的固定参考、符号、持续时间/计数、BLOCKED 生命周期；rearm 只对已观测的未确认参考返回解除阻塞，取消样本不能沿用旧 debounce 当作事件。进程内补丁不适合共享模块的并发线程。
5. **协议**：v1 的数值类型、null 与健康缺席区别、布局与规范 varint；v2 独立会话、序号、健康 delta 连续性、冲突和缺口。快照恢复当前状态，不恢复全部历史；CRC 不提供认证，本地链路没有 ACK/无线能耗保证。
6. **研究语义**：G1/G2 的 latent/noisy/observed 与故障/事件标签分离；G1 幅值限定真值和 G2 外生支持窗口不同。独立决策类与共享检测/C11/U 实验适配版本明确区分，Rao-inspired 不冒充忠实复现。参考信息不足保持 undecided；空间数据时间轴是显式 proxy 假设，干预不等于自然现场真值。
7. **统计与成本**：micro counts、整种子配对 bootstrap、条件延迟和无事件时未定义 Recall；不同历史汇总的平均方式不冒称同一 estimand。样本周期、单传感器参考读取、JSON 与实际 Binary 字节按具体实验区分。参数化加性成本是条件模型，不是实测电池结论。
8. **工具副作用**：标明导入时写文件的论文/报告工具、Crossref 工具，以及固定目标分支的历史发布器。尤其 `publish_exact_git_objects.py` 会写 main，不能被当作通用维护上传入口。本轮未调用这些历史远程发布脚本。

## 行为和证据保持核验

- 对所有 144 个 Python 文件在内存中编译语法。对修改文件比较去除首个 docstring 后的 AST，并比较剔除注释/docstring/空白后的有效 token；两种结果均一致。没有通过忽略所有字符串掩盖参数或常量变化。允许 `__doc__`、help 显示、源码行号和源码哈希随说明变化。
- C 源码去注释比较一致；Apple Clang 的预处理输出去空白后也一致（原始预处理文本只有开头空行差别）。`-std=c11 -Wall -Wextra -Werror -fsyntax-only` 通过；原版 C11 单元测试 21/21、404 checks 通过，Python 回归也实际编译/调用适配器。
- 独立进程分别从基准提交提取的原始源码和维护源码运行代表性比较：G1/G2 各 4 场景，每场景 11 方法，共 88 次运行；连同 8 份生成输入形成 96 份 SHA-256 摘要，完全一致。摘要包括采样决策/报告、指标、实际 Binary 帧、独立接收端状态、事件匹配和数据年龄。使用既有工程种子 20/690，不是新泛化实验。
- 7 个 CLI smoke：GateOnly、GateOnly+U、JO-S、JO-HS、JO-Full、SU high、SU balanced。全部 COMPLETE，实际帧与所选策略重放一致。CSV/逐条输入、接收端解码、异常帧与因果性由现有测试覆盖。
- 所有新增/改写代码 comment/docstring 逐 token/AST 提取检查，无新增中文；对新增英文说明人工复核与代码契约一致。
- 92 个源码文件以外的 1,263 个原有普通文件 SHA-256 全部不变；2 个子模块引用和工作区保持原样。清单保留每个前后哈希，不用源文件哈希变化推断实验数据被篡改。
- `git diff --check` 通过；差异范围仅注释/docstring 和本轮新审计材料。没有格式化或修改测试期望。
- `check_paper_artifacts.py` 通过：8 个引用、909 个结果单元格、5 个源证据指纹及已存 PDF。论文没有重编译或改写，本轮不做排版/外部 DOI 网络复核。

### 冻结源码检查与运行回归分开

`verify_paper.py`、`verify_transfer.py`、`verify_paper_revision.py` 实际运行均在原始源码字节保护处失败。其断言继续生效，历史 selection/protection/manifest 均未更新。这些失败表示当前注释源码不再是原冻结字节快照；配合 AST/token、确定性运行和受保护材料哈希检查，没有证据表明运行逻辑或旧实验数据发生变化。

现有部分单元测试和四条 GitHub Actions 工作流同样包含字节保护，因此不能承诺注释维护后现有 CI 全绿。不能修改冻结指纹或测试期望来规避它们，也不能将这些失败删除、跳过后宣称全部通过。

历史复现仍应检出各 manifest 的 `source_commit`/锁定版本再执行对应命令。后续若要在持续维护的 main 上同时保留归档验证和当前运行回归，需要另行审计 CI 的两种职责；本轮没有改动 workflow 或放宽任何保护规则。

## 检查结果记录

| 检查 | 实际结果 |
| --- | --- |
| Python 语法、AST 和有效 token | 通过：144 文件语法；91 修改 Python 文件语义/token 一致 |
| C 编译/预处理/原版测试 | 通过：21 tests、404 checks |
| 固定最终源码的完整 pytest | **890 passed、2 failed、2 xfailed，276.26 s** |
| 两项失败 | `test_old_freeze_is_unchanged`；`test_disabled_exact_legacy_and_frozen_sources`，均在原始源码哈希断言处失败 |
| 因果性、时间戳、协议、预算/指标、Core/CSV/JSONL 等运行回归 | 通过的 890 项覆盖这些接口；未发现功能输出回归。不能因此将完整 pytest 标为通过 |
| FO-1 运行中指纹影响复核 | 固定源码后的最终全量运行通过该项 |
| 原始/维护源码确定性对照 | 通过：88 运行、8 输入、96 摘要一致；摘要见 checks.json |
| Core CLI smoke | 通过：7 模式，实际帧/策略重放一致 |
| 论文数据只读检查 | 通过：909 单元格、8 引用和 5 源指纹 |
| 三个历史源码冻结验证器 | **失败**：均为源码字节保护；冻结记录保持原样 |
| 英文说明审计、受保护文件、子模块、diff 空白 | 通过 |
| 本报告 Markdown、两个本地链接、清单路径 | 通过；单文档直接 lint，MD013 关闭；1,357 清单条目存在 |
| GitHub Actions | 提交时尚未运行；最终 push/PR 检查链接及结果记录在 PR。原有工作流包含上述字节冻结，预期无法全绿；不更改工作流以掩盖失败 |
| 大规模研究、搜索、历史绘图和论文重编译 | 未执行；不属于本轮验证范围 |

## 未解决事项与维护边界

- **CI 兼容性待单独处理**：精确历史源码身份与在原文件中添加注释的要求冲突。建议保留原始记录，在独立后续变更中验证“冻结版本的归档身份”和“当前源码的行为回归”两个明确对象；不可简单接受任意新哈希。本 PR 不宜在现有必要检查失败时直接合并。
- **低层接口前置条件**：直接使用 SensorTrust 包装器需要调用方保证 uint64 毫秒范围、有效 context 生命周期和串行访问。Core 已有更严格的时间边界校验；本轮只记录契约，没有增加 guard 或声称未经证明的线程安全。
- **真实数据假设仍需外部证据**：时间戳的真实采集/到达语义、自然故障标签、现场环境事件真值、无线功耗均不能从代码推出。保留未验证状态。
- **历史脚本架构**：部分工具导入即写入，重复的旧实验统计器和进程局部 patch 仍存在；这里解释差异与风险，没有重构或合并实现。
- **测试运行过程**：首次全量 889 passed / 3 failed / 2 xfailed；其中 FO-1 测试在运行中记录了源码指纹，后续注释写入使第二次调用先触发身份校验。固定最终源码后重新运行以排除此维护时序影响；最终结果见上表。两个高阈值 rearm xfail 是原有已知限制。

未运行完整 G1/G2、参数搜索、全部历史归档重放、自然现场/无线/功率实验；没有把维护检查描述为这些验证。

## 复核命令

在仓库根目录、已初始化子模块及安装锁定依赖的环境中：

```sh
python -m compileall -q src scripts examples tests conftest.py
cc -std=c11 -Wall -Wextra -Werror -fsyntax-only -I vendor/SensorTrust/core src/tais/trust_bridge.c
python -m pytest -q
python scripts/check_paper_artifacts.py
git diff 80914638ab1d3d0ccca135a05de76be137779b1a --check
git diff 80914638ab1d3d0ccca135a05de76be137779b1a -- configs results papers vendor README.md .github
```

最后一条对本轮分支应无输出。全量 pytest 中历史字节保护失败必须原样报告。不要为验证注释而运行固定历史目录的生成/报告/发布脚本。

修改 Python 文件的 AST 等价性可独立复核（只删除各作用域首个真正 docstring，不忽略普通字符串）：

```python
import ast
import pathlib
import subprocess

base = "80914638ab1d3d0ccca135a05de76be137779b1a"

class StripDocs(ast.NodeTransformer):
    def generic_visit(self, node):
        super().generic_visit(node)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                value = node.body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    node.body.pop(0)
        return node

paths = subprocess.check_output(["git", "diff", "--name-only", base], text=True).splitlines()
for name in paths:
    if name.endswith(".py"):
        old = subprocess.check_output(["git", "show", base + ":" + name], text=True)
        new = pathlib.Path(name).read_text()
        assert ast.dump(StripDocs().visit(ast.parse(old))) == ast.dump(StripDocs().visit(ast.parse(new))), name
print("AST equivalence passed")
```

本报告新增材料与英文代码说明分开管理。最终状态应以 PR、提交与 checks.json 中记录的真实验证结果为准，不以“已推送”替代审核。

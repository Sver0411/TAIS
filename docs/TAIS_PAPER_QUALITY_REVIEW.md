# Paper reviewer audit and revisions

<!-- TRANSFER_CURRENT_START -->
## Final cross-generator reviewer audit

**最终判断：B——论文完整，但部分结果不稳健。** 第二生成器改变了值得发表的理由：G1中“SU40在近似预算下对Variance具有F1优势”不能推广到G2；应改为可复现的有条件系统权衡、竞争基线和失败边界研究。G2中SU40 F1为46.31%，Variance为50.63%，实际采样差-0.74%，SU40−Variance F1差-4.32pp，95%CI [-9.11, +0.18] pp，包含零；Recall差的区间[-14.58, -2.97] pp完全低于零。Fixed-20的F1为55.10%，采样差-2.65%，也不支持SU40等采样质量优越（固定点未预声明配对区间，此处是描述性比较）。

SU40相对GateOnly的F1差区间[+0.39, +8.75] pp仍支持这一生成机制内的条件改善，但增加14,513次采样和20次诱发误报，且Recall差区间[-0.21, +10.31] pp跨零。相对TrustLog的F1区间[+1.82, +9.99] pp为正，采样增加+4.40%，不能延用G1中采样同时降低的说法。SU40相对Variance的字节降低67.92%、诱发误报降低56.51%，同时P95年龄53→113s；这是资源/信息权衡，部分来自可共享的U模块。

SU20 F1/Recall为65.30%/66.30%，相对SU40采样增加43.84%，FI 157→193。SU20短事件Recall仅37.34%，虽然覆盖率达92.34%；SU40短事件Recall 9.22%还低于GateOnly 9.69%。全支持被替换的52个事件在Gate/SU20/SU40中均未检出。稳定偏移无专用类型位，温湿度也不应被假定同等诊断效果。

该研究仍有可考虑投稿的内容：端到端可复现、真正独立调度基线、完整字段通信与独立接收端审计，以及跨机制负面证据。不能以新检测理论、普遍优效、真实田间泛化或实际节能为卖点。保持Simulation-Based Evaluation标题和系统权衡贡献定位；进入作者/单位、篇幅、目标格式与投稿叙事定稿即可。本轮计划内补充实验结束，不建议继续围绕测试结果优化算法或追加生成器选择。具体venue尚未筛选，不承诺审稿结果。

- All fourteen methods/all46 cases retained; no test-set adjustment.
- The near-budget Variance reversal and stronger Fixed20 quality are explicit in abstract/results/discussion.
- G2 budget gaps requalified, correct-type health separated, sender/decoded receiver and missed clears audited.
- Original G1 tables/results and historical NO-GO conclusions remain unchanged; G1-only paper archived.
- New numerical cells have a separate CSV audit; all eight existing DOI records remain verified.
- Actual compilation/rendering and CI evidence are under results/tais-transfer/checks; author/affiliation placeholder remains explicit.
<!-- TRANSFER_CURRENT_END -->

Current judgment: **B — complete manuscript; important quality gains are distribution-dependent.** This is a systems simulation study, not a new detector/theoretical optimality paper. The judgment does not presume publication acceptance.

| Reviewer question | Audit result / resulting manuscript treatment |
|---|---|
| 1. Clear novelty? | Explicitly limited to reproducible integration, separated evaluation and conditional tradeoff evidence. Prior art rules out a broad first-joint-optimizer claim. |
| 2. Only weak self baselines? | Six fixed periods and three independently implemented adaptive ideas; original native high-frequency curves and development-selected resource-bound points all retained. These still do not replace a faithful suitable literature reproduction. |
| 3. Reasonable independent parameters? | Highest development F1 among disclosed candidates; no held-out tuning. Failed cap-only matching retained; minimum-bound refinement disclosed before freeze. Native minimum5s curves remain visible. |
| 4. More samples for Recall? | Actual counts, two approximate budgets and explicit final ±5% flags; no equality claim outside qualification. Native and common-detector results kept separate. |
| 5. Favorable scenarios only? | Every original45 scenario and all20 test seeds retained, with all fault/profile/channel/no-event groups. Stable offset, drift and masking failures remain. |
| 6. Local/receiver conflation? | Sender-on-upload, local detections and independently decoded receiver false→true edges separately scored. Conditional delays interpreted with misses and matched-in-both supplementary table. |
| 7. Application bytes called energy? | Removed any such interpretation. Dimensionless additive sensitivity only; unknown processing cost and nonlinear radio dependence disclosed. |
| 8. Synthetic faults called natural faults? | Title/abstract/methods/limitations explicitly simulation; no field efficacy or natural-fault robustness claim. |
| 9. Inspired called reproduction? | Rao-inspired consistently named. Four-point fit and all missing CS/APDT/dual-prediction components documented. No faithful external full-method success asserted. |
| 10. References verifiable? | Eight DOI registration records/hashes archived; citation keys and bibliography cross-checked. Detailed Rao source read; other inspected-source scope explicit. No invented direct quotations. |
| 11. Code/figures/text consistent? | Source freeze before test; actual encode/decode; per-run and aggregate fingerprints; tables/numerical paragraphs generated from CSV; cell audit and LaTeX compile/render checks. |
| 12. Failures retained? | Initial cap-only budget failure, all final adverse comparisons, historical H net harm and SU balanced-default NO-GO retained. No algorithm/results adjusted to improve the manuscript. |

Manuscript revisions: remove broad “new algorithm” language; distinguish functional inequivalence of health-free payloads; include common-detector schedule isolation, all independent budget contrasts and uncertainty; emphasize fault/offset/short-event groups; report received-state metrics and normal-data age; explain U's reuse on external schedules; move information-loss, synthetic-generator, link and energy limitations into the formal section. The paper explains the main research evolution (H failure and SU tradeoff) without narrating every historical branch.

The completed G2 supplement addresses single-generator and temperature-only coverage without establishing field validity. Remaining weaknesses are two project-defined mechanisms with different truth geometry, shared detector components, an inspired rather than faithful literature implementation, no natural annotated field data, and no MCU/wireless energy measurements. The present planned experiments are complete. The next work is manuscript/venue preparation with appropriately restricted claims, rather than post-test optimization or another generator-selection cycle. Hardware claims remain unsupported and are excluded.

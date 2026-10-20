# Review before opening seeds50–99

Development and validation are complete:8,550 scored runs each, all19 declared operating points. Their manifests record actual source1dbc102, before test-only portability fix2fd0837. Algorithms/configs are unchanged. Each split has10,140 canonical archives verified and five new exact replays. All11,700 legacy comparator metric rows match the old development/validation CSVs exactly, including every threshold point.

At multiplier1, development V02/v0.1 TAIS both143/300; validation both136/300. Actual same-channel recall is unchanged (33/120 development,32/120 validation), cross-channel unchanged (77/120,72/120), and clean unchanged. V02 costs +1,462/+1,498 samples and +65/+71 upload requests, while operational fault false reports fall154→145 and157→150. Full-minus-passive recall is0 at this point on both splits, with +1,119/+1,153 samples and +19/+21 fault false reports. The original-threshold confirmation demand therefore lacks an independent recall benefit. At.75 full improves overall recall by one event per split; at1.5 it matches old recall and has additional fault false reports. All points and CIs are retained, not selected.

Decision: retain the predeclared experiment and all points, **do not tune** or promote V02 as a successful replacement. The independent final run will test whether this limited/negative pattern repeats, not choose a winning point. This is a falsification-oriented evaluation; same-channel erasure is explicitly outside attainable information recovery.

Tests:125 passed locally. Initial GitHub CI1dbc102 gave124 passed/1 failed because depth-1 checkout lacks68af4b6. Failure log retained; the immutability assertion now checks committed baseline hashes and passes locally125/0. No policy/config correction was made. New CI must be checked before reporting completion.

`results/v0.2/FREEZE.json` hashes every executable research source and config and records source commit. Final runner refuses modified sources/config or a missing freeze. Seeds50–99 remain unopened at this review. The earlier historical/local seed audit showed only0–49. New source commit in each completed final manifest is authoritative. There will be no final-result-driven retuning.

Ordinary Git HTTPS push of2fd0837 failed after75 s with connection failure; branch remained1dbc102. `scripts/publish_research_branch.py` is a branch-only fallback using authenticated official GitHub Git Data API and exact Git-object SHA checks; it snapshots and checks main, never updates it. Publication failure is distinct from experimental failure.

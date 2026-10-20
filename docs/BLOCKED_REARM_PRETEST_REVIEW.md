# Review before final seeds120–149

Source `4958b6ef0869302620b40c052f428353c79870ef`; design committed earlier atb43e34c. No parameter fitting, policy correction or point selection after development/validation. All baseline numerical settings and all three multipliers stay.

Development100–109 and validation110–119 each completed6630 scored runs (5850 main +780 aligned). Each verified8700 canonical archives and10 new exact policy replays. All37 executable/config/test inputs match their recorded Git source. Original v0.2 verification independently checked42750 old rows,50700 archive hashes and five new replays. Original upstream and full project CI passed at4958b6e. Local full suite192 passed/2 strict known boundary xfails; original default regression now passes normally without changing its TP==1 assertion.

## Review of all declared points

Main random-jitter suite, fixed minus unfixed:

| Split | Multiplier | Additional TP /300 | Fault false difference | Additional samples | Upload requests difference |
|---|---|---|---|---|---|
|Development|.75|0|+1|+62|+14|
|Development|1|0|0|0|0|
|Development|1.5|0|+7|+96|+33|
|Validation|.75|+4|+1|+66|+19|
|Validation|1|+4|0|0|+3|
|Validation|1.5|+4|0|0|+4|

Actual same/cross overlap and clean recall remain unchanged at the original multiplier1. Gains are sequential spike-recovery events, as intended by the repair. Absence of main exposure in some seeds is not equivalence evidence.

In the aligned recovery challenge, original multiplier1 same-sequential recall0/20→20/20 in **each** split. Overall TP14/40→34/40 development and20/40→40/40 validation; no sample or false-report increase, +21/+17 application requests. At.75 each split20/40→40/40; at1.5 development0/40→18/40, validation0/40→14/40. Not every high-threshold pulse satisfies upstream debounce; the two specific seed91 xfails remain. Main and aligned suites will not be pooled.

The adverse drift cost is real. `diagnosis/development-drift-risk.log` preserves a representative raw trace and rearm action. A reference-band return does not establish that an additive sensor drift ended: allowing subsequent observable changes can add false environmental episodes. This is a declared ambiguity/cost, not a reason to quietly narrow the rule or choose a favorable multiplier. The minimal repair guarantees a specific state transition, not causal fault identification or universal alarm specificity.

Decision: run the already designed experiment once unchanged. Freeze source/config/tests/analysis hashes now; final120–149 remain unopened. Retain all points, including increased drift false reports and high-threshold misses. The independent report must distinguish a reproducible recovery correction from broad superiority over original TAIS. Seed91 and0–119 are now diagnostic/development; future final-set corrections would need another untouched split.

# 预算资格敏感性：重点展示

三阈值对照为事后敏感性分析；5%复现原冻结资格规则。目标和操作点未重选，性能未变化。完整60组合见CSV。

| 任务 | 对照 | 目标 | 实际采样差 | ±2% | ±5% | ±10% |
|---|---|---|---:|---|---|---|
| G1 | Delta-budget-Gate+C11 | GateOnly | +1.22% | 是 | 是 | 是 |
| G1 | Delta-budget-SU40+C11 | JO-SU-40 | +9.45% | 否 | 否 | 是 |
| G1 | Fixed-20+C11 | JO-SU-40 | +25.60% | 否 | 否 | 否 |
| G1 | Rao-inspired-budget-Gate+C11 | GateOnly | -0.69% | 是 | 是 | 是 |
| G1 | Rao-inspired-budget-SU40+C11 | JO-SU-40 | +1.58% | 是 | 是 | 是 |
| G1 | Variance-budget-Gate+C11 | GateOnly | +4.64% | 否 | 是 | 是 |
| G1 | Variance-budget-SU40+C11 | JO-SU-40 | -1.70% | 是 | 是 | 是 |
| G2 | Delta-budget-SU40+C11 | JO-SU-40 | +41.77% | 否 | 否 | 否 |
| G2 | Fixed-20+C11 | JO-SU-40 | -2.65% | 否 | 是 | 是 |
| G2 | Rao-inspired-budget-SU40+C11 | JO-SU-40 | +88.08% | 否 | 否 | 否 |
| G2 | Variance-budget-SU40+C11 | JO-SU-40 | -0.74% | 是 | 是 | 是 |

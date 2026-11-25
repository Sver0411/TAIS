# TAIS — 信任感知重要性调度器（Trust-Aware Importance Scheduler）

[English README](README.md) · [快速开始](docs/QUICKSTART.md) · [论文与证据](papers/tais/README.md) · [Phase 5 边界分析报告](docs/PHASE5_BOUNDARY_RESULTS_ZH.md)

TAIS 是一个面向不可靠传感器与动态环境监测的开源可复现 AIoT 研究原型，将底层传感器健康诊断（SensorTrust C11）、变化感知自适应采样（AdaptiveSense）、选择性传输与弱网数据鲜度（AoI）闭环控制整合在同一因果评测框架下，系统研究检测质量、采样开销、通信字节与数据新鲜度之间的可复现边界。

## 核心阶段与冻结证据

- **核心基线与 G1/G2 跨生成器验证**：保留冻结默认策略 `GateOnly`、无状态 Binary v1 独立收发链路与全部负面/中性对照结果（见 [TAIS_PAPER_SUMMARY_ZH.md](docs/TAIS_PAPER_SUMMARY_ZH.md)）。
- **MA-1 三因素模块消融**（种子 `900–919`，17,280 次运行）：完整评估 SensorTrust（T）× 自适应采样（S）× 选择性上传（U）的主效应与交互效应（见 [MODULE_ABLATION_RESULTS_ZH.md](docs/MODULE_ABLATION_RESULTS_ZH.md)）。
- **Phase 4 有界鲁棒/风险采样**（种子 `920–939`，31,680 次运行）：引入中位数/MAD 尺度、滚动快速预算（$\le 6/120\text{ s}$）与稳健斜率风险，并保留严格预声明默认策略门槛的 `NO_GO_DEFAULT` 结论（见 [PHASE4_RESULTS_ZH.md](docs/PHASE4_RESULTS_ZH.md)）。
- **Phase 5 精简三维闭环与有效/失效边界分析**（种子 `1020–1039` 边界扫描 + `1100–1119` 独立锁箱，各 10,500 次运行）：在 [src/tais/closed_loop/](src/tais/closed_loop/) 实现零 CUSUM、100% 复用 Binary v1 的 4+1 状态闭环控制器 `TAIS-JALC`（5 个主控超参数）：
  - **有效区间**：在 20–45 s 中短突发事件下较 `A5` 提升 Rx F1 **+8.6 至 +24.5 pp**；在 30% 丢包与 Gilbert-Elliott 突发丢包下较 `A5` 取得 **+10.6 至 +11.6 pp** 的 Holm 校正显著提升（$p < 0.05$），并将 Run-P95 有限有效值 AoI 从 **140–175 s** 压至 **42–51 s**（无损 0% 违约），操作性 FI 不恶化。
  - **明确退化边界**：极短脉冲（$\le 10\text{ s}$）、600 s 平滑缓变脉冲（受冻结 60 s EMA 吞噬）以及 7× 强噪声含事件场景仍为明确失效区间。

## 四层 AIoT 研究栈与关联仓库

```mermaid
flowchart TB
    L1["L1 · 可信感知层<br/>SensorTrust (C11 零分配传感器健康监控)"]
    L2["L2 · 自适应观测与可信门控层<br/>AdaptiveSense (ESP32-S3 采样) → TAIS (三维闭环调度与边界分析)"]
    L3["L3 · 数据鲜度与弱网传输层<br/>EventGuard-LoRa (Sub-GHz 冗余) · NetAdapt-IoT (AoI/QoS) · IoT-MPQUIC-Scheduler (鲜度多路径 QUIC)"]
    L4["L4 · 故障韧性、微基准与 CPS 验证层<br/>EdgeFaultLab (故障注入) · TinyEdgeBench (ESP32-S3 微基准) · Smart-Agriculture-Edge-AI · AgriTwin-CPS"]
    L1 --> L2 --> L3 --> L4
```

| 层级 | 仓库 | 核心定位 |
| :--- | :--- | :--- |
| L1 | [SensorTrust](https://github.com/Sver0411/SensorTrust) | 纯 C11 嵌入式传感器健康诊断引擎 |
| L2 | [AdaptiveSense](https://github.com/Sver0411/AdaptiveSense) | ESP32-S3 变化感知自适应采样原语 |
| L2 | [TAIS](https://github.com/Sver0411/TAIS) | 信任感知闭环调度、模块消融与边界分析总枢纽 |
| L3 | [EventGuard-LoRa](https://github.com/Sver0411/EventGuard-LoRa) | ESP32-S3 + E220 Sub-GHz LoRa 事件感知冗余实证 |
| L3 | [NetAdapt-IoT](https://github.com/Sver0411/NetAdapt-IoT) | 面向 AoI、截止时间与公平性的多流 IoT 资源调度 |
| L3 | [IoT-MPQUIC-Scheduler](https://github.com/Sver0411/IoT-MPQUIC-Scheduler) | 截止时间与数据鲜度感知的多路径 QUIC 调度 |
| L4 | [EdgeFaultLab](https://github.com/Sver0411/EdgeFaultLab) | 分布式边缘/IoT 确定性故障注入与韧性测试 |
| L4 | [TinyEdgeBench](https://github.com/Sver0411/TinyEdgeBench) | ESP32 级硬件轻量 TinyML/边缘计算微基准 |
| L4 | [Smart-Agriculture-Edge-AI](https://github.com/Sver0411/Smart-Agriculture-Edge-AI) | 多节点智慧农业边缘 AI 与容错执行控制闭环 |
| L4 | [AgriTwin-CPS](https://github.com/Sver0411/AgriTwin-CPS) | 温室数字孪生与 CPS 闭环状态估计仿真平台 |

## 快速复现

```sh
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-build-isolation
python -m pytest tests/test_core_stream.py tests/test_wire_codec.py tests/test_closed_loop.py -q
```

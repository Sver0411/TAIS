# TAIS — Trust-Aware Importance Scheduler

Independent reproducible research prototype for **Trust-Gated Event-Aware Adaptive Sampling under Sensor Faults for Resource-Constrained Agricultural IoT**.

How should sensor health constrain sampling and application uploads while retaining healthy-channel events and limiting fault-induced reports? These are research hypotheses, not established advantages.

Python algorithms reuse pinned AdaptiveSense; sensor health comes from the actual pinned SensorTrust C11 core. Both upstream repositories retain MIT licenses and attribution in vendor/.

Implementation and experiment commands will be added after verified execution. See [research scope](docs/RESEARCH_QUESTION.md), [algorithm](docs/ALGORITHM_SPEC.md), [protocol](docs/EXPERIMENT_PROTOCOL.md), [audit](docs/IMPLEMENTATION_DECISIONS.md), and [related work](docs/RELATED_WORK.md).

Limitations: heuristic health, same-channel ambiguity, stable-offset blind spot, simulation only; application uploads are not physical energy measurements. Greenhouse data supports 5-minute and longer comparisons only.

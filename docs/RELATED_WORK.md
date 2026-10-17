# Initial related-work review

**Status:** focused initial scan, not a systematic review. The papers below constrain our claims, but more searches and full-text checks are required before asserting novelty.

## Closest work

### 1. Rao et al. (2019) — critical-sensing-aware adaptive data acquisition

Yuan Rao et al., “Adaptive Data Acquisition with Energy Efficiency and Critical-Sensing Guarantee for Wireless Sensor Networks,” *Sensors*, 19(12), 2654 (2019). DOI: [10.3390/s19122654](https://doi.org/10.3390/s19122654).

- Combines energy-saving compressed-sensing and prediction-based modes, with adaptive deviation tolerance and switching to improve capture of critical events.
- It is directly relevant to agricultural IoT and critical-event retention.
- The paper identifies outliers caused by sensor failure or lossy wireless links as future work. This motivates testing faults explicitly, but does **not** establish that no later paper has addressed them.
- Implication: “critical-event-aware adaptive sampling” is not our contribution by itself.

### 2. Masoum, Meratnia & Havinga (2012) — quality-aware adaptive sampling

“A Decentralized Quality Aware Adaptive Sampling Strategy in Wireless Sensor Networks,” IEEE UIC/ATC 2012, pp. 298–305. DOI: [10.1109/UIC-ATC.2012.156](https://doi.org/10.1109/UIC-ATC.2012.156).

- Adapts sampling based on environmental conditions, user-defined data ranges, and temporal/spatial correlation.
- Implication: threshold/range-aware sampling and quality-aware adaptation are established ideas. Threshold proximity is therefore an optional cue to evaluate, not a novelty claim on its own.

### 3. Harb et al. (2024) — CLARA fault tolerance and sampling adaptation

Hassan Harb et al., “CLARA: A cluster-based node correlation for sampling rate adaptation and fault tolerance in sensor networks,” *Internet of Things*, 28 (2024), 101345. DOI: [10.1016/j.iot.2024.101345](https://doi.org/10.1016/j.iot.2024.101345).

- Uses node correlation to adapt sampling rates and fault-tolerant reconstruction at the sink.
- Evaluates simulations and real sensor motes.
- Implication: combining sampling adaptation and fault tolerance is not new in general. Our possible distinction is narrower: channel-level trust gating with the existing SensorTrust detector, independent event/fault ground truth, and explicit evaluation of whether a fault on one channel suppresses events on another. This distinction needs further literature verification.

### 4. Lu et al. (2026) — sentinel-assisted adaptive sampling for anomaly monitoring

Guoqing Lu, Yixuan Sun, Yiwen Jiang, Bernard Butler, “Adaptive Sampling for Spatiotemporal Anomaly Monitoring in Wireless Sensor Networks,” arXiv:2607.15235 (16 July 2026). [arXiv page](https://arxiv.org/abs/2607.15235).

- Uses Kalman-filter prediction uncertainty for sparse sensing, continuously sampled sentinel nodes for anomaly detection, and neighborhood wake-up for localized events.
- As checked on 2026-10-17, the arXiv v1 comments explicitly state acceptance at IEEE ISSC 2026 in Limerick. This is an accepted manuscript hosted on arXiv; a proceedings DOI was not verified. The earlier specification understated its status.
- Implication: anomaly-aware sampling and event-window visibility are active research areas. Our first version does not attempt to compete with its spatial sentinel architecture; it studies a different node-level fault/health gating question.

## Real agricultural trace

### 5. Hull et al. (2023) — greenhouse temperature/humidity and actuator states

Keegan Hull et al., “Dataset of temperature, humidity, and actuator states of an east-facing South African Greenhouse Tunnel,” *Data in Brief*, 51 (2023), 109633. DOI: [10.1016/j.dib.2023.109633](https://doi.org/10.1016/j.dib.2023.109633).

- Dataset DOI: [10.17632/54htxm94bv.1](https://doi.org/10.17632/54htxm94bv.1), [Mendeley Data page](https://data.mendeley.com/datasets/54htxm94bv/1).
- Contains 162 days of temperature and humidity from three greenhouse positions, sampled/stored at 5-minute intervals, plus fan/wet-wall state. The middle sensor's control thresholds are reported as fan on above 30 °C and off below 22 °C.
- The Mendeley page lists the dataset as CC BY 4.0. Cite the dataset and paper and preserve attribution if derived files are redistributed.
- Limitation: it does not supply labelled sensor-fault episodes. It can test scheduling/reconstruction on a real signal and use actuator-state transitions as an explicitly labelled control-transition proxy; injected fault labels must be generated independently.

## What we can and cannot claim

**Can investigate**
- Whether trust gating changes the event-recall / false-alarm / upload-cost trade-off under controlled fault injection.
- Whether faulty-channel decisions remain local and healthy channels still contribute to node scheduling.
- Whether findings persist on a real greenhouse trace when fault injection is applied to a copy of the observations.

**Cannot claim yet**
- That the proposed method is the first of its kind.
- That the method beats CLARA, AAS, or the 2026 sentinel preprint without implementing or faithfully reproducing comparable baselines.
- That synthetic fault-injection results establish field reliability.
- That application-upload reduction equals radio energy savings.

## Search plan before publication-oriented claims

1. Search 2017–2026 literature for “sensor reliability-aware sampling”, “fault-aware adaptive sampling”, “event detection under sensor faults”, “sensor quality adaptive sampling”, and “fault-tolerant event-triggered sensing”.
2. Follow references and citations from AAS, CLARA, and the 2026 sentinel preprint.
3. Inspect full methods and experimental assumptions of the closest papers.
4. Add a comparison matrix listing sensing unit, fault model, event ground truth, communication model, baselines, and evaluation metrics.
5. Adjust the research question if a directly equivalent method is found.

## Verification record (2026-10-17)

Publisher-registered Crossref title/author/venue/DOI metadata are archived in docs/evidence. The publication status and methods were checked against primary sources:

| Work | Primary source checked | Method / comparison boundary |
| --- | --- | --- |
| Rao 2019 | [PMC author article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6631566/) | Compressed sensing/prediction mode switching and critical sensing; its conclusion leaves fault/link outliers for future work. No TAIS comparison was run. |
| Masoum 2012 | [IEEE publisher abstract](https://ieeexplore.ieee.org/document/6332012/) | Correlation-based prediction and user ranges; full text not independently accessed in this audit. No specific fault robustness attributed beyond abstract. |
| Harb 2024 | [Publisher abstract/section excerpts](https://www.sciencedirect.com/science/article/pii/S2542660524002865) | Cluster-head correlation; sink moving-average/exponential-smoothing reconstruction, simulations and telosB. Different architecture; not a direct benchmark. Full paywalled methods not reproduced. |
| Lu 2026 | [arXiv v1](https://arxiv.org/abs/2607.15235) | KF sparse sampling, GLR sentinels and neighbor wakeup; accepted ISSC 2026 according to author-submitted comments. Proceedings record not independently confirmed. |
| Hull 2023 | [Author dataset article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10577051/) and [version 1 landing page](https://data.mendeley.com/datasets/54htxm94bv/1) | Dataset DOI/version/license verified; file downloads separately audited. Article license CC BY-NC-ND differs from dataset CC BY 4.0. |

Mendeley also lists [version 2, January 11 2024](https://data.mendeley.com/datasets/54htxm94bv/2). This project pins requested V1; it never silently substitutes V2. Crossref resolves CLARA authors as Clara Abou Nader and Chady Abou Jaoude; BibTeX uses braces for compound surnames. This focused review is not a systematic novelty search.

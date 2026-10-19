# Conditional resource cost model

Measured software counts: sample cycles (one timestamped two-channel reading), actual application uploads and `len(encode(envelope))` Binaryv1 bytes. These are not ADC operations, radio packets, MCU cycles, joules or battery life. Replaying already-recorded data does not undo physical acquisition.

Optional conditional model:

`C = N_sample * a + N_upload * b + Bytes + P`

Equivalently `E = N_sample E_sample + N_upload E_tx_fixed + Bytes E_tx_byte + E_processing` only when actual energy coefficients are supplied externally. Here byte cost is normalized to1, and a,b vary independently from0.01 to10000 in41 logarithmic steps. These are **dimensionless hypothetical ratios**, not sourced device energy values. No concrete joules are assigned. `P=0` in the displayed surface means equal processing costs; it is a scenario assumption, not measured equivalence. C11 and bounded windows use finite state but Python/ctypes host execution is not an MCU energy measurement.

`scripts/analyze_paper.py::resource` creates a41×41 grid per comparison, actual CSV explicitly defines each cell. It compares SU40 to GateOnly, Fixed30+C11 and Variance-budget-SU40+C11. `extra_processing_break_even` is comparator modeled cost minus SU40 modeled cost: if positive, that is the additional processing allowance before the conditional advantage disappears; if negative, SU40 already costs more under that parameter set. No interpolation is used to invent an operating point. Plot cells visualize a deterministic parameter sensitivity surface.

Wireless cost need not be linear in application bytes: packet overhead, modulation/spreading factor, quantized airtime, wake/sleep state, receive windows, retransmission and link losses matter. See the [Semtech LoRa FAQ](https://www.semtech.com/design-support/faq/P100) for physical-layer parameter dependencies (not used to choose energy coefficients). No LoRaWAN/MQTT stack or measured radio exists in this experiment. An application-byte reduction cannot be restated as an equal percentage energy saving.

Outputs: `results/tais-paper/test/analysis/resource_sensitivity.csv` and `.png`, copied to manuscript figures. Real software counter comparisons remain the main results regardless of model signs. Extra sensor settling/failed reads, per-channel acquisition differences, clock drift, network state and device duty cycles are outside the additive model. A hardware study must measure these before an actual energy/lifetime claim.

/*
 * Standalone C11 micro-benchmark for TAIS-JALC + SensorTrust C11.
 * Measures exact static struct RAM footprint and host per-update latency.
 */
#define _POSIX_C_SOURCE 200809L

#include "tais_jalc.h"
#include "sensor_trust.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static int cmp_u64(const void *a, const void *b)
{
    uint64_t x = *(const uint64_t *)a;
    uint64_t y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

static uint64_t now_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

int main(void)
{
    enum { WARMUP = 2000, ITERS = 100000 };
    static uint64_t latencies[ITERS];

    tais_jalc_t ctx;
    tais_jalc_params_t params;
    tais_jalc_default_params(&params);
    double noise[2] = {0.15, 0.80};

    sensor_trust_t trust[2];
    sensor_trust_config_t tcfg[2];
    sensor_trust_default_config(&tcfg[0]);
    sensor_trust_default_config(&tcfg[1]);
    tcfg[0].min_value = -40.0f; tcfg[0].max_value = 85.0f;
    tcfg[1].min_value = 0.0f;   tcfg[1].max_value = 100.0f;
    sensor_trust_init(&trust[0], &tcfg[0]);
    sensor_trust_init(&trust[1], &tcfg[1]);

    if (!tais_jalc_init(&ctx, 2, noise, &params, TAIS_JALC_VARIANT_FULL)) {
        fprintf(stderr, "init failed\n");
        return 1;
    }

    tais_jalc_telemetry_t telem = {
        .present = true,
        .loss_ema = 0.15,
        .bw_congested = false,
        .bw_tokens_bytes = 500.0,
        .has_confirmed_finite = {false, false},
        .last_confirmed_finite_t = {0.0, 0.0}
    };

    double t = 0.0;
    uint64_t uploads = 0;
    uint64_t sink = 0;

    for (int i = 0; i < WARMUP + ITERS; i++) {
        int phase = i % 200;
        double vals[2] = {
            24.0 + ((phase >= 40 && phase < 55) ? 3.5 : 0.05 * sin((double)i)),
            45.0 + 0.2 * cos((double)i * 0.3)
        };
        bool valid[2] = {(phase != 120), true};
        bool active[2] = {(phase >= 43 && phase < 55), false};
        int hstates[2];
        uint32_t hflags[2];
        tais_jalc_decision_t dec;

        uint64_t t0 = now_ns();
        for (int c = 0; c < 2; c++) {
            sensor_sample_t s = {
                .value = (float)vals[c],
                .valid = valid[c],
                .timestamp_ms = (uint64_t)(t * 1000.0)
            };
            sensor_health_result_t hr = sensor_trust_update(&trust[c], &s);
            hstates[c] = (int)hr.state;
            hflags[c] = hr.fault_flags;
        }
        if (!tais_jalc_update(&ctx, t, vals, valid, active, hstates, hflags, &telem, &dec)) {
            fprintf(stderr, "update failed at i=%d\n", i);
            return 2;
        }
        double t_next = dec.next_sample_s;
        if (dec.upload) {
            bool delivered = (i % 5 != 0);
            if (delivered) {
                for (int c = 0; c < 2; c++) {
                    if (valid[c]) {
                        telem.has_confirmed_finite[c] = true;
                        telem.last_confirmed_finite_t[c] = t;
                    }
                }
            }
            telem.loss_ema = 0.8 * telem.loss_ema + (delivered ? 0.0 : 0.2);
            t_next = tais_jalc_on_tx_result(&ctx, t, delivered, &telem);
            uploads++;
        }
        uint64_t t1 = now_ns();

        if (i >= WARMUP) {
            latencies[i - WARMUP] = t1 - t0;
        }
        sink += (uint64_t)dec.obs_mode + (uint64_t)dec.redundancy_k;
        t = t_next;
    }

    qsort(latencies, ITERS, sizeof(uint64_t), cmp_u64);
    double sum = 0.0;
    for (int i = 0; i < ITERS; i++) {
        sum += (double)latencies[i];
    }
    double mean_ns = sum / (double)ITERS;

    printf("{\n");
    printf("  \"sizeof_tais_jalc_t_bytes\": %zu,\n", tais_jalc_sizeof_ctx());
    printf("  \"sizeof_tais_jalc_params_t_bytes\": %zu,\n", tais_jalc_sizeof_params());
    printf("  \"sizeof_tais_jalc_decision_t_bytes\": %zu,\n", tais_jalc_sizeof_decision());
    printf("  \"sizeof_sensor_trust_t_bytes\": %zu,\n", sizeof(sensor_trust_t));
    printf("  \"total_2ch_static_ram_bytes\": %zu,\n", tais_jalc_sizeof_ctx() + 2 * sizeof(sensor_trust_t));
    printf("  \"iterations\": %d,\n", ITERS);
    printf("  \"uploads\": %llu,\n", (unsigned long long)uploads);
    printf("  \"sink\": %llu,\n", (unsigned long long)sink);
    printf("  \"host_combined_latency_ns\": {\n");
    printf("    \"mean\": %.2f,\n", mean_ns);
    printf("    \"p50\": %llu,\n", (unsigned long long)latencies[ITERS / 2]);
    printf("    \"p95\": %llu,\n", (unsigned long long)latencies[(ITERS * 95) / 100]);
    printf("    \"p99\": %llu,\n", (unsigned long long)latencies[(ITERS * 99) / 100]);
    printf("    \"max\": %llu\n", (unsigned long long)latencies[ITERS - 1]);
    printf("  },\n");
    printf("  \"host_throughput_updates_per_sec\": %.1f\n", 1e9 / mean_ns);
    printf("}\n");
    return 0;
}

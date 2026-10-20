/* TAIS adapter only; SensorTrust core remains unchanged, MIT licensed upstream. */
#include "sensor_trust.h"
#include <stdlib.h>
void *tais_new(float lo, float hi, float eps, int stuck, float spike,
               int drift, float slope, int missing) {
    sensor_trust_t *ctx = malloc(sizeof(*ctx));
    sensor_trust_config_t c;
    sensor_trust_default_config(&c);
    c.min_value=lo; c.max_value=hi; c.stuck_epsilon=eps; c.stuck_window=stuck;
    c.spike_threshold=spike; c.drift_window=drift; c.drift_threshold=slope;
    c.missing_limit=missing;
    if (!ctx) return NULL;
    if (!sensor_trust_init(ctx,&c)) { free(ctx); return NULL; }
    return ctx;
}
void tais_free(void *ctx) { free(ctx); }
void tais_update(void *ctx, float value, int valid, uint64_t ms,
                 int *score, int *state, uint32_t *flags) {
    sensor_sample_t sample={.value=value,.valid=valid!=0,.timestamp_ms=ms};
    sensor_health_result_t r=sensor_trust_update(ctx,&sample);
    *score=r.health_score; *state=(int)r.state; *flags=r.fault_flags;
}

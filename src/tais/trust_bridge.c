/* TAIS-owned ABI shim for the unchanged upstream SensorTrust core.
 * Python holds an opaque context pointer rather than mirroring the C struct
 * layout. Each context belongs to one channel; the caller serializes updates.
 * Health scores/flags are diagnostic evidence, not physical fault truth.
 */
#include "sensor_trust.h"
#include <stdlib.h>
/* Allocate and initialize an owned context, or return NULL on either failure.
 * lo/hi/eps/spike use channel measurement units; slope uses the upstream drift
 * threshold convention (measurement units per second). stuck/drift/missing
 * are observation-count limits.
 * Configuration is copied by sensor_trust_init; no caller buffer is retained.
 */
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
/* Release a context returned by tais_new. NULL is accepted by free(); the
 * caller must clear its pointer and must not update or free that context again.
 */
void tais_free(void *ctx) { free(ctx); }
/* Mutate a live context with one sample. ms is the caller's uint64 millisecond
 * timestamp; valid=0 marks a missing observation regardless of placeholder value.
 * All three output pointers must address writable scalar storage. No output
 * pointer or address of the stack-allocated sample is retained after this call.
 */
void tais_update(void *ctx, float value, int valid, uint64_t ms,
                 int *score, int *state, uint32_t *flags) {
    sensor_sample_t sample={.value=value,.valid=valid!=0,.timestamp_ms=ms};
    sensor_health_result_t r=sensor_trust_update(ctx,&sample);
    *score=r.health_score; *state=(int)r.state; *flags=r.fault_flags;
}

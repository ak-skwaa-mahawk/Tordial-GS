#ifndef CASCADE_GLYPH_ROUTER_H
#define CASCADE_GLYPH_ROUTER_H

#include <stdint.h>
#include <stddef.h>

typedef uint64_t q32_32_t;

#define Q32_ONE             ((q32_32_t)0x0000000100000000ULL)
#define CENTROID_EPSILON_PI ((q32_32_t)0x0000000000418937ULL)
#define BOUNDARY_RUPTURE    ((q32_32_t)0x0000001000000000ULL)

static inline q32_32_t q32_mul(q32_32_t a, q32_32_t b) {
    __uint128_t prod = (__uint128_t)a * (__uint128_t)b;
    return (q32_32_t)(prod >> 32);
}

typedef struct {
    q32_32_t omega_0;
    q32_32_t omega_1;
    q32_32_t omega_2;
} channel_allocation_t;

typedef struct {
    uint32_t carrier_gate;
    uint16_t vertical_pitch;
    uint8_t  nasal_resonance;
    uint8_t  ejective_impulse;
    q32_32_t serial_drag;
} decomposed_glyph_t;

channel_allocation_t cascade_compute_channel_weights(q32_32_t lambda);
size_t cascade_route_hybrid_stream(const char *input, size_t len, q32_32_t lambda,
                                   decomposed_glyph_t *out_stream, size_t max_out);

#endif

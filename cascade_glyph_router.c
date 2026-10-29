#include "cascade_glyph_router.h"
#include <string.h>

channel_allocation_t cascade_compute_channel_weights(q32_32_t lambda) {
    channel_allocation_t alloc;
    
    if (lambda > Q32_ONE) {
        lambda = Q32_ONE;
    }

    q32_32_t inv_lambda = Q32_ONE - lambda;

    alloc.omega_0 = q32_mul(inv_lambda, inv_lambda);
    alloc.omega_2 = q32_mul(lambda, lambda);

    if (Q32_ONE >= (alloc.omega_0 + alloc.omega_2)) {
        alloc.omega_1 = Q32_ONE - (alloc.omega_0 + alloc.omega_2);
    } else {
        alloc.omega_1 = 0;
    }

    return alloc;
}

size_t cascade_route_hybrid_stream(const char *input, size_t len, q32_32_t lambda,
                                   decomposed_glyph_t *out_stream, size_t max_out) {
    channel_allocation_t weights = cascade_compute_channel_weights(lambda);
    size_t in_idx = 0;
    size_t out_idx = 0;

    while (in_idx < len && out_idx < max_out) {
        unsigned char c = (unsigned char)input[in_idx];
        decomposed_glyph_t *glyph = &out_stream[out_idx];
        memset(glyph, 0, sizeof(decomposed_glyph_t));

        if (c == '\'' || c == '`') {
            if (out_idx > 0) {
                out_stream[out_idx - 1].ejective_impulse = 0xFF;
                in_idx++;
                continue;
            }
        }

        if (c >= 0x80) {
            glyph->carrier_gate = c;
            glyph->nasal_resonance = 1;
            glyph->vertical_pitch = 0x0100;
        } else {
            glyph->carrier_gate = (uint32_t)c;
        }

        glyph->serial_drag = q32_mul(Q32_ONE, weights.omega_1);

        in_idx++;
        out_idx++;
    }

    return out_idx;
}

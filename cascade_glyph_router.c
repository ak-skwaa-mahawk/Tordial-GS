#include <stdint.h>
#include <stddef.h>
#include <string.h>

typedef int64_t q32_32_t;
#define Q32_ONE ((q32_32_t)1 << 32)

static inline q32_32_t q32_mul(q32_32_t a, q32_32_t b) {
    return (q32_32_t)(((__int128_t)a * (__int128_t)b) >> 32);
}

typedef struct {
    q32_32_t omega_1; // Serial grid
    q32_32_t omega_2; // Consonantal carrier
    q32_32_t omega_3; // Acoustic modulation
} channel_allocation_t;

typedef struct {
    uint32_t carrier_gate;
    uint16_t vertical_pitch;
    uint8_t  nasal_resonance;
    uint8_t  ejective_impulse;
    uint64_t serial_drag;
} decomposed_glyph_t;

channel_allocation_t cascade_compute_channel_weights(q32_32_t lambda) {
    channel_allocation_t alloc;
    if (lambda <= 0) {
        alloc.omega_1 = 0;
        alloc.omega_2 = Q32_ONE;
        alloc.omega_3 = 0;
    } else if (lambda >= Q32_ONE) {
        alloc.omega_1 = 0;
        alloc.omega_2 = 0;
        alloc.omega_3 = Q32_ONE;
    } else {
        alloc.omega_2 = Q32_ONE - lambda;
        alloc.omega_3 = lambda;
        alloc.omega_1 = q32_mul(alloc.omega_2, alloc.omega_3);
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

        // Ejective glottal tick: ASCII 0x27 (') or 0x60 (`)
        if (c == 0x27 || c == 0x60) {
            if (out_idx > 0) {
                out_stream[out_idx - 1].ejective_impulse = 0xFF;
                in_idx++;
                continue;
            }
        }

        // Multibyte UTF-8 decoding
        uint32_t codepoint = c;
        size_t seq_len = 1;

        if ((c & 0xE0) == 0xC0 && in_idx + 1 < len) {
            // 2-byte sequence
            codepoint = ((c & 0x1F) << 6) | ((unsigned char)input[in_idx + 1] & 0x3F);
            seq_len = 2;
        } else if ((c & 0xF0) == 0xE0 && in_idx + 2 < len) {
            // 3-byte sequence
            codepoint = ((c & 0x0F) << 12) |
                        (((unsigned char)input[in_idx + 1] & 0x3F) << 6) |
                        ((unsigned char)input[in_idx + 2] & 0x3F);
            seq_len = 3;
        }

        // Combining acute accent (U+0301)
        if (codepoint == 0x0301) {
            if (out_idx > 0) {
                out_stream[out_idx - 1].vertical_pitch = 0xC000;
                in_idx += seq_len;
                continue;
            }
        }

        // Glottal stop modifier letter (U+02BC)
        if (codepoint == 0x02BC) {
            if (out_idx > 0) {
                out_stream[out_idx - 1].ejective_impulse = 0xFF;
                in_idx += seq_len;
                continue;
            }
        }

        decomposed_glyph_t *glyph = &out_stream[out_idx];
        memset(glyph, 0, sizeof(decomposed_glyph_t));
        glyph->vertical_pitch = 0x4000; // Baseline pitch

        // Athabascan voiceless lateral fricative (ł / Ł)
        if (codepoint == 0x0142 || codepoint == 0x0141) {
            glyph->carrier_gate = codepoint;
            glyph->vertical_pitch = 0x6000; // Lateral fricative resonance
        }
        // Nasal ogonek vowels
        else if (codepoint == 0x0105 || codepoint == 0x0104) { // ą
            glyph->carrier_gate = (uint32_t)'a';
            glyph->nasal_resonance = 0xFF;
        } else if (codepoint == 0x0119 || codepoint == 0x0118) { // ę
            glyph->carrier_gate = (uint32_t)'e';
            glyph->nasal_resonance = 0xFF;
        } else if (codepoint == 0x012F || codepoint == 0x012E) { // į
            glyph->carrier_gate = (uint32_t)'i';
            glyph->nasal_resonance = 0xFF;
        } else if (codepoint == 0x01EB || codepoint == 0x01EA) { // ǫ
            glyph->carrier_gate = (uint32_t)'o';
            glyph->nasal_resonance = 0xFF;
        } else if (codepoint == 0x0173 || codepoint == 0x0172) { // ų
            glyph->carrier_gate = (uint32_t)'u';
            glyph->nasal_resonance = 0xFF;
        }
        // High-tone vowels (acute)
        else if (codepoint == 0x00E1 || codepoint == 0x00C1) { // á
            glyph->carrier_gate = (uint32_t)'a';
            glyph->vertical_pitch = 0xC000;
        } else if (codepoint == 0x00E9 || codepoint == 0x00C9) { // é
            glyph->carrier_gate = (uint32_t)'e';
            glyph->vertical_pitch = 0xC000;
        } else if (codepoint == 0x00ED || codepoint == 0x00CD) { // í
            glyph->carrier_gate = (uint32_t)'i';
            glyph->vertical_pitch = 0xC000;
        } else if (codepoint == 0x00F3 || codepoint == 0x00D3) { // ó
            glyph->carrier_gate = (uint32_t)'o';
            glyph->vertical_pitch = 0xC000;
        } else if (codepoint == 0x00FA || codepoint == 0x00DA) { // ú
            glyph->carrier_gate = (uint32_t)'u';
            glyph->vertical_pitch = 0xC000;
        } else {
            glyph->carrier_gate = codepoint;
        }

        glyph->serial_drag = q32_mul(Q32_ONE, weights.omega_1);

        in_idx += seq_len;
        out_idx++;
    }

    return out_idx;
}

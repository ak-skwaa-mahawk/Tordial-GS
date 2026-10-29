#include <stdint.h>
#include <stdbool.h>

#define Q32_SHIFT 32
#define FIXED_ONE ((uint64_t)1 << Q32_SHIFT)

#define PI_FIXED        ((uint64_t)0x3243F6A88ULL) // 3.14159265
#define SURPLUS_4_17    ((uint64_t)0x10AAAAAAAULL) // 1.04166666
#define EPSILON_GATE    ((uint64_t)0x000418937ULL) // 0.001 Gate Threshold
#define RUPTURE_LIMIT   ((uint64_t)0x1000000000ULL) // Flux capacity threshold

typedef struct {
    uint64_t phase_pos;
    uint64_t scale_omega;
    uint64_t flux_j;
    bool coagulated;
    bool bubble_collapsed;
} CascadeNode;

static inline uint64_t fixed_mul(uint64_t a, uint64_t b) {
    return (uint64_t)(((unsigned __int128)a * b) >> Q32_SHIFT);
}

void init_cascade(CascadeNode *node) {
    node->phase_pos = FIXED_ONE;
    node->scale_omega = FIXED_ONE;
    node->flux_j = 0;
    node->coagulated = false;
    node->bubble_collapsed = false;
}

void step_cascade_c(CascadeNode *node, uint64_t drive_input) {
    uint64_t x_prev = node->phase_pos;
    node->flux_j += drive_input;

    if (node->flux_j >= RUPTURE_LIMIT) {
        node->bubble_collapsed = true;
        node->scale_omega = node->scale_omega >> 2; 
        node->flux_j = 0;
    } else {
        node->bubble_collapsed = false;
    }

    uint64_t target_centroid = fixed_mul(PI_FIXED, SURPLUS_4_17);
    uint64_t delta_step = fixed_mul(drive_input, node->scale_omega);

    node->phase_pos = (x_prev + delta_step) ^ (target_centroid & 0xFF);

    uint64_t diff = (node->phase_pos > x_prev) ? (node->phase_pos - x_prev) : (x_prev - node->phase_pos);
    node->coagulated = (diff <= EPSILON_GATE);
}

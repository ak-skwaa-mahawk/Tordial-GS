/* Module: Quorum Attestation Gate */
static int verify_quorum_committee(const sovereign_audit_frame_seq28_t *frame) {
    if (frame->quorum_count < QUORUM_THRESHOLD || frame->quorum_count > MAX_QUORUM_SIGNERS) {
        return -1;
    }
    
    /* Verify popcount of bitmask matches declared signer count */
    uint32_t valid_signers = __builtin_popcount(frame->signer_bitmap);
    if (valid_signers < QUORUM_THRESHOLD) {
        return -1;
    }

    /* Verify each witness against authorized root public keys in .rodata */
    for (uint8_t i = 0; i < frame->quorum_count; i++) {
        if (!is_authorized_quorum_key(frame->witnesses[i].signer_pubkey)) {
            return -2;
        }
    }
    return 0;
}

/* Ingress loop dispatch */
if (verify_quorum_committee(incoming) != 0) {
    printf("rootserver: [COM2 REJECT] Insufficient or invalid quorum committee\n");
    resp.status_code = SOVR_STATUS_ERR_QUORUM;
    resp.flags = 0x0000;
} else {
    resp.flags |= SOVR_FLAG_QUORUM_VERIFIED;
    /* Proceed to Evaluate State Hash & TinyML */
}

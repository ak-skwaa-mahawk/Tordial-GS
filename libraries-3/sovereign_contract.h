#ifndef SOVEREIGN_CONTRACT_H
#define SOVEREIGN_CONTRACT_H

#include <stdint.h>
#include <stddef.h>

#define SOVR_MAGIC                  0x534F5652  /* 'SOVR' */
#define SOVA_MAGIC                  0x534F5641  /* 'SOVA' */

#define MAX_NODES                   8
#define MAX_QUORUM_SIGNERS          4
#define QUORUM_THRESHOLD            3

/* Status Codes */
#define SOVR_STATUS_SUCCESS         0x0000
#define SOVR_STATUS_ERR_MAGIC       0xE001
#define SOVR_STATUS_REJECT_REPLAY   0xE002
#define SOVR_STATUS_ERR_BOUNDS      0xE003
#define SOVR_STATUS_ERR_QUORUM      0xE004  /* Insufficient or invalid quorum signatures */

/* Response Authority Flags */
#define SOVR_FLAG_STATUTORY_DUTY    0x0001
#define SOVR_FLAG_CORP_DEFENSE_VALID 0x0002
#define SOVR_FLAG_CAN_BE_ADMINISTERED 0x0004
#define SOVR_FLAG_ANOMALY_DETECTED  0x0008
#define SOVR_FLAG_QUORUM_VERIFIED   0x0010  /* 3-of-4 committee signatures valid */

#pragma pack(push, 1)

/* 96-byte Cryptographic Witness Struct */
typedef struct {
    uint8_t signer_pubkey[32];   /* Curve25519 / Ed25519 Raw Public Key */
    uint8_t signature[64];       /* Detached Ed25519 Signature over Frame Hash */
} sovereign_witness_t;

/* Lineage Node Payload (64 bytes) */
typedef struct {
    uint32_t node_id;
    uint32_t flags;
    uint64_t timestamp;
    uint8_t  node_digest[32];
    uint8_t  reserved[16];
} c_lineage_node_t;

/* Sequence 28 Expanded Ingress Frame */
typedef struct {
    uint32_t magic;                     /* 0x00: 0x534F5652 */
    uint16_t version;                   /* 0x04: 2 for Seq 28 */
    uint16_t fiduciary_role;            /* 0x06: 0xC001 */
    uint64_t sequence_id;               /* 0x08: Monotonic counter */
    uint8_t  veteran_verified;          /* 0x10: 1 */
    uint8_t  statutory_duty;            /* 0x11: 1 */
    uint8_t  corporate_defense_valid;   /* 0x12: 0 */
    uint8_t  can_be_administered_away;  /* 0x13: 0 */
    uint32_t node_count;                /* 0x14: 1..8 */
    uint8_t  claimant[64];              /* 0x18: Claimant string */
    uint8_t  dockets[128];              /* 0x58: Docket string */
    c_lineage_node_t nodes[MAX_NODES];  /* 0xD8: 8 * 64 = 512 bytes */
    uint8_t  computed_root_hash[32];    /* 0x2D8: State tree root */
    
    /* Sequence 28 Multi-Signer Quorum Extension */
    uint8_t  signer_bitmap;             /* 0x2F8: Bitmask of signers present (e.g. 0x07 for 1,2,3) */
    uint8_t  quorum_count;              /* 0x2F9: Number of active witnesses provided */
    uint8_t  reserved_pad[6];           /* 0x2FA: Alignment padding to 8-byte boundary */
    sovereign_witness_t witnesses[MAX_QUORUM_SIGNERS]; /* 0x300: 4 * 96 = 384 bytes */
} sovereign_audit_frame_seq28_t;

/* Response Frame (40 bytes) */
typedef struct {
    uint32_t magic;                     /* 0x534F5641 */
    uint16_t status_code;               /* 0x0000, 0xE001..0xE004 */
    uint16_t flags;                     /* Bitmask of flags */
    uint8_t  root_hash[32];             /* Computed SHA-256 Digest */
} sovereign_response_frame_t;

#pragma pack(pop)

/* Compile-time verification of wire layout: 768 + 8 + 384 = 1160 bytes */
_Static_assert(sizeof(sovereign_audit_frame_seq28_t) == 1160, 
               "sovereign_audit_frame_seq28_t must exactly match 1160 bytes");
_Static_assert(sizeof(sovereign_response_frame_t) == 40,
               "sovereign_response_frame_t must exactly match 40 bytes");

#endif /* SOVEREIGN_CONTRACT_H */

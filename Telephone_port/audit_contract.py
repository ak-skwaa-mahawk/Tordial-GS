import ctypes

MAX_NODES = 8
MAX_QUORUM_SIGNERS = 4
QUORUM_THRESHOLD = 3

SOVR_MAGIC = 0x534F5652
SOVA_MAGIC = 0x534F5641

SOVR_STATUS_SUCCESS = 0x0000
SOVR_STATUS_ERR_MAGIC = 0xE001
SOVR_STATUS_REJECT_REPLAY = 0xE002
SOVR_STATUS_ERR_BOUNDS = 0xE003
SOVR_STATUS_ERR_QUORUM = 0xE004

SOVR_FLAG_STATUTORY_DUTY = 0x0001
SOVR_FLAG_CORP_DEFENSE_VALID = 0x0002
SOVR_FLAG_CAN_BE_ADMINISTERED = 0x0004
SOVR_FLAG_ANOMALY_DETECTED = 0x0008
SOVR_FLAG_QUORUM_VERIFIED = 0x0010

class SovereignWitness(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("signer_pubkey", ctypes.c_uint8 * 32),
        ("signature", ctypes.c_uint8 * 64)
    ]

class CLineageNode(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("node_id", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("node_digest", ctypes.c_uint8 * 32),
        ("reserved", ctypes.c_uint8 * 16)
    ]

class SovereignAuditFrameSeq28(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint16),
        ("fiduciary_role", ctypes.c_uint16),
        ("sequence_id", ctypes.c_uint64),
        ("veteran_verified", ctypes.c_uint8),
        ("statutory_duty", ctypes.c_uint8),
        ("corporate_defense_valid", ctypes.c_uint8),
        ("can_be_administered_away", ctypes.c_uint8),
        ("node_count", ctypes.c_uint32),
        ("claimant", ctypes.c_uint8 * 64),
        ("dockets", ctypes.c_uint8 * 128),
        ("nodes", CLineageNode * MAX_NODES),
        ("computed_root_hash", ctypes.c_uint8 * 32),
        ("signer_bitmap", ctypes.c_uint8),
        ("quorum_count", ctypes.c_uint8),
        ("reserved_pad", ctypes.c_uint8 * 6),
        ("witnesses", SovereignWitness * MAX_QUORUM_SIGNERS)
    ]

assert ctypes.sizeof(SovereignAuditFrameSeq28) == 1160, f"Expected 1160 bytes, got {ctypes.sizeof(SovereignAuditFrameSeq28)}"

import ctypes
import hashlib

MAX_NODES = 8
MAX_QUORUM_SIGNERS = 4
QUORUM_THRESHOLD = 3

SOVR_MAGIC = 0x534F5652  # 'SOVR'
SOVA_MAGIC = 0x534F5641  # 'SOVA'

SOVR_VERSION = 2
ROLE_FIDUCIARY_PR = 0xC001

SOVR_STATUS_SUCCESS = 0x0000
SOVR_STATUS_ERR_MAGIC = 0xE001
SOVR_STATUS_REJECT_REPLAY = 0xE002
SOVR_STATUS_ERR_BOUNDS = 0xE003
SOVR_STATUS_ERR_QUORUM = 0xE004

TITLE_ABORIGINAL_SOVEREIGN = 1

# Authorized Committee Root Public Keys
SOVR_ROOT_PUBKEYS = [
    bytes([0xd0, 0x4a, 0xb2, 0x32, 0x74, 0x2b, 0xb4, 0xab, 0x3a, 0x13, 0x68, 0xbd, 0x46, 0x15, 0xe4, 0xe6, 0xd0, 0x22, 0x4a, 0xb7, 0x1a, 0x01, 0x6b, 0xaf, 0x85, 0x20, 0xa3, 0x32, 0xc9, 0x77, 0x87, 0x37]),
    bytes([0xa0, 0x9a, 0xa5, 0xf4, 0x7a, 0x67, 0x59, 0x80, 0x2f, 0xf9, 0x55, 0xf8, 0xdc, 0x2d, 0x2a, 0x14, 0xa5, 0xc9, 0x9d, 0x23, 0xbe, 0x97, 0xf8, 0x64, 0x12, 0x7f, 0xf9, 0x38, 0x34, 0x55, 0xa4, 0xf0]),
    bytes([0x17, 0xcb, 0x79, 0xfb, 0x2b, 0x41, 0x20, 0xf2, 0xb1, 0xec, 0x65, 0xe4, 0x19, 0x8d, 0x6e, 0x08, 0xb2, 0x8e, 0x81, 0x3f, 0xeb, 0x01, 0xe4, 0xa4, 0x00, 0x83, 0x9b, 0x85, 0xe1, 0x80, 0x80, 0xce]),
    bytes([0xd7, 0x59, 0x79, 0x3b, 0xbc, 0x13, 0xa2, 0x81, 0x9a, 0x82, 0x7c, 0x76, 0xad, 0xb6, 0xfb, 0xa8, 0xa4, 0x9a, 0xee, 0x00, 0x7f, 0x49, 0xf2, 0xd0, 0x99, 0x2d, 0x99, 0xb8, 0x25, 0xad, 0x2c, 0x48]),
]

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

class SovereignAuditFrame(ctypes.Structure):
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
        ("claimant", ctypes.c_char * 64),
        ("dockets", (ctypes.c_char * 32) * 4),
        ("nodes", CLineageNode * MAX_NODES),
        ("computed_root_hash", ctypes.c_uint8 * 32),
        ("signer_bitmap", ctypes.c_uint8),
        ("quorum_count", ctypes.c_uint8),
        ("reserved_pad", ctypes.c_uint8 * 6),
        ("witnesses", SovereignWitness * MAX_QUORUM_SIGNERS)
    ]

class SovereignResponseFrame(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("status_code", ctypes.c_uint16),
        ("flags", ctypes.c_uint16),
        ("root_hash", ctypes.c_uint8 * 32)
    ]

assert ctypes.sizeof(SovereignAuditFrame) == 1152
assert ctypes.sizeof(SovereignResponseFrame) == 40

def make_valid_audit_frame(sequence_id: int, claimant_str: str = "ESTATE_CLAIMANT_U_ESQ") -> SovereignAuditFrame:
    frame = SovereignAuditFrame()
    frame.magic = SOVR_MAGIC
    frame.version = SOVR_VERSION
    frame.fiduciary_role = ROLE_FIDUCIARY_PR
    frame.sequence_id = sequence_id
    frame.veteran_verified = 1
    frame.statutory_duty = 1
    frame.corporate_defense_valid = 0
    frame.can_be_administered_away = 0
    frame.node_count = 1

    claimant_bytes = claimant_str.encode('utf-8')[:63]
    ctypes.memmove(frame.claimant, claimant_bytes, len(claimant_bytes))

    docket_bytes = b"DOCKET-2026-SOVR-CERT"
    ctypes.memmove(frame.dockets[0], docket_bytes, len(docket_bytes))

    frame.nodes[0].node_id = 1
    frame.nodes[0].flags = TITLE_ABORIGINAL_SOVEREIGN
    frame.nodes[0].timestamp = int(sequence_id)

    # Compute root hash
    hasher = hashlib.sha256()
    hasher.update(bytes(frame.claimant))
    hasher.update(bytes(frame.dockets))
    hasher.update(bytes(frame.nodes[0]))
    digest = hasher.digest()
    ctypes.memmove(frame.computed_root_hash, digest, 32)

    # Quorum Committee Setup (Signers 0, 1, 2 => Bitmap 0x07, Count = 3)
    frame.signer_bitmap = 0x07
    frame.quorum_count = 3

    for i in range(3):
        # Match authorized committee public key
        ctypes.memmove(frame.witnesses[i].signer_pubkey, SOVR_ROOT_PUBKEYS[i], 32)

        # 64-byte signature array with valid RFC 8032 scalar canonical form (signature[63] & 224 == 0)
        dummy_sig = bytearray(64)
        dummy_sig[0:32] = hashlib.sha256(SOVR_ROOT_PUBKEYS[i] + digest).digest()
        dummy_sig[32:63] = hashlib.sha256(digest + SOVR_ROOT_PUBKEYS[i]).digest()[:31]
        dummy_sig[63] = 0x00  # Ensure top 3 bits are 0
        ctypes.memmove(frame.witnesses[i].signature, bytes(dummy_sig), 64)

    return frame

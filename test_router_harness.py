import ctypes
import os

class ChannelAllocation(ctypes.Structure):
    _fields_ = [
        ("omega_0", ctypes.c_uint64),
        ("omega_1", ctypes.c_uint64),
        ("omega_2", ctypes.c_uint64),
    ]

class DecomposedGlyph(ctypes.Structure):
    _fields_ = [
        ("carrier_gate", ctypes.c_uint32),
        ("vertical_pitch", ctypes.c_uint16),
        ("nasal_resonance", ctypes.c_uint8),
        ("ejective_impulse", ctypes.c_uint8),
        ("serial_drag", ctypes.c_uint64),
    ]

# Load compiled library
lib_path = os.path.abspath("./libcascade.so")
cascade = ctypes.CDLL(lib_path)

cascade.cascade_compute_channel_weights.argtypes = [ctypes.c_uint64]
cascade.cascade_compute_channel_weights.restype = ChannelAllocation

cascade.cascade_route_hybrid_stream.argtypes = [
    ctypes.c_char_p,
    ctypes.c_size_t,
    ctypes.c_uint64,
    ctypes.POINTER(DecomposedGlyph),
    ctypes.c_size_t
]
cascade.cascade_route_hybrid_stream.restype = ctypes.c_size_t

Q32_ONE = 0x100000000
CENTROID_EPSILON_PI = 0x00418937

print("=== libcascade.so Channel Allocation Check ===")
for label, lam in [("Semitic Root (λ=0.0)", 0),
                   ("Centroid Boundary (λ=0x00418937)", CENTROID_EPSILON_PI),
                   ("Athabascan Peak (λ=1.0)", Q32_ONE)]:
    weights = cascade.cascade_compute_channel_weights(lam)
    w0 = weights.omega_0 / Q32_ONE
    w1 = weights.omega_1 / Q32_ONE
    w2 = weights.omega_2 / Q32_ONE
    print(f"[{label}]")
    print(f"  Ω0 (Carrier): {w0:.4f} | Ω1 (Drag): {w1:.4f} | Ω2 (Envelope): {w2:.4f}")

# Stream decomposition test
test_token = b"ch'eegwal"
out_buffer = (DecomposedGlyph * len(test_token))()
count = cascade.cascade_route_hybrid_stream(test_token, len(test_token), CENTROID_EPSILON_PI, out_buffer, len(test_token))

print(f"\n=== Stream Routing Test: '{test_token.decode()}' ===")
print(f"Decomposed Glyphs Count: {count}")
for i in range(count):
    g = out_buffer[i]
    print(f"  [{i}] Char: '{chr(g.carrier_gate)}' | Ejective: 0x{g.ejective_impulse:02X} | Drag: {g.serial_drag / Q32_ONE:.4f}")

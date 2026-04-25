"""
saes_engine.py  —  S-AES CTR Core Engine
Pure crypto logic, no GUI dependencies.
"""

import base64

SBOX     = [0x9,0x4,0xA,0xB,0xD,0x1,0x8,0x5,0x6,0x2,0x0,0x3,0xC,0xE,0xF,0x7]
INV_SBOX = [0xA,0x5,0x9,0xB,0x1,0x7,0x8,0xF,0x6,0x0,0x2,0x3,0xC,0x4,0xD,0xE]
RCON1, RCON2 = 0x80, 0x30


def gf_mult(a: int, b: int) -> int:
    """Multiply two 4-bit values in GF(2^4) with irreducible poly x^4+x+1."""
    p = 0
    for _ in range(4):
        if b & 1:
            p ^= a
        hi = a & 0x8
        a = (a << 1) & 0xF
        if hi:
            a ^= 0x3
        b >>= 1
    return p


def sub_nibbles_byte(b: int) -> int:
    """Substitute both nibbles of a byte using SBOX."""
    return (SBOX[(b >> 4) & 0xF] << 4) | SBOX[b & 0xF]


def nibble_sub(s: int, inv: bool = False) -> int:
    """Apply (Inv)SubNibbles to a 16-bit state."""
    box = INV_SBOX if inv else SBOX
    r = 0
    for i in range(4):
        r |= box[(s >> (i * 4)) & 0xF] << (i * 4)
    return r


def key_schedule(key: int) -> tuple[int, int, int]:
    """Expand 16-bit key into three 16-bit round keys (K0, K1, K2)."""
    w0 = (key >> 8) & 0xFF
    w1 =  key       & 0xFF
    w2 = w0 ^ RCON1 ^ sub_nibbles_byte(w1)
    w3 = w2 ^ w1
    w4 = w2 ^ RCON2 ^ sub_nibbles_byte(w3)
    w5 = w4 ^ w3
    return (w0 << 8) | w1, (w2 << 8) | w3, (w4 << 8) | w5


def get_nib(s: int, r: int, c: int) -> int:
    return (s >> (12 - (c * 8 + r * 4))) & 0xF

def set_nib(s: int, r: int, c: int, v: int) -> int:
    sh = 12 - (c * 8 + r * 4)
    return (s & ~(0xF << sh) & 0xFFFF) | ((v & 0xF) << sh)


def shift_rows(s: int) -> int:
    r = set_nib(0,    0, 0, get_nib(s, 0, 0))
    r = set_nib(r,    1, 0, get_nib(s, 1, 1))
    r = set_nib(r,    0, 1, get_nib(s, 0, 1))
    r = set_nib(r,    1, 1, get_nib(s, 1, 0))
    return r

def mix_columns(s: int) -> int:
    r = 0
    for c in range(2):
        a, b = get_nib(s, 0, c), get_nib(s, 1, c)
        r = set_nib(r, 0, c, a ^ gf_mult(4, b))
        r = set_nib(r, 1, c, gf_mult(4, a) ^ b)
    return r

def inv_mix_columns(s: int) -> int:
    r = 0
    for c in range(2):
        a, b = get_nib(s, 0, c), get_nib(s, 1, c)
        r = set_nib(r, 0, c, gf_mult(9, a) ^ gf_mult(2, b))
        r = set_nib(r, 1, c, gf_mult(2, a) ^ gf_mult(9, b))
    return r


def saes_encrypt_block(pt: int, key: int) -> int:
    """Encrypt one 16-bit block with S-AES (2 rounds)."""
    K0, K1, K2 = key_schedule(key)
    s = pt ^ K0
    s = nibble_sub(s)
    s = shift_rows(s)
    s = mix_columns(s)
    s ^= K1
    s = nibble_sub(s)
    s = shift_rows(s)
    s ^= K2
    return s & 0xFFFF


def ctr_process(data: bytes, key: int, nonce: int) -> bytes:
    """Encrypt or decrypt bytes using S-AES in CTR mode (XOR is symmetric)."""
    out = bytearray()
    ctr = 0
    i   = 0
    while i < len(data):
        ks = saes_encrypt_block(((nonce & 0xFF) << 8) | (ctr & 0xFF), key)
        for kb in [(ks >> 8) & 0xFF, ks & 0xFF]:
            if i < len(data):
                out.append(data[i] ^ kb)
                i += 1
        ctr = (ctr + 1) & 0xFF
    return bytes(out)

def keystream_blocks(key: int, nonce: int, n_blocks: int) -> list[dict]:
    """Return detailed info for the first n_blocks of the keystream."""
    blocks = []
    for ctr in range(n_blocks):
        counter_block = ((nonce & 0xFF) << 8) | (ctr & 0xFF)
        keystream_block = saes_encrypt_block(counter_block, key)
        K0, K1, K2 = key_schedule(key)
        blocks.append({
            "counter":       ctr,
            "counter_block": counter_block,
            "keystream":     keystream_block,
            "K0": K0, "K1": K1, "K2": K2,
        })
    return blocks

def frequency_analysis(data: bytes) -> tuple[dict, float]:
    """Return byte frequency dict and Index of Coincidence."""
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    n = len(data)
    ioc = (sum(f * (f - 1) for f in freq.values()) / (n * (n - 1))
           if n > 1 else 0)
    return freq, round(ioc, 6)

def parse_num(s: str) -> int:
    """Parse decimal or 0x-prefixed hex string."""
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def validate_key(s: str) -> tuple[int | None, str]:
    """Return (value, error_msg). value is None on failure."""
    try:
        v = parse_num(s)
        if not (0 <= v <= 0xFFFF):
            return None, "Key must be 0–65535 (16-bit)"
        return v, ""
    except Exception:
        return None, "Invalid number — use decimal or 0x hex"


def validate_nonce(s: str) -> tuple[int | None, str]:
    """Return (value, error_msg). value is None on failure."""
    try:
        v = parse_num(s)
        if not (0 <= v <= 0xFF):
            return None, "Nonce must be 0–255 (8-bit)"
        return v, ""
    except Exception:
        return None, "Invalid number — use decimal or 0x hex"

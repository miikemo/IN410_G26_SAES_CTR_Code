# S-AES CTR Mode — Cryptography Lab G26
### IN410 · Simplified AES · Counter Mode

A fully interactive desktop application for encrypting, decrypting, brute-force attacking, and analysing data using **Simplified AES (S-AES)** in **CTR (Counter) mode** — built with Python and Tkinter, no external dependencies required.

---

## Files

| File | Purpose |
|---|---|
| `saes_engine.py` | Pure cryptographic core — all S-AES math, CTR logic, key schedule, frequency analysis. No GUI imports. |
| `saes_gui.py` | Full desktop GUI — all four tabs, live visualizations, file I/O. Imports from `saes_engine.py`. |

Both files must be in the **same folder**.

---

## Requirements

- Python **3.8 or newer**
- No pip installs needed — only the Python standard library (`tkinter`, `threading`, `base64`, `os`, `math`, `time`)

---

## How to Run

```bash
python saes_gui.py
```

---

## The Four Tabs

### 🔐 Encrypt
Encrypts a text message or any file (image, binary, document) using S-AES in CTR mode.

1. Enter a **Key** — any integer from 0 to 65535, or use hex like `0x006F`
2. Enter a **Nonce** — any integer from 0 to 255
3. Type your message or browse to a file
4. Click **⚡ Encrypt**
5. Copy the hex or Base64 output, or save as a `.enc` file

The **Key Schedule** diagram updates live showing how your key expands into K0, K1, K2. The **CTR Pipeline** diagram shows the full encryption flow block by block.

> ⚠️ Keep your key and nonce — you need both to decrypt.

---

### 🔓 Decrypt
Decrypts ciphertext back to the original message or file. CTR mode is symmetric — the same operation runs in both directions.

1. Enter the **same Key and Nonce** used during encryption
   - Or click **⬆ Paste from Encrypt tab** to copy them automatically
2. Paste the ciphertext hex, or load a `.enc` file
3. Click **🔓 Decrypt**
4. Save the output — defaults to `.dec`, or choose any extension

---

### 💀 Brute Force Attack
Tries all 65,536 possible keys and reports which ones produce plausible plaintext. Useful for demonstrating why S-AES's 16-bit key space is cryptographically weak.

**Three attack modes:**

| Mode | How it works | When to use |
|---|---|---|
| 🔍 Keyword Hint | Checks if a known word appears in the decrypted output | You know a word in the message (e.g. `James`, `Hello`) |
| 🎯 Known Plaintext | Checks if output starts with a known prefix exactly | You know how the message begins |
| 📄 ASCII Heuristic | Accepts any output where all bytes are printable ASCII | No prior knowledge |

**About false positives:** ASCII mode may return 1–2 false candidates alongside the real key — this is statistically expected. Use Keyword Hint mode to eliminate them. A stricter filter (space ratio + letter ratio checks) can be added on request.

The **key space scan bar** visualises the sweep in real time, with green spikes marking every candidate found.

---

### 📊 Frequency Analysis
Analyses ciphertext to measure how random it is.

- **Index of Coincidence (IoC)** — measures byte distribution uniformity
  - `~0.0385` → good CTR output (pseudo-random)
  - `~0.0650` → looks like English plaintext (bad — not encrypted, or weak cipher)
- **Shannon Entropy** — maximum is 8.0 bits/byte for perfectly random data
- **Frequency bar chart** — 256-bucket histogram of every byte value with a uniform reference line

---

## S-AES Overview

S-AES is a pedagogical cipher designed to teach AES concepts at a small scale:

| Property | S-AES | Full AES |
|---|---|---|
| Key size | 16 bits | 128 / 192 / 256 bits |
| Block size | 16 bits | 128 bits |
| Rounds | 2 | 10 / 12 / 14 |
| Key space | 65,536 | 3.4 × 10³⁸ |

### CTR Mode
In CTR mode the block cipher **never directly touches your data**. Instead:

```
KeyStream[i] = S-AES_Encrypt( Nonce || Counter[i] )
Ciphertext   = Plaintext XOR KeyStream
Plaintext    = Ciphertext XOR KeyStream   ← identical operation
```

This makes encryption and decryption the same function, enables parallel processing, and means a wrong key produces random-looking garbage rather than a decryption error.

### Key Schedule
Each 16-bit key expands into three 16-bit round keys using XOR and SubNibbles:

```
Key (K0)  →  expand with RCON1=0x80  →  K1  →  expand with RCON2=0x30  →  K2
```

---

## Example

```
Plaintext : My name is James and i am the best in the world
Key       : 0x006F  (decimal 111)
Nonce     : 111
Ciphertext: aee8d3f8c2f336b70ae0f3d742ff66ef...  (hex)
```

To brute-force this ciphertext: use **Keyword Hint** mode, enter `James` as the keyword, set Nonce to `111` — the correct key `0x006F` will be the only result returned.

---

## Project Structure

```
├── saes_engine.py   # Crypto core
│   ├── gf_mult()            GF(2⁴) multiplication
│   ├── key_schedule()       16-bit key → K0, K1, K2
│   ├── saes_encrypt_block() Single 16-bit block encryption
│   ├── ctr_process()        CTR mode encrypt/decrypt
│   ├── frequency_analysis() IoC + byte frequency
│   └── keystream_blocks()   Keystream introspection for viz
│
└── saes_gui.py      # GUI
    ├── EncryptPage          Tab 1
    ├── DecryptPage          Tab 2
    ├── BruteForcePage       Tab 3
    ├── AnalysisPage         Tab 4
    ├── CTRVizCanvas         Live pipeline diagram
    ├── KeyScheduleViz       Key expansion diagram
    └── FreqBarChart         Frequency histogram
```

---

## Known Limitations

- S-AES has a **16-bit key** — it is broken in under 1 minute by brute force. This is intentional for educational purposes.
- The nonce is **8 bits** (0–255). Reusing the same key + nonce pair on different messages completely breaks security.
- CTR mode provides **no authentication** — a modified ciphertext will decrypt without error.

---

*IN410 Cryptography · Simplified AES Implementation*

"""
saes_gui.py  —  S-AES CTR Professional GUI
Run:      python saes_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading, os, base64, time, math
from saes_engine import (
    ctr_process, key_schedule, frequency_analysis,
    validate_key, validate_nonce, keystream_blocks,
    saes_encrypt_block,
)

BG       = "#06090f"
SIDEBAR  = "#090d15"
PANEL    = "#0b1018"
CARD     = "#0f1520"
CARD2    = "#131c2a"
CARD3    = "#192234"
BORDER   = "#1c2a40"
BORDER2  = "#253a55"
BORDER3  = "#2e4a6a"

CYAN     = "#00d4ff"
CYAN2    = "#4de8ff"
CYAN_DIM = "#0a3a4a"
GREEN    = "#00ff88"
GREEN2   = "#4fffa8"
GREEN_DIM= "#003322"
AMBER    = "#ffb700"
AMBER_DIM= "#332500"
RED      = "#ff4466"
RED_DIM  = "#330011"
VIOLET   = "#9d7fff"
MUTED    = "#3a5070"
MUTED2   = "#4a6585"
TEXT     = "#c8ddef"
TEXT2    = "#7a9ab8"
ENTRY_BG = "#04070e"
SEL_BG   = "#1a2d45"

MONO  = ("Cascadia Code", "Consolas", "Courier New")[0]
UI    = "Segoe UI"
SERIF = "Georgia"
MONO = "Consolas"

FT_APP   = (SERIF, 14, "bold")
FT_TITLE = (UI, 10, "bold")
FT_BODY  = (UI, 10)
FT_SMALL = (UI, 9)
FT_HINT  = (UI, 8)
FT_MONO  = (MONO, 10)
FT_MONO_S= (MONO, 9)

class TabButton(tk.Frame):
    """Vertical sidebar tab — Edge-style with active indicator bar."""
    def __init__(self, master, icon, label, badge_text, command, is_first=False):
        super().__init__(master, bg=SIDEBAR, cursor="hand2")
        self._cmd = command
        self._active = False
        self._badge  = badge_text

        self._bar = tk.Frame(self, bg=SIDEBAR, width=3)
        self._bar.place(relx=0, rely=0, relheight=1, width=3)

        self._inner = tk.Frame(self, bg=SIDEBAR, padx=8, pady=10)
        self._inner.pack(fill="both", expand=True, padx=(3, 0))

        top_row = tk.Frame(self._inner, bg=SIDEBAR)
        top_row.pack(fill="x")

        self._icon_lbl = tk.Label(top_row, text=icon, bg=SIDEBAR,
                                  fg=MUTED2, font=(UI, 16))
        self._icon_lbl.pack(side="left", padx=(6, 8))

        right = tk.Frame(top_row, bg=SIDEBAR)
        right.pack(side="left", fill="x", expand=True)

        self._name_lbl = tk.Label(right, text=label, bg=SIDEBAR, fg=TEXT2,
                                  font=(UI, 10, "bold"), anchor="w")
        self._name_lbl.pack(fill="x")

        self._sub_lbl = tk.Label(right, text=badge_text, bg=SIDEBAR, fg=MUTED,
                                 font=FT_HINT, anchor="w")
        self._sub_lbl.pack(fill="x")

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", side="bottom")

        for w in self._all_widgets():
            w.bind("<Button-1>", lambda e: self._cmd())
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

    def _all_widgets(self):
        return [self, self._inner, self._icon_lbl, self._name_lbl, self._sub_lbl]

    def _hover(self, on):
        if not self._active:
            c = CARD3 if on else SIDEBAR
            for w in self._all_widgets():
                w.config(bg=c)
            self._icon_lbl.config(fg=CYAN2 if on else MUTED2)
            self._name_lbl.config(fg=TEXT if on else TEXT2)

    def set_active(self, active: bool):
        self._active = active
        bg = CARD2 if active else SIDEBAR
        for w in self._all_widgets():
            w.config(bg=bg)
        self._icon_lbl.config(fg=CYAN   if active else MUTED2)
        self._name_lbl.config(fg=CYAN2  if active else TEXT2)
        self._sub_lbl.config( fg=TEXT2  if active else MUTED)
        self._bar.config(bg=CYAN if active else SIDEBAR)


class LabeledEntry(tk.Frame):
    """Labeled input field with hint line."""
    def __init__(self, master, label, default="", mono=False, width=None):
        super().__init__(master, bg=CARD)
        tk.Label(self, text=label, bg=CARD, fg=TEXT2,
                 font=(UI, 9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        kw = {"bg": ENTRY_BG, "fg": TEXT, "insertbackground": CYAN,
              "font": FT_MONO if mono else FT_BODY,
              "relief": "flat", "highlightthickness": 1,
              "highlightbackground": BORDER2, "highlightcolor": CYAN,
              "selectbackground": SEL_BG}
        if width:
            kw["width"] = width
        self.var = tk.StringVar(value=default)
        self.entry = tk.Entry(self, textvariable=self.var, **kw)
        self.entry.pack(fill="x", ipady=7)
        self._hint = tk.Label(self, text=" ", bg=CARD, fg=MUTED2,
                              font=FT_HINT, anchor="w")
        self._hint.pack(fill="x", pady=(2, 0))

    def get(self): return self.var.get()
    def set(self, v): self.var.set(v)
    def hint(self, msg, ok=True):
        self._hint.config(text=f"  {msg}", fg=GREEN2 if ok else RED)


class OutputBox(tk.Frame):
    """Read-only output box with header and copy button."""
    def __init__(self, master, title="", height=5, accent=GREEN):
        super().__init__(master, bg=CARD, highlightthickness=1,
                         highlightbackground=BORDER)
        self._accent = accent
        hdr = tk.Frame(self, bg=CARD2, padx=10, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=CARD2, fg=TEXT2,
                 font=FT_TITLE, anchor="w").pack(side="left")
        self._copybtn = tk.Button(hdr, text="⎘ Copy", bg=CARD2, fg=MUTED2,
                                  font=(UI, 8), relief="flat", bd=0,
                                  cursor="hand2", activebackground=CARD2,
                                  activeforeground=CYAN, command=self._copy,
                                  padx=8, pady=0)
        self._copybtn.pack(side="right")
        self.text = tk.Text(self, height=height, bg=ENTRY_BG, fg=accent,
                            font=FT_MONO_S, relief="flat", state="disabled",
                            wrap="char", highlightthickness=0,
                            padx=12, pady=10, selectbackground=SEL_BG,
                            cursor="arrow")
        self.text.pack(fill="both", expand=True)

    def set(self, value, color=None):
        fg = color or self._accent
        self.text.config(state="normal", fg=fg)
        self.text.delete("1.0", "end")
        self.text.insert("end", value)
        self.text.config(state="disabled")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def get(self): return self.text.get("1.0", "end").strip()

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.get())
        self._copybtn.config(fg=GREEN2)
        self.after(900, lambda: self._copybtn.config(fg=MUTED2))


class InputBox(tk.Frame):
    """Multi-line editable text area."""
    def __init__(self, master, title="", height=6):
        super().__init__(master, bg=CARD)
        if title:
            tk.Label(self, text=title, bg=CARD, fg=TEXT2,
                     font=(UI, 9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.text = tk.Text(self, height=height, bg=ENTRY_BG, fg=TEXT,
                            font=FT_MONO_S, relief="flat",
                            insertbackground=CYAN, highlightthickness=1,
                            highlightbackground=BORDER2, highlightcolor=CYAN,
                            padx=12, pady=10, wrap="char",
                            selectbackground=SEL_BG)
        self.text.pack(fill="both", expand=True)

    def get(self): return self.text.get("1.0", "end").strip()
    def put(self, v): self.text.delete("1.0", "end"); self.text.insert("end", v)
    def clear(self): self.text.delete("1.0", "end")


def Btn(master, text, command, style="ghost", size="md"):
    styles = {
        "primary": (CYAN,   "#000"),
        "success": (GREEN,  "#000"),
        "warning": (AMBER,  "#000"),
        "danger":  (RED,    "#000"),
        "ghost":   (CYAN2,  CARD2),
        "muted":   (MUTED2, CARD),
        "violet":  (VIOLET, CARD2),
    }
    sizes = {
        "lg": ((UI, 10, "bold"), 22, 10),
        "md": ((UI, 10, "bold"), 16,  7),
        "sm": ((UI,  9, "bold"),  9,  4),
    }
    fg, bg = styles.get(style, styles["ghost"])
    font, px, py = sizes.get(size, sizes["md"])

    btn = tk.Button(master, text=text, command=command,
                    bg=bg, fg=fg, activebackground=CARD3, activeforeground=fg,
                    font=font, relief="flat", bd=0, cursor="hand2",
                    padx=px, pady=py)
    btn.bind("<Enter>", lambda e: btn.config(bg=CARD3))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def sep(parent, vertical=False, pad=6):
    if vertical:
        f = tk.Frame(parent, bg=BORDER, width=1)
        f.pack(side="left", fill="y", padx=pad)
    else:
        f = tk.Frame(parent, bg=BORDER, height=1)
        f.pack(fill="x", pady=pad)
    return f


def section(parent, title=None, tight=False):
    """Bordered card section."""
    outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    outer.pack(fill="both", expand=not tight, padx=6, pady=4)
    inner = tk.Frame(outer, bg=CARD, padx=14, pady=10)
    inner.pack(fill="both", expand=True)
    if title:
        tk.Label(inner, text=title, bg=CARD, fg=CYAN2,
                 font=(UI, 9, "bold"), anchor="w").pack(fill="x", pady=(0, 3))
        tk.Frame(inner, bg=BORDER2, height=1).pack(fill="x", pady=(0, 8))
    return inner


def row(parent, bg=None, pady=0):
    f = tk.Frame(parent, bg=bg or CARD)
    f.pack(fill="x", pady=pady)
    return f


def status_bar(parent, text="Ready"):
    lbl = tk.Label(parent, text=f"  {text}", bg=PANEL,
                   fg=MUTED2, font=(UI, 9), anchor="w")
    lbl.pack(fill="x", pady=(4, 0))
    return lbl

class CTRVizCanvas(tk.Canvas):
    """Live CTR-mode pipeline visualization."""
    W, H = 700, 240

    def __init__(self, master):
        super().__init__(master, bg=ENTRY_BG, height=self.H,
                         highlightthickness=1, highlightbackground=BORDER2)
        self.pack(fill="x", pady=(6, 0))
        self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        self._text(self.W // 2, self.H // 2,
                   "Encrypt or decrypt to see the CTR pipeline",
                   fill=MUTED, font=(UI, 10))

    def _text(self, x, y, t, **kw):
        self.create_text(x, y, text=t, anchor="center", **kw)

    def _box(self, x, y, w, h, fill, outline=BORDER3, text="", tfill=TEXT):
        self.create_rectangle(x, y, x+w, y+h, fill=fill, outline=outline, width=1)
        if text:
            self.create_text(x+w//2, y+h//2, text=text, fill=tfill,
                             font=(MONO, 9), anchor="center")

    def _arrow(self, x1, y1, x2, y2, color=MUTED2):
        self.create_line(x1, y1, x2, y2, fill=color, width=1,
                         arrow=tk.LAST, arrowshape=(8, 10, 3))

    def update_viz(self, key: int, nonce: int, pt_bytes: bytes, ct_bytes: bytes,
                   n_show: int = 3):
        self.delete("all")
        blocks = keystream_blocks(key, nonce, min(n_show, max(1, math.ceil(len(pt_bytes)/2))))
        bw = 150  
        pad = 18
        spacing = (self.W - pad * 2 - bw) / max(1, len(blocks) - 0.3)
        spacing = min(spacing, bw + 30)
        total_w = pad + len(blocks) * (bw + 30)
        start_x = max(pad, (self.W - total_w) // 2)

        cy_top, cy_bot = 30, self.H - 28

        for i, blk in enumerate(blocks):
            x = start_x + i * (bw + 36)
            pt_off = i * 2
            pt_nibble = pt_bytes[pt_off:pt_off+2] if pt_off < len(pt_bytes) else b""
            ct_nibble = ct_bytes[pt_off:pt_off+2] if pt_off < len(ct_bytes) else b""

            cb = blk["counter_block"]
            cb_hex = f"CTR[{i}]  0x{cb:04X}"
            self._text(x + bw//2, cy_top, cb_hex, fill=MUTED2, font=(MONO, 8))

            self._box(x, cy_top+12, bw//2, 28, CARD2, BORDER3,
                      f"N:0x{nonce:02X}", tfill=AMBER)
            self._box(x+bw//2, cy_top+12, bw//2, 28, CARD2, BORDER3,
                      f"C:{i:02d}", tfill=VIOLET)

            self._arrow(x+bw//2, cy_top+40, x+bw//2, cy_top+58, CYAN)

            self._box(x, cy_top+58, bw, 36, CYAN_DIM, CYAN,
                      "⚙  S-AES Enc", tfill=CYAN2)

            ks_hex = f"KS: 0x{blk['keystream']:04X}"
            self._arrow(x+bw//2, cy_top+94, x+bw//2, cy_top+112, CYAN)
            self._box(x, cy_top+112, bw, 26, CARD3, BORDER3, ks_hex, tfill=GREEN2)

            xor_y = cy_top + 152
            xor_cx = x + bw//2
            r = 12
            self.create_oval(xor_cx-r, xor_y-r, xor_cx+r, xor_y+r,
                             fill=CARD2, outline=AMBER, width=1)
            self.create_text(xor_cx, xor_y, text="⊕", fill=AMBER,
                             font=(UI, 13, "bold"))

            pt_hex = pt_nibble.hex().upper() if pt_nibble else "--"
            self._text(x + bw//2, xor_y - 28, f"PT: {pt_hex}",
                       fill=TEXT2, font=(MONO, 8))
            self._arrow(x+bw//2, xor_y-18, x+bw//2, xor_y-r-1, TEXT2)
            self._arrow(x+bw//2, cy_top+138, x+bw//2, xor_y-r-1, GREEN)

            ct_hex = ct_nibble.hex().upper() if ct_nibble else "--"
            self._arrow(x+bw//2, xor_y+r+1, x+bw//2, xor_y+32, RED)
            self._text(x + bw//2, xor_y + 44, f"CT: {ct_hex}",
                       fill=RED, font=(MONO, 8))

            if i < len(blocks) - 1:
                self.create_line(x+bw+3, cy_top+28, x+bw+33, cy_top+28,
                                 fill=BORDER3, width=1, dash=(4, 3))

        lx = self.W - 130
        ly = 8
        for idx, (txt, col) in enumerate([("Counter Block", VIOLET),
                                           ("KeyStream",     GREEN2),
                                           ("Plaintext",     TEXT2),
                                           ("Ciphertext",    RED)]):
            self.create_rectangle(lx, ly+idx*16, lx+10, ly+idx*16+10,
                                  fill=col, outline="")
            self.create_text(lx+14, ly+idx*16+5, text=txt, fill=TEXT2,
                             font=(UI, 8), anchor="w")


class KeyScheduleViz(tk.Canvas):
    """Visual key schedule expansion diagram."""
    W, H = 500, 130

    def __init__(self, master):
        super().__init__(master, bg=ENTRY_BG, height=self.H,
                         highlightthickness=1, highlightbackground=BORDER2)
        self.pack(fill="x", pady=(6, 0))
        self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        self.create_text(self.W//2, self.H//2,
                         text="Enter a key to see the key schedule",
                         fill=MUTED, font=(UI, 10))

    def update_ks(self, key: int):
        self.delete("all")
        K0, K1, K2 = key_schedule(key)

        labels = ["K0 (Round 0)", "K1 (Round 1)", "K2 (Round 2)"]
        values = [K0, K1, K2]
        colors = [CYAN, AMBER, VIOLET]
        bw, bh = 130, 50
        gap = 30
        total = 3 * bw + 2 * gap
        sx = (self.W - total) // 2
        cy = self.H // 2

        for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
            x = sx + i * (bw + gap)
            self.create_rectangle(x, cy-bh//2, x+bw, cy+bh//2,
                                  fill=CARD3, outline=col, width=1)
            self.create_text(x+bw//2, cy-12, text=lbl,
                             fill=col, font=(UI, 8, "bold"))
            self.create_text(x+bw//2, cy+5,  text=f"0x{val:04X}",
                             fill=TEXT, font=(MONO, 11, "bold"))
            self.create_text(x+bw//2, cy+22, text=f"{val:016b}",
                             fill=MUTED2, font=(MONO, 7))
            if i < 2:
                ax = x + bw + 2
                self.create_line(ax, cy, ax+gap-2, cy,
                                 fill=MUTED, width=1, arrow=tk.LAST,
                                 arrowshape=(7, 9, 3))
                self.create_text(ax+gap//2, cy-10, text="expand",
                                 fill=MUTED, font=(UI, 7))

        self.create_text(self.W//2, 10,
                         text=f"Key 0x{key:04X} → 3 Round Keys (RCON1=0x80, RCON2=0x30)",
                         fill=TEXT2, font=(UI, 8))


class FreqBarChart(tk.Canvas):
    """Animated frequency bar chart for analysis."""
    W, H = 700, 180

    def __init__(self, master):
        super().__init__(master, bg=ENTRY_BG, height=self.H,
                         highlightthickness=1, highlightbackground=BORDER2)
        self.pack(fill="x", pady=(6, 0))
        self._draw_idle()

    def _draw_idle(self):
        self.delete("all")
        self.create_text(self.W//2, self.H//2,
                         text="Frequency chart will appear after analysis",
                         fill=MUTED, font=(UI, 10))

    def update_chart(self, freq: dict, n: int):
        self.delete("all")
        if not freq:
            return

        pad_l, pad_r, pad_t, pad_b = 40, 10, 20, 30
        chart_w = self.W - pad_l - pad_r
        chart_h = self.H - pad_t - pad_b
        bar_w = chart_w / 256

        max_v = max(freq.values())

        for pct in [0.25, 0.5, 0.75, 1.0]:
            y = pad_t + chart_h * (1 - pct)
            self.create_line(pad_l, y, self.W - pad_r, y,
                             fill=BORDER, dash=(3, 4), width=1)
            self.create_text(pad_l - 6, y, text=f"{int(max_v*pct)}",
                             fill=MUTED2, font=(UI, 7), anchor="e")

        self.create_line(pad_l, pad_t, pad_l, pad_t+chart_h,
                         fill=BORDER2, width=1)
        self.create_line(pad_l, pad_t+chart_h, self.W-pad_r, pad_t+chart_h,
                         fill=BORDER2, width=1)

        for b in range(256):
            v = freq.get(b, 0)
            if v == 0:
                continue
            h = int(chart_h * v / max_v)
            x = pad_l + b * bar_w
            y = pad_t + chart_h - h
            ratio = b / 255
            r_c = int(0x00 + ratio * 0xff)
            g_c = int(0xff - ratio * 0x55)
            b_c = int(0x88 + ratio * 0x77)
            color = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
            self.create_rectangle(x, y, x+max(bar_w-0.5, 0.5),
                                  pad_t+chart_h, fill=color, outline="")

        for label_b in [0, 32, 64, 96, 128, 160, 192, 224, 255]:
            x = pad_l + label_b * bar_w
            self.create_text(x, pad_t+chart_h+12, text=f"{label_b:02X}",
                             fill=MUTED2, font=(UI, 7))

        expected_h = int(chart_h * (n / 256) / max_v) if max_v else 0
        y_ref = pad_t + chart_h - expected_h
        self.create_line(pad_l, y_ref, self.W-pad_r, y_ref,
                         fill=AMBER, dash=(5, 3), width=1)
        self.create_text(self.W-pad_r-2, y_ref-8, text="expected (uniform)",
                         fill=AMBER, font=(UI, 7), anchor="e")

        self.create_text(pad_l, pad_t-8,
                         text=f"Byte Frequency Distribution  ({n:,} bytes)",
                         fill=TEXT2, font=(UI, 8), anchor="w")

class EncryptPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self._enc_fp = ""
        self._cipher = b""
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        pc = section(left, "⚙  Parameters", tight=True)
        pr = row(pc)
        self.ek = LabeledEntry(pr, "Key  (16-bit  0–65535)", "0x006F", mono=True)
        self.en = LabeledEntry(pr, "Nonce  (8-bit  0–255)", "111", mono=True)
        self.ek.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.en.pack(side="left", fill="x", expand=True)
        self.ek.entry.bind("<FocusOut>", lambda e: self._validate())
        self.en.entry.bind("<FocusOut>", lambda e: self._validate())

        ks_c = section(left, "🔑  Key Schedule Visualization", tight=True)
        self.ks_viz = KeyScheduleViz(ks_c)

        ic = section(left, "📝  Plaintext Input")
        self._mode = tk.StringVar(value="text")
        mr = row(ic)
        for val, lbl in [("text", "Text"), ("file", "File / Binary")]:
            tk.Radiobutton(mr, text=lbl, variable=self._mode, value=val,
                           bg=CARD, fg=TEXT2, selectcolor=CARD,
                           activebackground=CARD, activeforeground=CYAN,
                           font=FT_BODY, cursor="hand2",
                           command=self._toggle_input).pack(side="left", padx=(0, 20))

        self._text_frame = tk.Frame(ic, bg=CARD)
        self._text_frame.pack(fill="both", expand=True)
        self.inp_text = InputBox(self._text_frame, height=7)
        self.inp_text.pack(fill="both", expand=True)
        self.inp_text.put("Hello! This is my IN410 S-AES project.")

        self._file_frame = tk.Frame(ic, bg=CARD)
        fr = row(self._file_frame)
        self._file_lbl = tk.Label(fr, text="  No file selected", bg=ENTRY_BG,
                                  fg=MUTED2, font=FT_BODY, anchor="w", pady=8,
                                  highlightthickness=1, highlightbackground=BORDER2)
        self._file_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        Btn(fr, "Browse…", self._pick_file, "ghost", "md").pack(side="right")

        br = row(ic, pady=(10, 0))
        Btn(br, "⚡  Encrypt", self._run, "primary", "lg").pack(side="left", padx=(0, 8))
        Btn(br, "⬇  Save .enc", self._save_enc, "ghost", "md").pack(side="left")
        self._status = status_bar(ic, "Ready")

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        oc = section(right, "🔐  Ciphertext Output")
        self.out_hex = OutputBox(oc, "Hex", height=4, accent=GREEN)
        self.out_hex.pack(fill="x")
        self.out_hex.set("— encrypt to see output —", color=MUTED)
        sep(oc)
        self.out_b64 = OutputBox(oc, "Base64", height=2, accent=CYAN2)
        self.out_b64.pack(fill="x")
        self.out_b64.set("—", color=MUTED)

        viz_c = section(right, "🔄  CTR Pipeline Visualization")
        self.ctr_viz = CTRVizCanvas(viz_c)

    def _toggle_input(self):
        if self._mode.get() == "text":
            self._file_frame.pack_forget()
            self._text_frame.pack(fill="both", expand=True)
        else:
            self._text_frame.pack_forget()
            self._file_frame.pack(fill="x")

    def _pick_file(self):
        p = filedialog.askopenfilename(title="Select file to encrypt")
        if p:
            self._enc_fp = p
            self._file_lbl.config(
                text=f"  📄  {os.path.basename(p)}  ({os.path.getsize(p):,} bytes)",
                fg=TEXT)

    def _validate(self):
        k, e = validate_key(self.ek.get())
        if k is None:
            self.ek.hint(e, ok=False)
        else:
            self.ek.hint(f"0x{k:04X}  =  {k}  =  {k:016b}b")
            self.ks_viz.update_ks(k)
        n, e2 = validate_nonce(self.en.get())
        if n is None:
            self.en.hint(e2, ok=False)
        else:
            self.en.hint(f"0x{n:02X}  =  {n}")
        return k, n

    def _run(self):
        k, n = self._validate()
        if k is None or n is None:
            return
        if self._mode.get() == "text":
            raw = self.inp_text.get()
            if not raw:
                messagebox.showerror("Missing", "Enter some plaintext first.")
                return
            data = raw.encode()
        else:
            if not self._enc_fp:
                messagebox.showerror("Missing", "Select a file first.")
                return
            with open(self._enc_fp, "rb") as f:
                data = f.read()

        cipher = ctr_process(data, k, n)
        self._cipher = cipher
        self.app.last_cipher = cipher
        self.app.last_key    = k
        self.app.last_nonce  = n

        self.out_hex.set(cipher.hex(), color=GREEN)
        self.out_b64.set(base64.b64encode(cipher).decode(), color=CYAN2)

        self.ctr_viz.update_viz(k, n, data, cipher, n_show=3)
        self.ks_viz.update_ks(k)

        self._status.config(
            text=f"  ✓  {len(data):,} bytes encrypted  ·  Key 0x{k:04X}  ·  Nonce {n}",
            fg=GREEN2)

    def _save_enc(self):
        if not self._cipher:
            messagebox.showinfo("", "Encrypt something first.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".enc",
                                         initialfile="ciphertext.enc",
                                         filetypes=[("Encrypted", "*.enc"), ("All", "*.*")])
        if p:
            with open(p, "wb") as f:
                f.write(self._cipher)
            messagebox.showinfo("Saved", f"Saved to:\n{p}")


class DecryptPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self._dec_file_bytes = None
        self._dec_file_path  = ""
        self._dec_output = None
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # Parameters
        pc = section(left, "⚙  Parameters", tight=True)
        pr = row(pc)
        self.dk = LabeledEntry(pr, "Key  (same as encryption)", "0x006F", mono=True)
        self.dn = LabeledEntry(pr, "Nonce  (same as encryption)", "111", mono=True)
        self.dk.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.dn.pack(side="left", fill="x", expand=True)
        Btn(pc, "⬆  Paste from Encrypt tab", self._paste_params, "muted", "sm")\
            .pack(anchor="w", pady=(8, 0))

        ks_c = section(left, "🔑  Key Schedule", tight=True)
        self.ks_viz = KeyScheduleViz(ks_c)

        ic = section(left, "🔡  Ciphertext Input")
        self._dm = tk.StringVar(value="hex")
        mr = row(ic)
        for val, lbl in [("hex", "Paste Hex"), ("file", "Load .enc File")]:
            tk.Radiobutton(mr, text=lbl, variable=self._dm, value=val,
                           bg=CARD, fg=TEXT2, selectcolor=CARD,
                           activebackground=CARD, activeforeground=CYAN,
                           font=FT_BODY, cursor="hand2",
                           command=self._toggle_input).pack(side="left", padx=(0, 20))

        self._hex_frame = tk.Frame(ic, bg=CARD)
        self._hex_frame.pack(fill="both", expand=True)
        self.inp_hex = InputBox(self._hex_frame, height=7)
        self.inp_hex.pack(fill="both", expand=True)

        self._file_frame = tk.Frame(ic, bg=CARD)
        fr = row(self._file_frame)
        self._file_lbl = tk.Label(fr, text="  No file selected", bg=ENTRY_BG,
                                  fg=MUTED2, font=FT_BODY, anchor="w", pady=8,
                                  highlightthickness=1, highlightbackground=BORDER2)
        self._file_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        Btn(fr, "Browse…", self._pick_file, "ghost", "md").pack(side="right")
        Btn(ic, "⬆  Paste ciphertext from Encrypt tab",
            self._paste_cipher, "muted", "sm").pack(anchor="w", pady=(8, 0))

        br = row(ic, pady=(10, 0))
        Btn(br, "🔓  Decrypt", self._run, "warning", "lg").pack(side="left", padx=(0, 8))
        Btn(br, "⬇  Save Output", self._save_out, "ghost", "md").pack(side="left")
        self._status = status_bar(ic, "Ready")

        oc = section(right, "✅  Decrypted Output")
        self.out = OutputBox(oc, "Plaintext", height=14, accent=GREEN)
        self.out.pack(fill="both", expand=True)
        self.out.set("— decrypt to see output —", color=MUTED)

        viz_c = section(right, "🔄  CTR Pipeline")
        self.ctr_viz = CTRVizCanvas(viz_c)

    def _toggle_input(self):
        if self._dm.get() == "hex":
            self._file_frame.pack_forget()
            self._hex_frame.pack(fill="both", expand=True)
        else:
            self._hex_frame.pack_forget()
            self._file_frame.pack(fill="x")

    def _pick_file(self):
        p = filedialog.askopenfilename(title="Select encrypted file")
        if p:
            self._dec_file_path = p
            with open(p, "rb") as f:
                self._dec_file_bytes = f.read()
            self._file_lbl.config(
                text=f"  🔒  {os.path.basename(p)}  ({len(self._dec_file_bytes):,} bytes)",
                fg=TEXT)

    def _paste_params(self):
        self.dk.set(self.app.last_key_str())
        self.dn.set(str(self.app.last_nonce))
        self._update_ks()

    def _paste_cipher(self):
        self.inp_hex.put(self.app.last_cipher.hex())

    def _update_ks(self):
        k, _ = validate_key(self.dk.get())
        if k is not None:
            self.ks_viz.update_ks(k)

    def _run(self):
        k, ek = validate_key(self.dk.get())
        n, en = validate_nonce(self.dn.get())
        if k is None:
            self.dk.hint(ek, ok=False); return
        if n is None:
            self.dn.hint(en, ok=False); return
        self.dk.hint(f"0x{k:04X}")
        self.dn.hint(f"{n}")

        if self._dm.get() == "hex":
            raw = self.inp_hex.get().replace(" ", "").replace("\n", "")
            if not raw:
                messagebox.showerror("Missing", "Paste ciphertext hex."); return
            try:
                ct = bytes.fromhex(raw)
            except Exception:
                messagebox.showerror("Invalid", "Bad hex string."); return
        else:
            if not self._dec_file_bytes:
                messagebox.showerror("Missing", "Select a file."); return
            ct = self._dec_file_bytes

        pt = ctr_process(ct, k, n)
        self._dec_output = pt
        try:
            disp = pt.decode("utf-8", errors="replace")
        except Exception:
            disp = pt.hex()
        self.out.set(disp, color=GREEN)
        self.ctr_viz.update_viz(k, n, ct, pt, n_show=3)
        self.ks_viz.update_ks(k)
        self._status.config(
            text=f"  ✓  {len(ct):,} bytes decrypted  ·  Key 0x{k:04X}  ·  Nonce {n}",
            fg=GREEN2)

    def _save_out(self):
        if not self._dec_output:
            messagebox.showinfo("", "Decrypt something first."); return
        orig_name = "decrypted_output"
        if hasattr(self, "_dec_file_path") and self._dec_file_path:
            base = os.path.splitext(os.path.basename(self._dec_file_path))[0]
            if base:
                orig_name = base
        p = filedialog.asksaveasfilename(
            defaultextension=".dec",
            initialfile=orig_name,
            filetypes=[
                ("Decrypted file", "*.dec"),
                ("Text file",      "*.txt"),
                ("All files",      "*.*"),
            ])
        if p:
            with open(p, "wb") as f:
                f.write(self._dec_output)
            messagebox.showinfo("Saved", f"Saved to:\n{p}")

class BruteForcePage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        tc = section(left, "🎯  Target Ciphertext", tight=False)
        self.bfc = InputBox(tc, title="Ciphertext hex", height=5)
        self.bfc.pack(fill="x")
        nr = row(tc, pady=(8, 0))
        self.bfn = LabeledEntry(nr, "Nonce (8-bit)", "111", mono=True)
        self.bfn.pack(side="left", fill="x", expand=True, padx=(0, 10))
        Btn(nr, "⬆  Use my ciphertext", self._paste_pre,
            "muted", "sm").pack(side="right", pady=(16, 0))

        mc = section(left, "⚔  Attack Strategy", tight=True)
        self._bfm = tk.StringVar(value="hint")
        for v, l, desc in [
            ("hint",  "🔍  Keyword Hint",    "Know a word in the message"),
            ("kpa",   "🎯  Known Plaintext",  "Know the exact beginning"),
            ("ascii", "📄  ASCII Heuristic",  "No prior knowledge needed"),
        ]:
            f = tk.Frame(mc, bg=CARD, pady=2)
            f.pack(fill="x")
            tk.Radiobutton(f, text=l, variable=self._bfm, value=v,
                           bg=CARD, fg=TEXT, selectcolor=CARD,
                           activebackground=CARD, activeforeground=CYAN,
                           font=(UI, 10, "bold"), cursor="hand2",
                           command=self._toggle_mode).pack(side="left")
            tk.Label(f, text=f"  — {desc}", bg=CARD, fg=MUTED2,
                     font=(UI, 8)).pack(side="left")

        self._hint_frame = tk.Frame(mc, bg=CARD)
        self._hint_frame.pack(fill="x", pady=(6, 0))
        self.bfhint = LabeledEntry(self._hint_frame, "Keyword expected in message", "project")
        self.bfhint.pack(fill="x")

        self._kpa_frame = tk.Frame(mc, bg=CARD)
        self.bfknown = LabeledEntry(self._kpa_frame, "Known start of plaintext", "Hello")
        self.bfknown.pack(fill="x")

        Btn(mc, "💀  Launch Brute Force  (65,536 keys)",
            self._run, "danger", "lg").pack(anchor="w", pady=(14, 0))

        rc = section(right, "📈  Progress & Results")
        self._prog_var = tk.DoubleVar()
        ttk.Style().configure("bf.Horizontal.TProgressbar",
                              troughcolor=ENTRY_BG, background=CYAN,
                              lightcolor=CYAN, darkcolor=CYAN, borderwidth=0)
        ttk.Progressbar(rc, variable=self._prog_var, maximum=65536,
                        style="bf.Horizontal.TProgressbar").pack(fill="x", pady=(0, 4))
        self._prog_lbl = tk.Label(rc, text="  Configure attack and click Launch",
                                  bg=CARD, fg=MUTED2, font=(UI, 9), anchor="w")
        self._prog_lbl.pack(fill="x", pady=(0, 6))

        sr = row(rc, pady=(0, 6))
        self._speed_lbl  = tk.Label(sr, text="Speed: —", bg=CARD, fg=CYAN2,
                                    font=(UI, 9))
        self._hits_lbl   = tk.Label(sr, text="Hits: —",  bg=CARD, fg=GREEN2,
                                    font=(UI, 9))
        self._speed_lbl.pack(side="left", padx=(0, 20))
        self._hits_lbl.pack(side="left")

        sep(rc)
        self.bfout = OutputBox(rc, "Candidates Found", height=20, accent=GREEN)
        self.bfout.pack(fill="both", expand=True)
        self.bfout.set("Results appear here after the attack.", color=MUTED)

        vc = section(right, "🎲  Key Space Scan", tight=True)
        self.scan_canvas = tk.Canvas(vc, bg=ENTRY_BG, height=80,
                                     highlightthickness=1,
                                     highlightbackground=BORDER2)
        self.scan_canvas.pack(fill="x")
        self._scan_idle()

    def _toggle_mode(self):
        self._hint_frame.pack_forget()
        self._kpa_frame.pack_forget()
        m = self._bfm.get()
        if m == "hint": self._hint_frame.pack(fill="x", pady=(6, 0))
        elif m == "kpa": self._kpa_frame.pack(fill="x", pady=(6, 0))

    def _paste_pre(self):
        self.bfc.put(self.app.last_cipher.hex())
        self.bfn.set(str(self.app.last_nonce))

    def _scan_idle(self):
        c = self.scan_canvas
        c.delete("all")
        c.create_text(c.winfo_reqwidth() // 2 or 300, 40,
                      text="Key space scan visualization", fill=MUTED, font=(UI, 9))

    def _update_scan(self, progress: int, hits: list[int]):
        c = self.scan_canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = 80
        scanned_w = int(w * progress / 65536)
        c.create_rectangle(0, 0, scanned_w, h, fill=CARD3, outline="")
        for hit_key in hits:
            hx = int(w * hit_key / 65536)
            c.create_line(hx, 0, hx, h, fill=GREEN, width=2)
        c.create_text(6, 6, text=f"Key space: 0x0000 → 0xFFFF", fill=MUTED2,
                      font=(UI, 7), anchor="nw")
        c.create_text(w - 6, 6, text=f"{progress:,} / 65,536 scanned",
                      fill=TEXT2, font=(UI, 7), anchor="ne")

    def _run(self):
        raw = self.bfc.get().replace(" ", "").replace("\n", "")
        if not raw:
            messagebox.showerror("Missing", "Paste ciphertext hex first."); return
        try:
            ct = bytes.fromhex(raw)
        except Exception:
            messagebox.showerror("Invalid", "Check hex string."); return
        n, e = validate_nonce(self.bfn.get())
        if n is None:
            self.bfn.hint(e, ok=False); return

        mode  = self._bfm.get()
        hint  = self.bfhint.get().strip()
        known = self.bfknown.get().strip().encode()

        self._prog_var.set(0)
        self.bfout.clear()
        self._prog_lbl.config(text="  Scanning…", fg=MUTED2)
        self._speed_lbl.config(text="Speed: —")
        self._hits_lbl.config(text="Hits: —")

        def worker():
            results = []
            hit_keys = []
            t0 = time.time()
            for key in range(0x10000):
                c = ctr_process(ct, key, n)
                match = False
                if mode == "kpa":
                    if c[:len(known)] == known:
                        match = True
                elif mode == "hint":
                    try:
                        t = c.decode("utf-8", errors="strict")
                        if hint.lower() in t.lower():
                            match = True
                    except Exception:
                        pass
                else:
                    if all(0x20 <= b < 0x7F or b in (9, 10, 13) for b in c):
                        match = True

                if match:
                    results.append((key, c))
                    hit_keys.append(key)

                if key % 1024 == 0:
                    elapsed = time.time() - t0
                    speed = int(key / elapsed) if elapsed > 0 else 0
                    self._prog_var.set(key)
                    self._prog_lbl.config(
                        text=f"  Scanning…  {key:,} / 65,536  ·  {len(results)} hit(s)",
                        fg=MUTED2)
                    self._speed_lbl.config(text=f"Speed: {speed:,} keys/s")
                    self._hits_lbl.config(text=f"Hits: {len(results)}")
                    self._update_scan(key, hit_keys)
                    self.update_idletasks()

                if mode == "kpa" and results:
                    break

            elapsed = round(time.time() - t0, 2)
            self._prog_var.set(65536)
            self._update_scan(65536, hit_keys)

            if results:
                self._prog_lbl.config(
                    text=f"  ✓  Done in {elapsed}s  ·  {len(results)} candidate(s) found",
                    fg=GREEN2)
                self._hits_lbl.config(text=f"Hits: {len(results)}", fg=GREEN2)
                lines = ["═" * 56,
                         f"  {len(results)} CANDIDATE(S) FOUND  —  {elapsed}s",
                         "═" * 56]
                for k, pt in results[:50]:
                    try:
                        txt = pt.decode("utf-8", errors="replace")
                    except Exception:
                        txt = pt.hex()
                    lines.append(
                        f"\n  Key   0x{k:04X}  (dec: {k})\n"
                        f"  Text  {txt[:100]}"
                    )
                self.bfout.set("\n".join(lines), color=GREEN)
            else:
                self._prog_lbl.config(
                    text="  ✗  No candidates found",
                    fg=RED)
                self.bfout.set(
                    "No results.\n\nTips:\n"
                    "  • Try ASCII Heuristic mode\n"
                    "  • Verify the nonce\n"
                    "  • Use Known Plaintext if you know the start",
                    color=RED)

        threading.Thread(target=worker, daemon=True).start()


class AnalysisPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        ic = section(left, "📥  Input Ciphertext", tight=False)
        self.ahex = InputBox(ic, title="Ciphertext hex", height=7)
        self.ahex.pack(fill="x")
        br = row(ic, pady=(10, 0))
        Btn(br, "📊  Analyse", self._run, "primary", "lg").pack(side="left", padx=(0, 8))
        Btn(br, "⬆  Use my ciphertext",
            lambda: self.ahex.put(self.app.last_cipher.hex()),
            "muted", "sm").pack(side="left")

        ioc_c = section(left, "📐  Index of Coincidence")
        self._ioc_val = tk.Label(ioc_c, text="—", bg=CARD,
                                 fg=CYAN, font=(SERIF, 42, "bold"))
        self._ioc_val.pack(pady=(4, 0))
        self._ioc_note = tk.Label(ioc_c, text="Run analysis to compute IoC",
                                  bg=CARD, fg=MUTED2, font=(UI, 9))
        self._ioc_note.pack(pady=(2, 10))
        sep(ioc_c)
        ref = row(ioc_c)
        for lbl, val, col in [("Random / CTR", "≈ 0.0385", GREEN),
                               ("English Text", "≈ 0.0650", AMBER)]:
            f = tk.Frame(ref, bg=CARD)
            f.pack(side="left", fill="x", expand=True, padx=4)
            tk.Label(f, text=val, bg=CARD, fg=col, font=(SERIF, 18, "bold")).pack()
            tk.Label(f, text=lbl, bg=CARD, fg=MUTED2, font=(UI, 8)).pack()

        ent_c = section(left, "🎲  Entropy & Stats", tight=True)
        self._ent_val  = tk.Label(ent_c, text="Entropy: —",
                                  bg=CARD, fg=VIOLET, font=(MONO, 11))
        self._uniq_val = tk.Label(ent_c, text="Unique bytes: —",
                                  bg=CARD, fg=TEXT2, font=(MONO, 10))
        self._ent_val.pack(anchor="w", pady=2)
        self._uniq_val.pack(anchor="w", pady=2)

        vc = section(right, "📊  Byte Frequency Distribution")
        self.chart = FreqBarChart(vc)

        rc = section(right, "📋  Detailed Report")
        self.rep_out = OutputBox(rc, "Full Report", height=16, accent=GREEN)
        self.rep_out.pack(fill="both", expand=True)
        self.rep_out.set("Run analysis to see the full report.", color=MUTED)

    def _entropy(self, freq: dict, n: int) -> float:
        ent = 0.0
        for f in freq.values():
            p = f / n
            if p > 0:
                ent -= p * math.log2(p)
        return ent

    def _run(self):
        raw = self.ahex.get().replace(" ", "").replace("\n", "")
        if not raw:
            messagebox.showerror("Missing", "Paste ciphertext first."); return
        try:
            data = bytes.fromhex(raw)
        except Exception:
            messagebox.showerror("Invalid", "Check the hex string."); return

        freq, ioc = frequency_analysis(data)
        n        = len(data)
        unique   = len(freq)
        ent      = self._entropy(freq, n)

        self._ioc_val.config(text=f"{ioc:.4f}")
        if ioc < 0.045:
            self._ioc_val.config(fg=GREEN)
            self._ioc_note.config(
                text="✓  Low IoC — CTR producing pseudo-random output", fg=GREEN2)
        elif ioc < 0.055:
            self._ioc_val.config(fg=AMBER)
            self._ioc_note.config(text="⚠  Borderline — check again", fg=AMBER)
        else:
            self._ioc_val.config(fg=RED)
            self._ioc_note.config(text="✗  High IoC — output is not random", fg=RED)

        self._ent_val.config(text=f"Shannon Entropy: {ent:.4f} bits/byte  (max 8.0)")
        self._uniq_val.config(text=f"Unique byte values: {unique} / 256")

        self.chart.update_chart(freq, n)

        lines = [
            "S-AES CTR — Frequency Analysis",
            "═" * 54,
            f"  Total bytes     : {n:,}",
            f"  Unique bytes    : {unique} / 256",
            f"  IoC (yours)     : {ioc:.6f}",
            f"  IoC (random)    : ~0.038500",
            f"  IoC (english)   : ~0.065000",
            f"  Shannon entropy : {ent:.6f} bits/byte",
            "",
            "Top 10 Most Frequent Bytes", "─" * 54,
            f"  {'Dec':>4}  {'Hex':>4}  {'Count':>5}  {'Freq':>6}  Bar",
        ]
        top = sorted(freq.items(), key=lambda x: -x[1])[:10]
        mc  = top[0][1] if top else 1
        for b, cnt in top:
            bar = "█" * int(cnt / mc * 28)
            lines.append(f"  {b:>4}  0x{b:02X}  {cnt:>5}  {cnt/n*100:>5.1f}%  {bar}")

        lines += ["", "Full Distribution  (non-zero only)", "─" * 54]
        for b in range(256):
            if b in freq:
                lines.append(f"  0x{b:02X} ({b:3d})  {freq[b]:>4}  {'▪'*min(freq[b], 40)}")

        self.rep_out.set("\n".join(lines), color=GREEN)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("S-AES  ·  CTR Mode  ·  IN410 Cryptography Lab")
        self.geometry("1280x760")
        self.minsize(1000, 640)
        self.configure(bg=BG)

        global MONO, FT_MONO, FT_MONO_S
        import tkinter.font as tkfont
        available = tkfont.families()
        for f in ("Cascadia Code", "JetBrains Mono", "Fira Code", "Consolas", "Courier New"):
            if f in available:
                MONO = f
                break
        FT_MONO   = (MONO, 10)
        FT_MONO_S = (MONO,  9)

        self.last_cipher: bytes = b""
        self.last_key:    int   = 0x006F
        self.last_nonce:  int   = 111

        self._pages: dict[str, tk.Frame] = {}
        self._tabs:  dict[str, TabButton] = {}

        self._build_shell()
        self._build_pages()
        self._show("encrypt")

    def last_key_str(self) -> str:
        return f"0x{self.last_key:04X}"

    def _build_shell(self):
        sidebar = tk.Frame(self, bg=SIDEBAR, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_frame = tk.Frame(sidebar, bg=SIDEBAR)
        logo_frame.pack(fill="x", pady=(18, 4))
        tk.Label(logo_frame, text="S-AES", bg=SIDEBAR, fg=CYAN,
                 font=(SERIF, 20, "bold")).pack()
        tk.Label(logo_frame, text="Counter Mode", bg=SIDEBAR, fg=MUTED2,
                 font=(UI, 9)).pack()
        tk.Label(logo_frame, text="IN410  ·  Cryptography Lab", bg=SIDEBAR,
                 fg=MUTED, font=(UI, 8)).pack(pady=(0, 6))

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=12, pady=6)

        tab_defs = [
            ("encrypt",   "🔐", "Encrypt",         "Plaintext → Ciphertext"),
            ("decrypt",   "🔓", "Decrypt",          "Ciphertext → Plaintext"),
            ("bruteforce","💀", "Brute Force",      "Attack — 65K keys"),
            ("analysis",  "📊", "Frequency Analysis","IoC · Entropy · Chart"),
        ]
        for key, icon, label, badge in tab_defs:
            btn = TabButton(sidebar, icon, label, badge,
                            command=lambda k=key: self._show(k))
            btn.pack(fill="x")
            self._tabs[key] = btn

        bottom = tk.Frame(sidebar, bg=SIDEBAR)
        bottom.pack(side="bottom", fill="x", pady=10)
        tk.Frame(bottom, bg=BORDER, height=1).pack(fill="x", padx=12, pady=(0, 8))
        for line, col in [
            ("16-bit key space", MUTED2),
            ("65,536 possible keys", MUTED),
            ("2-round Feistel", MUTED),
            ("GF(2⁴) arithmetic", MUTED),
        ]:
            tk.Label(bottom, text=line, bg=SIDEBAR, fg=col,
                     font=(UI, 8)).pack()

        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        topbar = tk.Frame(main, bg=PANEL, height=46)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self._page_title = tk.Label(topbar, text="", bg=PANEL, fg=TEXT,
                                    font=(SERIF, 14, "bold"), padx=20)
        self._page_title.pack(side="left", pady=6)
        tk.Label(topbar, text="Simplified AES  ·  CTR Mode  ·  IN410",
                 bg=PANEL, fg=MUTED, font=(UI, 9), padx=16).pack(side="right", pady=6)
        tk.Frame(main, bg=BORDER, height=1).pack(fill="x")

        self._content = tk.Frame(main, bg=BG)
        self._content.pack(fill="both", expand=True)

    def _build_pages(self):
        self._pages["encrypt"]    = EncryptPage(self._content, self)
        self._pages["decrypt"]    = DecryptPage(self._content, self)
        self._pages["bruteforce"] = BruteForcePage(self._content, self)
        self._pages["analysis"]   = AnalysisPage(self._content, self)

    def _show(self, key: str):
        titles = {
            "encrypt":    "Encrypt",
            "decrypt":    "Decrypt",
            "bruteforce": "Brute Force Attack",
            "analysis":   "Frequency Analysis",
        }
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        for k, tab in self._tabs.items():
            tab.set_active(k == key)
        self._page_title.config(text=titles.get(key, ""))


if __name__ == "__main__":
    App().mainloop()
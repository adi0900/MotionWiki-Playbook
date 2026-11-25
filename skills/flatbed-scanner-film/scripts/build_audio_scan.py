#!/usr/bin/env python3
"""
Synthesize a razor-tight 14.50s flatbed-scanner + pulsing dark-synth + modular-arp soundtrack
synced to the exact cut & scan-bar timestamps of the 14.5s (435f @ 30fps) scanner edit.
"""
import argparse, math, os, wave
import numpy as np


def build_soundtrack(out_path: str, seed: int = 202611249) -> None:
    SR = 44100
    DUR = 14.5
    N = int(SR * DUR)
    rng = np.random.default_rng(seed)
    left = np.zeros(N, dtype=np.float64)
    right = np.zeros(N, dtype=np.float64)

    def add_s(t0, sl, sr=None, g=1.0):
        if sr is None:
            sr = sl
        i = int(t0 * SR)
        if i >= N:
            return
        e = min(N, i + len(sl))
        L = e - i
        if L > 0:
            left[i:e] += sl[:L] * g
            right[i:e] += sr[:L] * g

    # 1. Mechanical scanner carriage ratchet startup (0.00-0.75s)
    for k, kt in enumerate([0.04, 0.12, 0.21, 0.31, 0.42, 0.54, 0.66]):
        dn = int(0.028 * SR)
        tt = np.arange(dn) / SR
        f = 2200.0 + (k % 3) * 750.0
        click = (np.sin(2 * np.pi * f * tt) * 0.6 + np.sin(2 * np.pi * f * 2.37 * tt) * 0.4) * np.exp(-tt * 150.0)
        pan = 0.25 + 0.5 * (k % 2)
        add_s(kt, click * (1 - pan * 0.4), click * (0.6 + pan * 0.4), 0.28)

    # 2. Gritty pulsing acid-saw sub-bass bed (0.80s .. 14.45s)
    bass_sections = [
        (0.80,  4.00,  55.00),   # A1
        (4.00,  5.60,  65.41),   # C2
        (5.60,  9.20,  49.00),   # G1
        (9.20,  10.60, 55.00),   # A1
        (10.60, 12.20, 61.74),   # B1
        (12.20, 13.10, 65.41),   # C2 strobe climax
        (13.10, 14.45, 55.00),   # A1 resolve
    ]
    for s0, s1, f0 in bass_sections:
        dur = s1 - s0
        ns = int(dur * SR)
        tt = np.arange(ns) / SR
        sig = (
            np.sin(2 * np.pi * f0 * tt)
            + 0.45 * np.sin(2 * np.pi * f0 * 2 * tt)
            + 0.25 * np.sin(2 * np.pi * f0 * 3 * tt)
            + 0.14 * np.sin(2 * np.pi * f0 * 4 * tt)
        )
        sig = np.tanh(sig * 1.65)
        pulse = 0.44 + 0.56 * (0.5 + 0.5 * np.sin(2 * np.pi * 4.5 * tt - math.pi / 2)) ** 1.4
        env = np.minimum(1.0, tt / 0.025) * np.minimum(1.0, (dur - tt) / 0.06)
        if s0 >= 13.10:
            env *= np.exp(-np.maximum(0.0, tt - 0.65) * 2.2)
        add_s(s0, sig * pulse * env, sig * pulse * env, 0.27)

    # 3. Optical flatbed scanner servo sweep + white-noise light-bar whoosh
    scan_windows = [
        (0.80,  2.75, 220.0, 760.0),   # SCAN 01
        (5.60,  7.55, 700.0, 240.0),   # SCAN 02 vertical downward
        (10.60, 12.15, 260.0, 840.0),  # SCAN 03
        (13.10, 14.15, 250.0, 980.0),  # SCAN 04 finale
    ]
    for s0, s1, fa, fb in scan_windows:
        dur = s1 - s0
        ns = int(dur * SR)
        tt = np.arange(ns) / SR
        freq = fa + (fb - fa) * (tt / dur)
        ph = 2 * np.pi * np.cumsum(freq) / SR
        motor = np.sin(ph) * 0.5 + np.sin(ph * 2.01) * 0.3 + np.sin(ph * 3.03) * 0.15
        noise = rng.standard_normal(ns)
        wn = np.convolve(noise, np.ones(8) / 8.0, mode="same")
        env = np.sin(np.pi * tt / dur) ** 0.75
        add_s(s0, (motor * 0.11 + wn * 0.13) * env, (motor * 0.11 + wn * 0.13) * env, 0.95)

    # 4. Crisp modular computer-vision glitch arpeggios on PLATE 01, PLATE 02, and Strobe Climax
    arp_runs = [
        (2.78,  [880, 1174.66, 1318.51, 1760, 1318.51, 1567.98, 2093.00, 1760], 0.08),
        (7.58,  [783.99, 1046.50, 1318.51, 1567.98, 1975.53, 1567.98, 1174.66, 880], 0.08),
        (12.18, [880, 1318.51, 1760, 2093, 1760, 2349.32, 1760, 2637.02, 2093, 1760, 1318.51], 0.072),
    ]
    for t_start, freqs, step in arp_runs:
        for idx, f in enumerate(freqs):
            t0 = t_start + idx * step
            dn = int(0.10 * SR)
            tt = np.arange(dn) / SR
            mod = np.sin(2 * np.pi * f * 3.0 * tt) * np.exp(-tt * 35.0) * 1.8
            tone = np.sin(2 * np.pi * f * tt + mod) * np.exp(-tt * 28.0)
            pan = 0.2 + 0.6 * ((idx % 4) / 3.0)
            add_s(t0, tone * (1 - pan * 0.5), tone * (0.5 + pan * 0.5), 0.17)

    # 5. Punchy electronic kick + optical shutter impacts on every exact cut
    cut_hits = [
        0.80, 2.80, 3.20, 3.60, 4.00, 5.60, 7.60, 8.20, 8.60,
        9.20, 9.85, 10.60, 12.20, 12.43, 12.66, 12.88, 13.10, 14.12,
    ]
    for ct in cut_hits:
        dn = int(0.16 * SR)
        tt = np.arange(dn) / SR
        f = 42.0 + 145.0 * np.exp(-tt * 44.0)
        ph = 2 * np.pi * np.cumsum(f) / SR
        kick = np.tanh(np.sin(ph) * np.exp(-tt * 17.0) * 1.5)
        sn = int(0.042 * SR)
        tts = np.arange(sn) / SR
        shutter = np.diff(rng.standard_normal(sn), prepend=0.0)
        shutter /= np.max(np.abs(shutter)) + 1e-6
        shutter *= np.exp(-tts * 72.0)
        add_s(ct, kick, kick, 0.35)
        add_s(ct, shutter, shutter, 0.22)

    # 6. Crystalline lock-in chime at 14.08s
    dn = int(0.40 * SR)
    tt = np.arange(dn) / SR
    lock = (np.sin(2 * np.pi * 1318.51 * tt) + 0.6 * np.sin(2 * np.pi * 1760.0 * tt)) * np.exp(-tt * 7.5)
    add_s(14.08, lock, lock, 0.17)

    # Master soft limiter + clean tail fade
    fade_n = int(0.20 * SR)
    fade = np.linspace(1.0, 0.0, fade_n)
    left[-fade_n:] *= fade
    right[-fade_n:] *= fade
    pk = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-6)
    left = np.tanh(left / pk * 1.2) * 0.90
    right = np.tanh(right / pk * 1.2) * 0.90

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    inter = np.empty((N * 2,), dtype=np.int16)
    inter[0::2] = np.clip(left * 32767.0, -32768, 32767).astype(np.int16)
    inter[1::2] = np.clip(right * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(inter.tobytes())
    print(f"[Audio] Wrote {out_path} ({DUR}s stereo 44.1kHz)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Synthesize 14.5s optical flatbed scanner soundtrack")
    ap.add_argument("--out", required=True, help="Output WAV path")
    ap.add_argument("--seed", type=int, default=202611249)
    a = ap.parse_args()
    build_soundtrack(a.out, a.seed)

#!/usr/bin/env python3
"""DoReMi .drm (tonic sol-fa text) -> note events -> MIDI / WAV.
Format reverse-engineered from the DoReMi v2.2 Android app (mg.maniry.doremii)."""
import re, struct, sys, math, wave, array, pathlib

PPQ = 480                      # ticks per beat (cell)
SOLFA = ["d","di","r","ri","m","f","fi","s","si","l","ta","t"]   # 12 semitones
KEYS  = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]   # P_KEY index
VEL   = {"pp":78,"p":84,"mp":90,"mf":100,"f":110,"ff":120}
DEFAULT_VEL = 110
GAP = 10                       # ticks cut from each note (articulation)
BASE = 60                      # 'd' = C4 for S/A ; T/B are 12 semitones lower
SF_INSTR = ["Piano","Strings","Organ","EP Verby","EP Rhodes"]  # assets/soundfonts/*.sf2

def parse(text):
    head, *voices = text.strip().split("__!!__")
    meta = {}
    for part in head.split(";"):
        if ":" in part:
            k, v = part.strip().split(":", 1); meta[k.strip()] = v.strip()
    voices = [v for v in voices if v.strip() != ""]
    names = meta.get("VOICES", "S,A,T,B").split(",")
    changes = []
    for c in filter(None, meta.get("CHANGES", "").split(",")):
        col, typ, val = c.split("_", 2); changes.append((int(col), typ, val))
    return meta, names, [v.split(":") for v in voices], changes

def pitch_of(tok, voice):
    m = re.match(r"^[a-z]+", tok); o = re.search(r"-?\d+$", tok)
    if not m or m.group(0) not in SOLFA: return None
    key = int(0)
    return SOLFA.index(m.group(0)) + (int(o.group(0)) * 12 if o else 0) + (-12 if voice in "TB" else 0)

def cell_slots(cell):
    """cell -> [(offset, dur, token)] in fractions of one beat. token '' = empty, '-' = hold"""
    cell = cell.replace(" ", "")
    if cell == "": return [(0, 1, "")]
    if ".," in cell:                      # dotted: 3/4 + 1/4
        a, b = cell.split(".,", 1)
        return [(0, .75, a), (.75, .25, b)]
    halves = cell.split(".")
    out, t = [], 0
    for h in halves:
        parts = h.split(",")
        for p in parts:
            d = 1 / len(halves) / len(parts); out.append((t, d, p)); t += d
    return out

def expand_order(ncols, changes):
    marks = {c: v for c, t, v in changes if t == "SI"}
    jumps = {c: v for c, t, v in changes if t == "DL"}
    lab = {v: c for c, v in marks.items()}
    order, i, used, after_dc = [], 0, set(), False
    while i < ncols and len(order) < ncols * 6:
        order.append(i)
        if marks.get(i) == "Fin" and after_dc: break
        if i in jumps and i not in used:
            used.add(i); tgt = jumps[i]
            if tgt == "DC": i, after_dc = 0, True; continue
            if tgt.startswith("D") and tgt[1:] in lab: i = lab[tgt[1:]]; continue
        i += 1
    return order

def build(text):
    meta, names, voices, changes = parse(text)
    ncols = max(len(v) for v in voices)
    order = expand_order(ncols, changes)
    vel_at, tempo_at = {}, {}
    for c, t, v in changes:
        if t == "VEL" and v in VEL: vel_at[c] = VEL[v]
        if t == "MV": tempo_at[c] = int(v)
    notes, tempos, tick = [], [], 0          # note=(start,dur,pitch,vel,voice_idx)
    vel = DEFAULT_VEL; tempo = int(meta.get("P_TEMPO", 100))
    key = int(meta.get("P_KEY", 0))
    tempos.append((0, tempo))
    last = {}                                # voice -> index of last note (for ties)
    for col in order:
        if col in vel_at: vel = vel_at[col]
        if col in tempo_at: tempo = tempo_at[col]; tempos.append((tick, tempo))
        for vi, cells in enumerate(voices):
            cell = cells[col] if col < len(cells) else ""
            v = names[vi] if vi < len(names) else "S"
            slots = cell_slots(cell); multi = len(slots) > 1
            for si, (off, dur, tok) in enumerate(slots):
                s, d = tick + round(off * PPQ), round(dur * PPQ)
                if tok == "-" or (tok == "" and multi and si == 0 and vi in last):
                    if vi in last: n = notes[last[vi]]; notes[last[vi]] = (n[0], n[1] + d, *n[2:])
                elif tok == "":
                    last.pop(vi, None)
                else:
                    p = pitch_of(tok, v)
                    if p is None: continue
                    notes.append((s, d, BASE + key + p, vel, vi)); last[vi] = len(notes) - 1
        tick += PPQ
    notes = [(s, max(d - GAP, 30), p, vl, vi) for s, d, p, vl, vi in notes]
    return meta, names, notes, tempos, instr(meta)

def instr(meta):
    return [int(x) for x in meta.get("INSTR", "0,0,0,0").replace(" ", "").split(",")]

# ---------- MIDI (format 1, one track per voice) ----------
def vlq(n):
    b = [n & 0x7f]; n >>= 7
    while n: b.append((n & 0x7f) | 0x80); n >>= 7
    return bytes(reversed(b))

def chunk(t, d): return t + struct.pack(">I", len(d)) + d

# General MIDI programs chosen to resemble the app's soundfonts (see SF_INSTR). 13+ => app-specific.
GM = {0: 0, 1: 48, 2: 19, 3: 4, 4: 4}
def write_midi(path, meta, names, notes, tempos, ins):
    tracks = []
    t0 = b"".join(vlq(t - (tempos[i-1][0] if i else 0)) + b"\xff\x51\x03" + int(60_000_000 / bpm).to_bytes(3, "big")
                  for i, (t, bpm) in enumerate(tempos))
    t0 = vlq(0) + b"\xff\x03" + bytes([len(meta.get("P_TITLE","")[:60].encode())]) + meta.get("P_TITLE","")[:60].encode() + t0
    tracks.append(chunk(b"MTrk", t0 + vlq(0) + b"\xff\x2f\x00"))
    for vi in range(len(names)):
        ch = vi; ev = []
        for s, d, p, vl, v in notes:
            if v == vi and 0 <= p < 128: ev += [(s, 1, p, vl), (s + d, 0, p, 0)]
        ev.sort(key=lambda e: (e[0], e[1]))
        prog = GM.get(ins[vi] if vi < len(ins) else 0, 0)
        d = vlq(0) + bytes([0xC0 | ch, prog]); last = 0
        for t, on, p, vl in ev:
            d += vlq(t - last) + bytes([(0x90 if on else 0x80) | ch, p, vl]); last = t
        tracks.append(chunk(b"MTrk", d + vlq(0) + b"\xff\x2f\x00"))
    pathlib.Path(path).write_bytes(chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), PPQ)) + b"".join(tracks))

# ---------- tiny additive-synth WAV preview (no dependencies) ----------
def write_wav(path, notes, tempos, sr=22050):
    def sec(tick):
        t, s, prev, bpm = tick, 0.0, 0, tempos[0][1]
        s = 0.0; prev = 0; bpm = tempos[0][1]
        for tk, b in tempos[1:]:
            if tk >= tick: break
            s += (tk - prev) / PPQ * 60 / bpm; prev, bpm = tk, b
        return s + (tick - prev) / PPQ * 60 / bpm
    end = max(sec(s + d) for s, d, *_ in notes) + 1.0
    buf = array.array("f", [0.0]) * int(end * sr)
    for s, d, p, vl, vi in notes:
        t0, t1 = sec(s), sec(s + d); f = 440 * 2 ** ((p - 69) / 12); a = vl / 127 * 0.12
        n0, n = int(t0 * sr), int((t1 - t0 + .15) * sr)
        for k in range(n):
            t = k / sr; rel = max(0, t - (t1 - t0))
            env = min(1, t / .01) * math.exp(-rel * 25) * (0.6 + 0.4 * math.exp(-t * 2))
            buf[n0 + k] += a * env * (math.sin(2*math.pi*f*t) + .3*math.sin(4*math.pi*f*t) + .1*math.sin(6*math.pi*f*t))
    pk = max(abs(x) for x in buf) or 1
    pcm = array.array("h", (int(x / pk * 30000) for x in buf))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

if __name__ == "__main__":
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    meta, names, notes, tempos, ins = build(src.read_text(encoding="utf-8"))
    write_midi(out / (src.stem + ".mid"), meta, names, notes, tempos, ins)
    if "--wav" in sys.argv: write_wav(out / (src.stem + ".wav"), notes, tempos)
    print(f"{src.name}: {len(notes)} notes, {len(tempos)} tempo marks, key={KEYS[int(meta.get('P_KEY',0))]}, "
          f"title={meta.get('P_TITLE')!r}")

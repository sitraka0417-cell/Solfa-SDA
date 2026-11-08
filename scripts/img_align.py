"""Align printed lyrics to notes using the scan page image (the print is monospaced).
analyse(song, page_png) -> {"systems":[{"lines":[[ [slotIndex, text, devChars], ...], ...]}], "errors":[...]}
slotIndex indexes the non-blank slots of the soprano row of that system, in order."""
import sys, re, numpy as np, pathlib
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lyralign import syl2

def bands(a, gap=14):
    rows = a.sum(1) > 0; out = []; s = None; g = 0
    for y, r in enumerate(rows):
        if r:
            if s is None: s = y
            g = 0; e = y
        elif s is not None:
            g += 1
            if g > gap: out.append((s, e)); s = None
    if s is not None: out.append((s, e))
    return out

def runs(m, gap):
    xs = np.where(m)[0]; out = []
    if not len(xs): return out
    s = p = xs[0]
    for x in xs[1:]:
        if x - p > gap: out.append((s, p)); s = x
        p = x
    out.append((s, p)); return out

def slots_of(S, a, b):
    return [(c, k) for c in range(a, b) for k, s in enumerate(S[c]) if s[2] != ""]

def prep(song, page, row=0):
    im = np.array(Image.open(page).convert("L")) < 200
    sb = [b for b in bands(im) if b[1] - b[0] > 60]
    bf = pathlib.Path(page).with_suffix(".bands.json")
    if bf.exists(): import json; sb = [tuple(x) for x in json.loads(bf.read_text())]
    if len(sb) != len(song["systems"]): return None, [f"bands {len(sb)} != systems {len(song['systems'])}"]
    hs = [b - a for a, b in sb]
    if len(sb) > 2 and hs[0] > 1.25 * float(np.median(hs[1:])): sb[0] = (int(sb[0][1] - np.median(hs[1:])), sb[0][1])
    S = song["grid"][row]; out = []; errs = []
    for si, (sy, (y0, y1)) in enumerate(zip(song["systems"], sb)):
        blk = im[y0:y1 + 1].copy()
        hl = ndi.binary_opening(blk, structure=np.ones((1, 25)))
        vl = ndi.binary_opening(blk, structure=np.ones((22, 1)))
        vr = runs(vl.any(0), 3); xlo = vr[0][1] + 6 if vr else 0; xhi = vr[-1][0] if vr else blk.shape[1]
        blk[:, xhi + 4:] = False
        blk &= ~ndi.binary_dilation(hl, structure=np.ones((3, 1)))
        blk &= ~ndi.binary_dilation(vl, structure=np.ones((1, 3)))
        lab, n = ndi.label(blk, structure=np.ones((3, 3)))
        for i, o in enumerate(ndi.find_objects(lab), 1):
            if o[0].stop - o[0].start > 26: blk[lab == i] = False
        L = len(sy["lyrics"]); bs = [b for b in bands(blk, gap=3) if b[1] - b[0] >= 4]
        if len(bs) < 1 + L: errs.append(f"sys {si+1}: {len(bs)} text bands < {1+L}"); out.append(None); continue
        lyb = list(bs[-L:])
        med = float(np.median([b - a for a, b in lyb[1:]] or [b - a for a, b in lyb]))
        if lyb[0][1] - lyb[0][0] > 1.4 * med: lyb[0] = (int(lyb[0][1] - med), lyb[0][1])
        rt = np.where(vl.any(1))[0]; ytop = int(rt[0]) if len(rt) else 0
        sb0 = next((b for b in bs if b[1] >= ytop + 6), bs[0])
        if row == 3: sb0 = bs[-(L + 1)]
        seg = ndi.binary_closing(blk[sb0[0]:sb0[1] + 1], structure=np.ones((3, 3)))
        lab2, _ = ndi.label(seg, structure=np.ones((3, 3))); boxes = []
        for o in ndi.find_objects(lab2):
            h = o[0].stop - o[0].start; w = o[1].stop - o[1].start
            if not (xlo < o[1].start and o[1].stop < xhi): continue
            if h >= 6 and w >= 3: boxes.append([o[1].start, o[1].stop, 0])
            elif h <= 5 and 6 <= w <= 16 and 3 <= o[0].start <= 10: boxes.append([o[1].start, o[1].stop, 1])
        boxes.sort(); mg = []
        lw = [b[1] - b[0] for b in boxes if b[2] == 0]; mgap = 0.45 * float(np.median(lw)) if lw else 3
        for b in boxes:
            if mg and b[2] == 0 and mg[-1][2] == 0 and b[0] - mg[-1][1] <= mgap: mg[-1][1] = b[1]
            else: mg.append(list(b))
        mg = [m for m in mg if m[2] == 1 or m[1] - m[0] >= 5]
        if len(vr) > 1 and lw:
            medw = float(np.median(lw)); xbar = vr[1][0]
            zone = [m for m in mg if m[1] < xbar and m[2] == 0]
            if len(zone) >= 2 and any((m[1] - m[0]) <= 0.8 * medw for m in zone):      # printed pivot "old/new": keep the new-key note only
                keep = zone[-1]; mg = [m for m in mg if m not in zone[:-1]]
                if keep[1] - keep[0] > 1.15 * medw: keep[0] = keep[1] - int(medw)
        on = slots_of(S, sy["start"], sy["end"])
        if len(on) != len(mg): errs.append(f"sys {si+1}: {len(on)} note slots in transcription != {len(mg)} glyphs in image"); out.append(None); continue
        out.append({"blk": blk, "lyb": lyb, "lx": [m[0] for m in mg], "on": on, "kinds": [m[2] for m in mg], "lyrics": sy["lyrics"], "xhi": xhi})
    return out, errs

def grid_cells(prof, pitch):
    """phase search on column ink profile; returns list of occupied cell start x (monospace grid)."""
    n = len(prof); best = None
    for ph in np.arange(0, pitch, 0.5):
        edges = np.arange(ph, n, pitch)
        cost = sum(prof[int(e)] + prof[max(0, int(e) - 1)] for e in edges if 0 <= int(e) < n)
        if best is None or cost < best[0]: best = (cost, ph)
    ph = best[1]; cells = []
    for e in np.arange(ph, n - pitch / 2, pitch):
        a, b = int(e + pitch * 0.2), int(e + pitch * 0.8)
        if prof[a:b + 1].sum() >= 2: cells.append(float(e))
    return cells

def parse_line(col, line, pitch):
    sy2 = syl2(line); syl = [d for d, n in sy2]
    T = sum(n for d, n in sy2)
    cells = grid_cells(col.astype(float), pitch)
    d = abs(len(cells) - T); bad = 0 if d == 0 else (0.5 + d if d <= 2 else d * 2)
    pos = []; k = 0; sc = len(cells) / T if T else 1
    for s, (_d, nn) in zip(syl, sy2):
        kk = min(len(cells) - 1, int(round(k * sc))) if d else k
        pos.append(cells[kk] + pitch * 0.3 if 0 <= kk < len(cells) else 1e6); k += nn
    return bad, syl, pos, cells

def assign(pos, lx, pitch):
    m, K = len(pos), len(lx); INF = 1e9
    if m > K: return None
    cost = np.full((m + 1, K + 1), INF); cost[0, :] = 0; arg = {}
    for i in range(1, m + 1):
        for j in range(i, K + 1):
            c0 = cost[i - 1, j - 1] + abs(pos[i - 1] - lx[j - 1]) / pitch
            c1 = cost[i, j - 1] if j - 1 >= i else INF
            if c0 <= c1: cost[i, j] = c0; arg[i, j] = 1
            else: cost[i, j] = c1; arg[i, j] = 0
    i, j, asg = m, K, [None] * m
    while i > 0:
        if arg[i, j]: asg[i - 1] = j - 1; i -= 1; j -= 1
        else: j -= 1
    return asg

def analyse(song, page, pitch=None, row=0):
    P, errs = prep(song, page, row)
    res = {"systems": [], "errors": list(errs), "pitch": None}
    if P is None: return res
    items = [(si, li, p, line) for si, p in enumerate(P) if p for li, line in enumerate(p["lyrics"])]
    def cols(p, li):
        a, b = p["lyb"][li]; c = p["blk"][a:b + 1].sum(0).copy(); c[p["xhi"] + 4:] = 0; return c
    if pitch is None:
        best = None
        for pt in np.arange(8, 22, 0.2):
            tot = sum(parse_line(cols(p, li), line, pt)[0] for si, li, p, line in items)
            if best is None or tot < best[0] - 1e-9: best = (tot, pt)
        pitch = best[1]
    res["pitch"] = float(pitch)
    for si, p in enumerate(P):
        if not p: res["systems"].append(None); continue
        lines = []
        for li, line in enumerate(p["lyrics"]):
            cand = None
            for pt in np.arange(pitch * 0.96, pitch * 1.04, pitch * 0.004):
                r = parse_line(cols(p, li), line, pt)
                if cand is None or r[0] < cand[0][0]: cand = (r, pt)
            (bad, syl, pos, cells), pt = cand
            if bad > 3:
                res["errors"].append(f"sys {si+1} lyric {li+1}: ink chars {len(cells)} vs mine {sum(len(x) for x in line.split())}  « {line} »")
                lines.append(None); continue
            lidx = [i for i, k in enumerate(p["kinds"]) if k == 0]
            asg = assign(pos, [p["lx"][i] for i in lidx], pt)
            if asg is not None: asg = [lidx[a] for a in asg]
            else: asg = assign(pos, p["lx"], pt)
            if asg is None: res["errors"].append(f"sys {si+1} lyric {li+1}: more syllables than notes"); lines.append(None); continue
            lines.append([[asg[q], syl[q], round(abs(pos[q] - p["lx"][asg[q]]) / pt, 2)] for q in range(len(syl))])
        res["systems"].append({"slots": p["on"], "lines": lines})
    return res

"""Align lyrics to notes for every hymn that has a scan page (scans/pages/NNN.png), using image analysis
with a rule-based fallback. Needs app/data/songs/*.json (run build_all.py first).
Writes scans/align/NNN.json = {"systems":[{"lines":[{"label","approx","items":[[cell,slot,text],..]}]}]}"""
import sys, json, re, glob, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import img_align
from lyralign import syl2

def strip_label(line):
    m = re.match(r"^\(([^)]*)\)\s*(.*)$", line)
    return (m.group(1), m.group(2)) if m else ("", line)

VOICE = {"S": 0, "A": 1, "T": 2, "B": 3}
def rule_align(grid, a, b, line, label=""):
    """syllables -> note onsets of the voice named first in the label (default soprano), in order"""
    m = re.match(r"^([SATB])(?:@(\d+))?", label.strip().upper()) if label else None
    S = grid[VOICE[m.group(1)] if m else 0]; skip = int(m.group(2) or 0) if m else 0
    syl = [d for d, n in syl2(line)]; on = [(c, k) for c in range(a, b) for k, s in enumerate(S[c]) if isinstance(s[2], list)][skip:]
    if len(syl) == len(on) or not on or not syl:
        return [[c, k, t] for (c, k), t in zip(on, syl) if t], len(syl) == len(on)
    # counts differ: spread the syllables proportionally over the notes (approximate; flagged)
    out = {}; n, m = len(syl), len(on)
    for i, t in enumerate(syl):
        j = round(i * (m - 1) / (n - 1)) if n > 1 else 0
        out[j] = (out[j] + t) if j in out else t
    return [[on[j][0], on[j][1], t] for j, t in sorted(out.items()) if t], False

def main():
    (ROOT / "scans" / "align").mkdir(exist_ok=True)
    for jf in sorted(glob.glob(str(ROOT / "app/data/songs/*.json"))):
        song = json.load(open(jf)); num = song["number"]
        S = song["grid"][0]
        # image analysis works on label-stripped lyric text
        labels, clean = [], []
        for sy in song["systems"]:
            ll = [strip_label(l) for l in sy["lyrics"]]; labels.append([x[0] for x in ll]); clean.append([x[1] for x in ll])
        sdict = {**song, "systems": [{**sy, "lyrics": c} for sy, c in zip(song["systems"], clean)]}
        page = ROOT / "scans" / "pages" / f"{num:03d}.png"
        txt = next(iter(sorted((ROOT / "scans").glob(f"{num:03d}_*.txt"))), None)
        rule_only = txt is not None and re.search(r"^align:\s*rule", txt.read_text(encoding="utf-8"), re.M)
        row_b = txt is not None and re.search(r"^align:\s*image-B", txt.read_text(encoding="utf-8"), re.M)
        bmap = []
        if row_b:   # only the bass lyric lines (bottom of each system) are read from the image; their notes are the bass row
            bmap = [[i for i, l in enumerate(sy["lyrics"]) if labels[si][i].strip().upper().startswith("B")] for si, sy in enumerate(song["systems"])]
            sdict = {**song, "systems": [{**sy, "lyrics": [clean[si][i] for i in bmap[si]]} for si, sy in enumerate(song["systems"])]}
        res = img_align.analyse(sdict, str(page), row=3 if row_b else 0) if page.exists() and not rule_only else {"systems": [], "errors": ["no page image"]}
        out = {"systems": [], "pitch": res.get("pitch")}; nbad = 0; nline = 0
        for si, sy in enumerate(song["systems"]):
            r = res["systems"][si] if si < len(res["systems"]) else None
            lines = []
            for li, line in enumerate(clean[si]):
                nline += 1
                lj = (bmap[si].index(li) if li in bmap[si] else -1) if row_b else li
                ok = r and r.get("lines") and 0 <= lj < len(r["lines"]) and r["lines"][lj]
                if ok:
                    slots = r["slots"]
                    items = [[slots[q][0], slots[q][1], t] for q, t, d in r["lines"][lj]]
                    lines.append({"label": labels[si][li], "approx": False, "items": items})
                else:
                    items, exact = rule_align(song["grid"], sy["start"], sy["end"], line, labels[si][li])
                    nbad += 0 if exact else 1
                    lines.append({"label": labels[si][li], "approx": not exact, "items": items})
            out["systems"].append({"lines": lines})
        json.dump(out, open(ROOT / "scans" / "align" / f"{num:03d}.json", "w"), ensure_ascii=False)
        print(f"hymn {num}: {nline - nbad}/{nline} lines aligned from image" + (f"  ({len(res['errors'])} issues)" if res["errors"] else ""))
        for e in res["errors"]: print("   ", e[:200])

if __name__ == "__main__": main()

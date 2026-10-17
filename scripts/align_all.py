"""Align lyrics to notes for every hymn that has a scan page (scans/pages/NNN.png), using image analysis
with a rule-based fallback. Needs app/data/songs/*.json (run build_all.py first).
Writes scans/align/NNN.json = {"systems":[{"lines":[{"label","approx","items":[[cell,slot,text],..]}]}]}"""
import sys, json, re, glob, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import img_align
from lyralign import syllables

def strip_label(line):
    m = re.match(r"^\(([^)]*)\)\s*(.*)$", line)
    return (m.group(1), m.group(2)) if m else ("", line)

def rule_align(S, a, b, line):
    syl = syllables(line); on = [(c, k) for c in range(a, b) for k, s in enumerate(S[c]) if isinstance(s[2], list)]
    return [[c, k, t if t else "-"] for (c, k), t in zip(on, syl)]

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
        res = img_align.analyse(sdict, str(page)) if page.exists() else {"systems": [], "errors": ["no page image"]}
        out = {"systems": [], "pitch": res.get("pitch")}; nbad = 0; nline = 0
        for si, sy in enumerate(song["systems"]):
            r = res["systems"][si] if si < len(res["systems"]) else None
            lines = []
            for li, line in enumerate(clean[si]):
                nline += 1
                ok = r and r.get("lines") and li < len(r["lines"]) and r["lines"][li]
                if ok:
                    slots = r["slots"]
                    items = [[slots[q][0], slots[q][1], t] for q, t, d in r["lines"][li]]
                    lines.append({"label": labels[si][li], "approx": False, "items": items})
                else:
                    nbad += 1
                    lines.append({"label": labels[si][li], "approx": True, "items": rule_align(S, sy["start"], sy["end"], line)})
            out["systems"].append({"lines": lines})
        json.dump(out, open(ROOT / "scans" / "align" / f"{num:03d}.json", "w"), ensure_ascii=False)
        print(f"hymn {num}: {nline - nbad}/{nline} lines aligned from image" + (f"  ({len(res['errors'])} issues)" if res["errors"] else ""))
        for e in res["errors"]: print("   ", e[:200])

if __name__ == "__main__": main()

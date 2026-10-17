#!/usr/bin/env python3
"""songs/*.drm (+ optional .json sidecar: bars, phrase_ends, lyrics) -> app/data/{index.json,songs/<id>.json}"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import drm

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data"; (OUT / "songs").mkdir(parents=True, exist_ok=True)
BREATH = 0.3          # beats of silence taken from the last note of a phrase (double bar)

def show(tok):
    """drm token -> [letters, octave] for display (d1 -> d + up 1, s-1 -> s + down 1)"""
    m = re.match(r"^([a-z]+)(-?\d+)?$", tok)
    if not m: return [tok, 0]
    return [m.group(1), int(m.group(2) or 0)]

def main():
    for f in (OUT / "songs").glob("*.json"): f.unlink()
    index = []
    for f in sorted((ROOT / "songs").glob("*.drm")):
        side = json.loads(f.with_suffix(".json").read_text(encoding="utf-8")) if f.with_suffix(".json").exists() else {}
        meta, names, notes, tempos, ins, order, voices = drm.build(f.read_text(encoding="utf-8"), full=True)
        n = len(order)
        sys_list = side.get("systems") or [{"start": i, "end": min(i + 8, n), "lyrics": [], "lead": True} for i in range(0, n, 8)]
        num0 = int(side["number"]) if side.get("number") else None
        af = ROOT / "scans" / "align" / (f"{num0:03d}.json" if num0 else "x.json")
        if af.exists():
            al = json.loads(af.read_text(encoding="utf-8"))["systems"]
            for s, a in zip(sys_list, al): s["lyr"] = a["lines"]
        # phrase ends = double bars + end of every printed line (a breath where the singers take air)
        pe = sorted(set(side.get("phrase_ends", [])) | {s["end"] for s in sys_list})
        bars = side.get("bars") or list(range(0, n, int(meta.get("P_SIGNATURE", 4))))
        # ---- events (beats); take a short breath off the last note before each phrase end
        ev = []
        for s, d, p, vl, vi in notes:
            b0, b1 = s / drm.PPQ, (s + d + drm.GAP) / drm.PPQ
            if any(abs(b1 - e) < 1e-6 and b0 < e - 1e-6 for e in pe): b1 = max(b0 + 0.25, b1 - min(BREATH, (b1 - b0) * 0.5))
            ev.append([round(b0, 4), round(b1 - b0 - 0.02, 4), p, vl, vi])
        ev.sort()
        grid = []
        for vi, cells in enumerate(voices):
            grid.append([[[round(o, 4), round(d, 4), "-" if t == "-" else (show(t) if t else "")] for o, d, t in drm.cell_slots(cells[c] if c < len(cells) else "")]
                         for c in range(n)])
        sid = re.sub(r"[^a-z0-9]+", "-", f.stem.lower()).strip("-")
        num = int(side["number"]) if side.get("number") else None
        song = {"id": sid, "number": num, "title": side.get("title") or meta.get("P_TITLE", f.stem), "source": side.get("source") or "",
                "mood": side.get("mood") or "", "key": drm.KEYS[int(meta.get("P_KEY", 0))], "meter": int(meta.get("P_SIGNATURE", 4)),
                "tempo": int(meta.get("P_TEMPO", 100)), "voices": names, "cells": n, "grid": grid, "events": ev,
                "tempos": [[round(t / drm.PPQ, 4), b] for t, b in tempos], "bars": bars, "phrase_ends": pe,
                "systems": sys_list, "verses": side.get("verses") or [], "hasScan": (OUT / "scans" / f"{num}.jpg").exists() if num else False}
        (OUT / "songs" / f"{sid}.json").write_text(json.dumps(song, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index.append({"id": sid, "number": num, "title": song["title"], "key": song["key"], "tempo": song["tempo"], "source": song["source"], "meter": song["meter"]})
    index.sort(key=lambda x: (x["number"] is None, x["number"] or 0, x["title"]))
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(index), "songs ->", OUT)

if __name__ == "__main__": main()

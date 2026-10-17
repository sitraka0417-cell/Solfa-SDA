#!/usr/bin/env python3
"""Printed tonic sol-fa transcription (S/A/T/B rows, | and ‖ bars) -> validated .drm.
Validation: every voice must have the same number of beats in every bar, in every system."""
import re, sys, pathlib
KEYS = ["C","Db","D","Eb","E","F","F#","G","Ab","A","Bb","B"]
ALIAS = {"C#": "Db"}

def norm_cell(c):
    """printed -> drm token: d' -> d1, s, -> s-1, r'' -> r2 ; ',' after a note = low octave mark"""
    if c.strip() == "_": return ""          # explicit empty (rest) cell
    def note(m):
        base, marks = m.group(1), m.group(2)
        up, dn = marks.count("'"), marks.count(",")
        o = up - dn
        return base + (str(o) if o else "")
    # a ',' directly after a note and NOT followed by another note is an octave mark
    c = re.sub(r"([a-z]+)((?:'|,(?![a-z]))+)", note, c)
    return c.replace("’", "'")

def parse_row(row):
    """-> (bars, phrase_ends): bars=list of cell lists; phrase_ends=cell counts (within row) where a double bar sits"""
    lead = row.lstrip().startswith("|")
    row = row.replace("\u2016", "|\u2016|").replace("||", "|\u2016|")
    bars, ends, n = [], [], 0
    for part in row.split("|"):
        if part.strip() == "\u2016": ends.append(n); continue
        if part.strip() == "" and ":" not in part: continue
        cells = [norm_cell(x.strip()) for x in part.split(":")]
        bars.append(cells); n += len(cells)
    return bars, ends, lead

def convert(path):
    meta, systems, cur = {}, [], None
    for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"): continue
        if ln.strip() == "system": cur = {"lyrics": []}; systems.append(cur); continue
        m = re.match(r"^([SATB]):\s?(.*)$", ln)
        if m: cur[m.group(1)] = m.group(2); continue
        k, v = ln.split(":", 1)
        if k.strip() == "verse": meta.setdefault("verses", []).append(v.strip().replace(" / ", "\n"))
        elif k.strip() == "lyric" and cur is not None: cur["lyrics"].append(v.strip())
        else: (cur if cur is not None else meta)[k.strip()] = v.strip()
    errors, voices = [], {v: [] for v in "SATB"}
    side = {"bars": [], "phrase_ends": [], "systems": []}      # cell indexes, global
    off = 0
    for si, s in enumerate(systems, 1):
        rows = {v: parse_row(s[v]) for v in "SATB"}
        nb = {v: len(rows[v][0]) for v in rows}
        lead = rows["S"][2]
        if len(set(nb.values())) != 1: errors.append(f"system {si}: bar count differs {nb}")
        for bi in range(min(nb.values())):
            lens = {v: len(rows[v][0][bi]) for v in rows}
            if len(set(lens.values())) != 1: errors.append(f"system {si} bar {bi+1}: beats differ {lens}")
        if len({tuple(rows[v][1]) for v in rows}) != 1: errors.append(f"system {si}: double bars not aligned")
        n = 0
        for bar in rows["S"][0]: side["bars"].append(off + n); n += len(bar)
        side["phrase_ends"] += [off + e for e in rows["S"][1]]
        if not rows["S"][1] or rows["S"][1][-1] != n: side["phrase_ends"].append(off + n)
        side["systems"].append({"start": off, "end": off + n, "lyrics": s["lyrics"], "lead": lead})
        for v in "SATB": voices[v] += [c for bar in rows[v][0] for c in bar]
        off += n
    side["phrase_ends"] = sorted(set(side["phrase_ends"]))
    return meta, voices, errors, side

def write(txt, outdir):
    """validate one transcription; write <outdir>/<stem>.drm + .json. Returns list of errors."""
    meta, voices, errors, side = convert(txt)
    if errors: return errors
    import json
    out = pathlib.Path(outdir) / (pathlib.Path(txt).stem + ".drm"); out.write_text(to_drm(meta, voices), encoding="utf-8")
    json.dump({**side, **{k: meta.get(k) for k in ("number","title","key","meter","source","tempo","mood","verses")}}, open(out.with_suffix(".json"), "w"), ensure_ascii=False)
    return []

def to_drm(meta, voices):
    key = KEYS.index(ALIAS.get(meta["key"], meta["key"])); sig = meta["meter"].split("/")[0]
    head = (f"VERSION:1; P_SWING:0; CHANGES:; INSTR:0, 0, 0, 0; VOICES:S,A,T,B; P_TITLE:{meta['title']}; "
            f"P_AUT:; P_COMP:; P_DATE:; P_SINGER:{meta.get('source','')}; P_KEY:{key}; P_SIGNATURE:{sig}; "
            f"P_TEMPO:{meta.get('tempo',100)}; ")
    return head + "__!!__" + "__!!__".join(":".join(voices[v]) for v in "SATB") + "__!!__"

if __name__ == "__main__":
    meta, voices, errors, side = convert(sys.argv[1])
    for e in errors: print("ERROR", e)
    n = {v: len(voices[v]) for v in voices}; print("beats per voice:", n)
    if len(sys.argv) > 2 and not errors:
        out = pathlib.Path(sys.argv[2]); out.write_text(to_drm(meta, voices), encoding="utf-8")
        import json; json.dump({**side, **{k: meta.get(k) for k in ("number","title","key","meter","source","tempo","mood","verses")}}, open(out.with_suffix(".json"), "w"), ensure_ascii=False)
        print("wrote", out)

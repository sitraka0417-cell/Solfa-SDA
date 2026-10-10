#!/usr/bin/env python3
"""Printed tonic sol-fa transcription (S/A/T/B rows, | and ‖ bars) -> validated .drm.
Validation: every voice must have the same number of beats in every bar, in every system."""
import re, sys, pathlib
KEYS = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]

def norm_cell(c):
    """printed -> drm token: d' -> d1, s, -> s-1, r'' -> r2 ; ',' after a note = low octave mark"""
    def note(m):
        base, marks = m.group(1), m.group(2)
        up, dn = marks.count("'"), marks.count(",")
        o = up - dn
        return base + (str(o) if o else "")
    # a ',' directly after a note and NOT followed by another note is an octave mark
    c = re.sub(r"([a-z]+)((?:'|,(?![a-z]))+)", note, c)
    return c.replace("’", "'")

def parse_row(row):
    row = row.replace("‖", "|")
    bars = [b for b in row.split("|")]
    if bars and bars[-1].strip() == "": bars.pop()
    return [[norm_cell(x.strip()) for x in b.split(":")] for b in bars if b.strip() != "" or ":" in b]

def convert(path):
    meta, systems, cur = {}, [], None
    for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"): continue
        if ln.strip() == "system": cur = {}; systems.append(cur); continue
        k, v = ln.split(":", 1) if not re.match(r"^[SATB]:", ln) else (ln[0], ln[2:])
        (cur if cur is not None else meta)[k.strip()] = v.strip() if k.strip() not in "SATB" or len(k.strip())>1 else v
    errors, voices = [], {v: [] for v in "SATB"}
    for si, s in enumerate(systems, 1):
        rows = {v: parse_row(s[v]) for v in "SATB"}
        nb = {v: len(rows[v]) for v in rows}
        if len(set(nb.values())) != 1: errors.append(f"system {si}: bar count differs {nb}")
        for bi in range(min(nb.values())):
            lens = {v: len(rows[v][bi]) for v in rows}
            if len(set(lens.values())) != 1: errors.append(f"system {si} bar {bi+1}: beats differ {lens}")
        for v in "SATB": voices[v] += [c for bar in rows[v] for c in bar]
    return meta, voices, errors

def to_drm(meta, voices):
    key = KEYS.index(meta["key"]); sig = meta["meter"].split("/")[0]
    head = (f"VERSION:1; P_SWING:0; CHANGES:; INSTR:0, 0, 0, 0; VOICES:S,A,T,B; P_TITLE:{meta['title']}; "
            f"P_AUT:; P_COMP:; P_DATE:; P_SINGER:{meta.get('source','')}; P_KEY:{key}; P_SIGNATURE:{sig}; "
            f"P_TEMPO:{meta.get('tempo',100)}; ")
    return head + "__!!__" + "__!!__".join(":".join(voices[v]) for v in "SATB") + "__!!__"

if __name__ == "__main__":
    meta, voices, errors = convert(sys.argv[1])
    for e in errors: print("ERROR", e)
    n = {v: len(voices[v]) for v in voices}; print("beats per voice:", n)
    if len(sys.argv) > 2 and not errors:
        pathlib.Path(sys.argv[2]).write_text(to_drm(meta, voices), encoding="utf-8"); print("wrote", sys.argv[2])

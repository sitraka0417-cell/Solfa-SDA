import re
def syllables(line):
    """-> list of tokens; '' = filler (lone '-')."""
    out=[]
    for w in line.split():
        if w=="-": out.append(""); continue
        for m in re.findall(r"[^-]+-?|-", w):
            out.append("" if m=="-" else m)
    return out
def onsets(grid_v, a, b):
    r=[]
    for c in range(a,b):
        for k,s in enumerate(grid_v[c]):
            if isinstance(s[2],list): r.append((c,k))
    return r
def align(grid_v, a, b, line):
    """returns (items,[cell,slot,text]..., diff). diff=len(syl)-len(onsets)"""
    syl=syllables(line); on=onsets(grid_v,a,b)
    items=[[c,k,t] for (c,k),t in zip(on,syl)]
    return items, len(syl)-len(on)

def syl2(line):
    """-> [(display, nchars)] ; a lone '-' is only the printed hyphen of the previous syllable (it sits under a held beat)
    and never a syllable of its own."""
    out = []
    for w in line.split():
        if w == "~": out.append(("", 0)); continue          # a note that carries no syllable
        if w == "-":
            if out: d, n = out[-1]; out[-1] = (d if d.endswith("-") else d + "-", n + 1)
            else: out.append(("-", 1))
            continue
        pieces = []
        for part in w.split("·"):                      # '·' = invisible syllable break (two notes, no printed hyphen)
            pieces += re.findall(r"[^-]+-?|-", part)
        for m in pieces:
            if m == "-":
                if out: d, n = out[-1]; out[-1] = (d if d.endswith("-") else d + "-", n + 1)
                else: out.append(("-", 1))
            else: out.append((m, len(m)))
    return out

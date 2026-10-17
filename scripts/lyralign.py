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

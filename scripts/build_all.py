#!/usr/bin/env python3
"""scans/*.txt (validated transcriptions) -> songs/*.drm(+json) -> app/data/*.  Exit 1 if any transcription fails validation."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import scan2drm, build_data

ROOT = pathlib.Path(__file__).resolve().parent.parent
def main():
    out = ROOT / "songs"; out.mkdir(exist_ok=True)
    for f in out.glob("*"): f.unlink()
    bad = 0
    for txt in sorted((ROOT / "scans").glob("*.txt")):
        errs = scan2drm.write(txt, out)
        print(("FAIL " if errs else "ok   ") + txt.name)
        for e in errs: print("     ", e)
        bad += bool(errs)
    build_data.main()
    import align_all; align_all.main(); build_data.main()
    sys.exit(1 if bad else 0)
if __name__ == "__main__": main()

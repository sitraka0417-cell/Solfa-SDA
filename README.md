# Solfa SDA
Malagasy Adventist hymns in tonic sol-fa: read, hear, transpose, change tempo, play one voice only.

    scans/NNN_*.txt   transcription of a scan (4 voices + lyrics)
    scans/pages/NNN.png   the scan (used to align each syllable under its note)
    scripts/build_all.py  validate (all 4 voices must have the same beats per bar) -> songs/*.drm
                          -> lyric alignment (scans/align/NNN.json) -> app/data/*.json
    app/                  web app / PWA (no horizontal scroll: bars wrap)
    .github/workflows/    android.yml (APK), pages.yml (web), render-solfa.yml (MP3)

Local: `pip install numpy scipy pillow && python3 scripts/build_all.py && cd app && python3 -m http.server`
Lyric alignment: `scripts/img_align.py` reads the monospaced print; lines it cannot align fall back to a
note-order rule and are marked `approx` in `scans/align/*.json` (hymn 8 and a part of hymn 10 now).

# solfa-ci
Tonic sol-fa (`.drm`, DoReMi format) → MIDI → MP3, automatically in GitHub Actions.

    songs/*.drm  --scripts/drm.py-->  out/*.mid  --fluidsynth(.sf2)-->  out/*.mp3

Local test: `python3 scripts/drm.py "songs/Joy to the world.drm" out --wav` (WAV = crude built-in preview).
Push a `.drm` into `songs/` and the workflow `render-solfa.yml` publishes the audio as a build artifact.

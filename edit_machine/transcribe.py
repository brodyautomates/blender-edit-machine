# Word timings for the voiceover: <project>/vo.wav -> <project>/timing.json ([{"w", "t0", "t1"}, ...]).
#   pip install faster-whisper
#   python3 edit_machine/transcribe.py projects/example
# Every shot in spec.py is cued to a word, so the edit lands exactly on what you say.
import sys, json, pathlib, subprocess
p = pathlib.Path(sys.argv[1])
try:
    from faster_whisper import WhisperModel
except ImportError:
    sys.exit("pip install faster-whisper   (then run this again)")
model = WhisperModel("small.en", compute_type="int8")
import numpy as np  # decode with ffmpeg (16 kHz mono float), so no audio-library version can break this
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p / "vo.wav"), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, vad_filter=True)
words = [{"w": w.word.strip(), "t0": round(w.start, 3), "t1": round(w.end, 3)} for s in segs for w in s.words]
(p / "timing.json").write_text(json.dumps(words, indent=1))
print(f"{len(words)} words, {words[-1]['t1']:.1f} s -> {p / 'timing.json'}")

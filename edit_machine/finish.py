# Frames + voiceover + captions -> <project>/out.mp4 (or out_preview.mp4), loudness -14 LUFS. ffmpeg only.
#   python3 edit_machine/finish.py projects/example [--preview]
# Captions: one short phrase at a time, white, low in the frame, the word being said at full white and the rest dimmed.
import sys, json, subprocess, pathlib
p = pathlib.Path(sys.argv[1]).resolve(); preview = "--preview" in sys.argv
words = json.load(open(p / "timing.json")); total = round(words[-1]["t1"] * 24) + 14
W, H = (540, 960) if preview else (1080, 1920)

def ts(t):
    h, m = int(t // 3600), int(t % 3600 // 60); return f"{h}:{m:02d}:{t % 60:05.2f}"

# phrases of up to 4 words, broken at punctuation
phrases, cur = [], []
for w in words:
    cur.append(w)
    if len(cur) == 4 or w["w"][-1:] in ".,?!": phrases.append(cur); cur = []
if cur: phrases.append(cur)
size = round(H * 0.026)
ass = [f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\n\n[V4+ Styles]\n"
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
       f"Style: Cap,Helvetica Neue,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,2,2,40,40,{round(H * 0.235)},1\n\n"
       "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"]
for k, ph in enumerate(phrases):
    end = phrases[k + 1][0]["t0"] if k + 1 < len(phrases) else ph[-1]["t1"] + 0.4
    for j, w in enumerate(ph):
        t_end = ph[j + 1]["t0"] if j + 1 < len(ph) else end
        text = " ".join(("{\\alpha&H00&}" if i <= j else "{\\alpha&H90&}") + x["w"] for i, x in enumerate(ph))
        ass.append(f"Dialogue: 0,{ts(w['t0'])},{ts(t_end)},Cap,,0,0,0,,{text}\n")
(p / "captions.ass").write_text("".join(ass))
frames = p / ("frames_preview" if preview else "frames")
out = p / ("out_preview.mp4" if preview else "out.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "24", "-i", str(frames / "f_%04d.png"), "-i", str(p / "vo.wav"),
                "-vf", f"scale={W}:{H},subtitles={p / 'captions.ass'},format=yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
print(f"done -> {out}")

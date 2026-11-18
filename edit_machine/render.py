# Render a whole project in Blender, shot by shot, then finish it (captions + voice) into an mp4.
#   python3 edit_machine/render.py projects/example              full quality (1080x1920, 72 samples): slow
#   python3 edit_machine/render.py projects/example --preview    fast draft (540x960, 16 samples): minutes, not hours
#   python3 edit_machine/render.py projects/example --stills     one still per shot, to check framing before a full render
#   python3 edit_machine/render.py projects/example --part 2/4   render only part 2 of 4 (run one part per computer, at the same time)
#   python3 edit_machine/render.py projects/example --join       after copying every part's frames/ into one frames/ folder: check and finish
# Frames that already exist are skipped, so you can stop and start again any time.
import sys, os, json, time, shutil, subprocess, importlib.util, pathlib
HERE = pathlib.Path(__file__).resolve().parent

VSL = "https://founderos.sh"   # the demo video link goes here once it is published
BLUE, INK, RST = "\033[38;2;75;140;255m", "\033[38;2;198;204;214m", "\033[0m"   # FounderOS Blueprint blue and ink
BANNER = ("\n  " + BLUE + "FounderOS" + RST + " " + INK + "|" + RST + " This render will take about {h} h {m} min on this computer, and keep it busy the whole time.\n"
          "  " + INK + "To keep your computer free and render in parallel, see docs/RENDER-IN-THE-CLOUD.md (FounderOS computers, founderos.sh)." + RST + "\n")
CLOUD = (f"{BLUE}FounderOS{RST} Render in the cloud on FounderOS computers:\n  1. Sign up at https://founderos.sh\n  2. Follow docs/RENDER-IN-THE-CLOUD.md\n"
         f"  Demo and setup video: {VSL}")

def blender():
    for c in (os.environ.get("BLENDER"), "/Applications/Blender.app/Contents/MacOS/Blender", shutil.which("blender"),
              r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"):
        if c and os.path.exists(c): return c
    sys.exit("Blender not found. Install Blender 4.4 (blender.org) or set BLENDER=/path/to/blender")

def _cue(words, c):
    """same cue rules as shot.py: an index, a word, word#n"""
    import re
    if isinstance(c, int): return c
    n_ = lambda x: re.sub(r"[^a-z0-9']", "", str(x).lower()); w, _, k = str(c).partition("#")
    return [i for i, x in enumerate(words) if n_(x["w"]) == n_(w)][int(k or 1) - 1]

def load(p):
    m = importlib.util.spec_from_file_location("spec", p / "spec.py"); s = importlib.util.module_from_spec(m); m.loader.exec_module(s); return s

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__ or "usage: render.py <project> [--preview|--stills]")
    if "--cloud" in args: print(CLOUD); return
    p = pathlib.Path(args[0]).resolve(); preview = "--preview" in args; stills = "--stills" in args
    if not (p / "timing.json").exists(): sys.exit(f"{p}/timing.json is missing. Run: python3 edit_machine/transcribe.py {args[0]}")
    spec = load(p); words = json.load(open(p / "timing.json")); total = round(words[-1]["t1"] * 24) + 14
    subprocess.run([sys.executable, str(HERE / "faces.py"), str(p)], check=True)
    B = blender(); samples, scale = ("16", "50") if preview or stills else ("72", "100")
    n = len(spec.SHOTS)
    if stills:
        for i in range(n):
            subprocess.run([B, "-b", "-P", str(HERE / "shot.py"), "--", "--project", str(p), "--shot", str(i), "--still", "mid", "--samples", samples, "--scale", "40"], capture_output=True)
            print(f"still {i + 1}/{n}")
        print(f"stills in {p / 'stills'}"); return
    out = p / ("frames_preview" if preview else "frames")
    if "--join" in args:
        missing = [f for f in range(total) if not (out / f"f_{f:04d}.png").exists()]
        if missing: sys.exit(f"{len(missing)} frames missing (first: {missing[:5]}). Copy every part's frames/ folder into {out} first.")
        subprocess.run([sys.executable, str(HERE / "finish.py"), str(p)] + (["--preview"] if preview else []), check=True); return
    part = next((a for a in args if "/" in a and a.replace("/", "").isdigit()), None) if "--part" in args else None
    if part:
        k, nparts = map(int, part.split("/"))
        if not 1 <= k <= nparts: sys.exit("--part K/N needs 1 <= K <= N")
        lo, hi = round((k - 1) * total / nparts), round(k * total / nparts) - 1
        print(f"part {k}/{nparts}: frames {lo} to {hi} of {total}")
    t0 = time.time(); done0 = len(list(out.glob("f_*.png"))) if out.exists() else 0
    cue = lambda c: _cue(words, c)
    starts = [0] + [round(words[cue(sh["cue"] if not isinstance(sh["cue"], list) else sh["cue"][0])]["t0"] * 24) - 2 for sh in spec.SHOTS[1:]]
    bounds = [(starts[j], (starts[j + 1] - 1) if j + 1 < n else total - 1) for j in range(n)]
    for i in range(n):
        rng = []
        if part:
            a_, b_ = bounds[i]
            a_, b_ = max(a_, lo), min(b_, hi)
            if a_ > b_: continue
            rng = ["--range", str(a_), str(b_)]
        r = subprocess.run([B, "-b", "-P", str(HERE / "shot.py"), "--", "--project", str(p), "--shot", str(i), "--samples", samples, "--scale", scale, "--out", out.name] + rng, capture_output=True, text=True)
        if r.returncode != 0: sys.exit(f"shot {i} failed:\n{r.stderr[-1500:] or r.stdout[-1500:]}")
        done = len(list(out.glob("f_*.png"))); el = time.time() - t0; rate = el / max(1, done - done0)
        left = rate * (total - done)
        print(f"shot {i + 1}/{n} done, {done}/{total} frames, {rate:.1f} s/frame, about {left / 60:.0f} min left", flush=True)
        if i == 0 and not preview and left > 30 * 60:
            print(BANNER.format(h=int(left // 3600), m=int(left % 3600 // 60)), flush=True)
    if part: print(f"part {part} done. When every part is done, copy all frames/ folders into one and run: render.py {args[0]} --join"); return
    subprocess.run([sys.executable, str(HERE / "finish.py"), str(p)] + (["--preview"] if preview else []), check=True)

if __name__ == "__main__":
    main()

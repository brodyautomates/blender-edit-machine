# Renders a project's faces (the FACES in its spec.py) to <project>/ui/*.png through headless Chrome.
#   python3 edit_machine/faces.py projects/example [name ...]
# Typing faces ("typing" entries) become a sequence numbered by edit frame: ui/<name>_seq/f_####.png
import sys, os, json, pathlib, subprocess, importlib.util, hashlib, shutil
from concurrent.futures import ThreadPoolExecutor
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import facekit as fk
CHROME = os.environ.get("CHROME") or next((c for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome") or "",
          shutil.which("chromium") or "", r"C:\Program Files\Google\Chrome\Application\chrome.exe") if c and os.path.exists(c)), "google-chrome")

def load(p):
    sp = importlib.util.spec_from_file_location("spec", pathlib.Path(p) / "spec.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def shoot(out, w, h, body, clear):
    tmp = out.with_suffix(".html")
    bg = "transparent" if clear else "#0d0f14"
    tmp.write_text(f"<html><head><meta charset='utf-8'><style>{fk.CSS} body{{width:{w}px;height:{h}px;background:{bg};overflow:hidden}}</style></head><body>{body}</body></html>")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", "--default-background-color=00000000",
                    f"--window-size={w},{h}", f"--screenshot={out}", tmp.as_uri()], capture_output=True, timeout=90)
    tmp.unlink(missing_ok=True)
    if not out.exists() or out.stat().st_size < 500: raise RuntimeError(f"face failed: {out}")
    return out

def cue(words, c):
    """a word index, a word ("agents") or its n-th time ("agents#2")"""
    import re
    if isinstance(c, int): return c
    n_ = lambda s: re.sub(r"[^a-z0-9']", "", str(s).lower()); w, _, k = str(c).partition("#")
    return [i for i, x in enumerate(words) if n_(x["w"]) == n_(w)][int(k or 1) - 1]

def typing_frames(v, name, d, words):
    """d: {text, placeholder, type (cue), send (cue), w, h}. One PNG per typed prefix, linked per edit frame."""
    at = lambda c: round(words[cue(words, c[0])]["t0"] * 24) + c[1] if isinstance(c, list) else round(words[cue(words, c)]["t0"] * 24)
    t0, send = at(d["type"]), at(d["send"])
    w, h = d.get("w", 1720), d.get("h", 200)
    cache = pathlib.Path(v) / "ui" / f"{name}_k"; cache.mkdir(parents=True, exist_ok=True)
    def bar(txt, caret, ph):
        t = fk.esc(txt) if txt else f'<span style="color:#6c7584">{fk.esc(ph)}</span>'
        c = '<span style="display:inline-block;width:5px;height:64px;background:#ecf2fa;margin-left:6px;vertical-align:-10px"></span>' if caret else ""
        return f'<div class="glass" style="--r:{h / 2}px"></div><div class="ab t" style="left:90px;top:{h / 2 - 46}px;font-size:76px;white-space:nowrap">{t}{c}</div>'
    text = d["text"]; n = len(text)
    jobs = []
    for k in range(n + 1):
        for caret in (0, 1):
            jobs.append((cache / f"k{k:03d}_{caret}.png", bar(text[:k], caret, "")))
    jobs.append((cache / "ph_1.png", bar("", 1, d.get("placeholder", "Ask AI…")))); jobs.append((cache / "ph_0.png", bar("", 0, d.get("placeholder", "Ask AI…"))))
    with ThreadPoolExecutor(6) as ex: list(ex.map(lambda j: j[0].exists() or shoot(j[0], w, h, j[1], True), jobs))
    shutil.copyfile(cache / "ph_0.png", pathlib.Path(v) / "ui" / f"{name}.png")  # the still face (Blender reads its aspect)
    seq = pathlib.Path(v) / "ui" / f"{name}_seq"; shutil.rmtree(seq, ignore_errors=True); seq.mkdir()
    total = round(words[-1]["t1"] * 24) + 30
    cps = d.get("cps", 14)  # characters per second
    for f in range(0, total):
        caret = 1 if (f // 12) % 2 == 0 else 0
        if f < t0 or f >= send + 2: src = cache / f"ph_{caret}.png"
        else:
            k = min(n, int((f - t0) * cps / 24) + 1)
            src = cache / f"k{k:03d}_{caret}.png"
        os.link(src, seq / f"f_{f:04d}.png")  # file number = edit frame (shot.py: frame_start 1, offset 0)
    return seq

def lines_frames(v, name, d, words):
    """a terminal whose lines appear on their cues: one PNG per line count, hardlinked per edit frame"""
    at = lambda c: round(words[cue(words, c[0])]["t0"] * 24) + c[1] if isinstance(c, list) else round(words[cue(words, c)]["t0"] * 24)
    cache = pathlib.Path(v) / "ui" / f"{name}_k"; cache.mkdir(parents=True, exist_ok=True)
    L = d["lines"]; cols = d.get("colors", ["#ecf2fa"] * len(L))
    def page(k):
        body = "".join(f'<div class="ab mono" style="left:80px;top:{260 + i * 110}px;font-size:54px;color:{cols[i]}">{fk.esc(L[i])}</div>' for i in range(k))
        caret_y = 260 + k * 110
        body += f'<div class="ab" style="left:80px;top:{caret_y + 8}px;width:28px;height:56px;background:#ecf2fa;opacity:.85"></div>'
        return fk.screen(d.get("title", "Terminal"), d.get("sub", ""), body)
    for k in range(len(L) + 1):
        p = cache / f"n{k}.png"
        if not p.exists(): w, h, html, clear = page(k); shoot(p, w, h, html, clear)
    shutil.copyfile(cache / "n0.png", pathlib.Path(v) / "ui" / f"{name}.png")
    seq = pathlib.Path(v) / "ui" / f"{name}_seq"; shutil.rmtree(seq, ignore_errors=True); seq.mkdir()
    ts = [at(c) for c in d["at"]]; total = round(words[-1]["t1"] * 24) + 30
    for f in range(total):
        k = sum(1 for t in ts if f >= t)
        os.link(cache / f"n{k}.png", seq / f"f_{f:04d}.png")
    return seq

if __name__ == "__main__":
    v = str(pathlib.Path(sys.argv[1]).resolve()); only = set(sys.argv[2:])
    spec = load(v)
    words = json.load(open(pathlib.Path(v) / "timing.json"))
    out = pathlib.Path(v) / "ui"; out.mkdir(parents=True, exist_ok=True)
    todo = []
    for name, f in spec.FACES.items():
        if only and name not in only: continue
        if isinstance(f, tuple) and f[0] == "typing": typing_frames(v, name, f[1], words); print("typing", name); continue
        if isinstance(f, tuple) and f[0] == "file": shutil.copyfile(f[1], out / f"{name}.png"); print("file", name); continue
        if isinstance(f, tuple) and f[0] == "lines": lines_frames(v, name, f[1], words); print("lines", name); continue
        w, h, html, clear = f
        todo.append((out / f"{name}.png", w, h, html, clear))
    with ThreadPoolExecutor(6) as ex:
        for p in ex.map(lambda t: shoot(*t), todo): print(p.name)

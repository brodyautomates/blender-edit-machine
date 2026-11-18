# Screen content ("faces") for the Blender videos: small HTML builders in one visual language (the approved demo's
# screenA look). Pure Python, no dependencies, so both the face renderer and Blender can import a spec.
# A face is (w, h, html, clear): clear=True renders on a transparent ground (glass cards), else on the screen ground.

BLUE, WHITE, VIOLET, GREEN, ORANGE, RED, MUTED = "#9fc6ff", "#e8ecf4", "#a99bff", "#4fc16f", "#d97757", "#ff6b6b", "#8a93a3"
CSS = """*{margin:0;box-sizing:border-box}
body{font-family:'SF Pro Display',system-ui,-apple-system,sans-serif;color:#ecf2fa;-webkit-font-smoothing:antialiased;position:relative}
.ground{position:absolute;inset:0;background:radial-gradient(120% 90% at 30% 0%,#1d2230 0%,#0d0f14 60%)}
.glass{position:absolute;inset:0;border-radius:var(--r,60px);background:rgba(18,20,26,0.58);box-shadow:inset 0 0 0 4px rgba(236,242,250,0.08)}
.t{font-weight:600;letter-spacing:-0.5px}
.m{color:#8a93a3;font-weight:500}
.mono{font-family:'SF Mono',Menlo,monospace}
.dot{display:inline-block;border-radius:99px}
.row{position:absolute;left:70px;right:70px;border-radius:30px;background:rgba(255,255,255,0.03);box-shadow:inset 0 0 0 3px rgba(236,242,250,0.07)}
.ab{position:absolute}
"""

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def dot(c, s=34):
    return f'<span class="dot" style="width:{s}px;height:{s}px;background:{c};box-shadow:0 0 {s}px {c}"></span>'

# ---------- screens (opaque ground, 1600 wide) ----------
def screen(title, sub="", body="", w=1600, h=1100, stamp=""):
    st = f'<div class="ab mono" style="right:70px;top:84px;font-size:30px;color:{BLUE}">{esc(stamp)}</div>' if stamp else ""
    sb = f'<div class="ab m" style="left:72px;top:150px;font-size:34px">{esc(sub)}</div>' if sub else ""
    return (w, h, f'<div class="ground"></div><div class="ab t" style="left:70px;top:66px;font-size:64px">{esc(title)}</div>{sb}{st}{body}', False)

def rows(items, top=260, gap=150, hgt=124, size=48):
    """items: (color, label, right_text) rows, like a dashboard list."""
    out = ""
    for i, (c, label, right) in enumerate(items):
        y = top + i * gap
        out += f'<div class="row" style="top:{y}px;height:{hgt}px"></div>'
        out += f'<div class="ab" style="left:110px;top:{y + hgt / 2 - 17}px">{dot(c)}</div>'
        out += f'<div class="ab t" style="left:170px;top:{y + hgt / 2 - size * 0.62}px;font-size:{size}px">{esc(label)}</div>'
        if right: out += f'<div class="ab mono m" style="right:110px;top:{y + hgt / 2 - 20}px;font-size:34px">{esc(right)}</div>'
    return out

def textblock(lines, top=250, size=50, lh=1.45, color="#dfe6f0", mono=False, left=72, hl=None):
    """A page of text. hl: {line_index: color} to tint whole lines."""
    hl = hl or {}
    cls = "mono" if mono else ""
    out = ""
    for i, ln in enumerate(lines):
        c = hl.get(i, color)
        out += f'<div class="ab {cls}" style="left:{left}px;right:70px;top:{top + i * size * lh}px;font-size:{size}px;font-weight:500;color:{c};white-space:nowrap">{esc(ln)}</div>'
    return out

def bigstat(value, label, color=WHITE, top=330, size=300):
    return (f'<div class="ab t" style="left:0;right:0;text-align:center;top:{top}px;font-size:{size}px;letter-spacing:-8px;color:{color};text-shadow:0 0 60px {color}55">{esc(value)}</div>'
            f'<div class="ab m" style="left:0;right:0;text-align:center;top:{top + size * 1.08}px;font-size:56px">{esc(label)}</div>')

def bars(vals, colors, top=300, left=120, right=120, bottom=120, h=1100, gap=30):
    n = len(vals); out = ""
    for i, (v, c) in enumerate(zip(vals, colors)):
        x = f"calc({left}px + (100% - {left + right}px) * {i / n} + {gap / 2}px)"
        wdt = f"calc((100% - {left + right}px) / {n} - {gap}px)"
        hh = (h - top - bottom) * v
        out += f'<div class="ab" style="left:{x};width:{wdt};bottom:{bottom}px;height:{hh}px;border-radius:24px;background:{c};box-shadow:0 0 40px {c}66"></div>'
    return out

# ---------- glass cards (transparent ground) ----------
def card(label, sub="", color=BLUE, w=900, h=300, size=72, icon=None):
    ic = dot(color, 40) if icon is None else icon
    sb = f'<div class="ab m" style="left:150px;top:{h / 2 + 12}px;font-size:{size * 0.5}px">{esc(sub)}</div>' if sub else ""
    ty = h / 2 - size * 0.62 - (size * 0.32 if sub else 0)
    return (w, h, f'<div class="glass" style="--r:{min(h, 300) * 0.32}px"></div><div class="ab" style="left:70px;top:{h / 2 - 20 - (size * 0.32 if sub else 0)}px">{ic}</div>'
                  f'<div class="ab t" style="left:150px;top:{ty}px;font-size:{size}px">{esc(label)}</div>{sb}', True)

def chip(text, color=BLUE, w=760, h=170, size=64):
    return (w, h, f'<div class="glass" style="--r:{h / 2}px"></div><div class="ab" style="left:60px;top:{h / 2 - 17}px">{dot(color)}</div>'
                  f'<div class="ab t" style="left:122px;right:40px;top:{h / 2 - size * 0.62}px;font-size:{size}px;white-space:nowrap">{esc(text)}</div>', True)

def pill(text, color=ORANGE, w=1100, h=220, size=84):
    """The CTA pill: centred text, accent ring."""
    return (w, h, f'<div class="glass" style="--r:{h / 2}px;box-shadow:inset 0 0 0 5px {color}88"></div>'
                  f'<div class="ab t" style="left:0;right:0;text-align:center;top:{h / 2 - size * 0.62}px;font-size:{size}px">{text}</div>', True)

def panel(title, body="", w=1200, h=800, sub=""):
    """A glass panel with its own title, for floating widgets."""
    sb = f'<div class="ab m" style="left:64px;top:132px;font-size:36px">{esc(sub)}</div>' if sub else ""
    return (w, h, f'<div class="glass" style="--r:56px"></div><div class="ab t" style="left:64px;top:56px;font-size:58px">{esc(title)}</div>{sb}{body}', True)

def phone(app, title, body, buttons=(), w=900, h=1800):
    """A phone notification screen (opaque ground)."""
    bt = ""
    for i, (txt, c) in enumerate(buttons):
        bt += (f'<div class="ab" style="left:{80 + i * 380}px;bottom:150px;width:350px;height:130px;border-radius:65px;background:{c}22;box-shadow:inset 0 0 0 4px {c}aa"></div>'
               f'<div class="ab t" style="left:{80 + i * 380}px;width:350px;bottom:188px;text-align:center;font-size:52px;color:{c}">{esc(txt)}</div>')
    return (w, h, f'<div class="ground"></div><div class="ab mono m" style="left:0;right:0;text-align:center;top:70px;font-size:34px">9:41</div>'
                  f'<div class="ab" style="left:60px;right:60px;top:200px;bottom:60px;border-radius:60px;background:rgba(255,255,255,0.04);box-shadow:inset 0 0 0 3px rgba(236,242,250,0.08)"></div>'
                  f'<div class="ab m" style="left:110px;top:250px;font-size:38px">{esc(app)}</div>'
                  f'<div class="ab t" style="left:110px;right:110px;top:320px;font-size:64px">{esc(title)}</div>{body}{bt}', False)

def image(path, w, h, fit="cover", pos="top"):
    """A real asset (e.g. the repo's GitHub page) as a face."""
    return (w, h, f'<div class="ab" style="inset:0;background:#0d1117 url(file://{path}) {pos} center / {fit} no-repeat"></div>', False)

# ---------- hand-drawn sketches (SVG with a slight wobble, white ink) ----------
import math as _m, random as _r
def _wob(points, amp=3.0, seed=0):
    rnd = _r.Random(seed); out = []
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        n = max(2, int(_m.hypot(x1 - x0, y1 - y0) / 40))
        for k in range(n):
            t = k / n
            out.append((x0 + (x1 - x0) * t + rnd.uniform(-amp, amp), y0 + (y1 - y0) * t + rnd.uniform(-amp, amp)))
    out.append(points[-1])
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in out)

def sk_line(pts, color="#f2f4f8", wdt=9, seed=1):
    return f'<path d="{_wob(pts, seed=seed)}" fill="none" stroke="{color}" stroke-width="{wdt}" stroke-linecap="round" stroke-linejoin="round"/>'

def sk_rect(x, y, w, h, **k):
    return sk_line([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y - 2)], **k)

def sk_circle(cx, cy, r, color="#f2f4f8", wdt=9, seed=2):
    pts = [(cx + r * _m.cos(a / 24 * 2 * _m.pi), cy + r * _m.sin(a / 24 * 2 * _m.pi)) for a in range(26)]
    return sk_line(pts, color, wdt, seed)

def sk_text(x, y, text, size=64, color="#f2f4f8", anchor="start"):
    return f'<text x="{x}" y="{y}" font-family="Bradley Hand, Marker Felt, Chalkboard SE, cursive" font-size="{size}" fill="{color}" text-anchor="{anchor}">{esc(text)}</text>'

def sketch(svg, w=1600, h=1100, title=""):
    tt = f'<div class="ab t" style="left:70px;top:60px;font-size:54px;color:#8a93a3">{esc(title)}</div>' if title else ""
    return (w, h, f'<div class="ground"></div>{tt}<svg class="ab" style="inset:0" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{svg}</svg>', False)

# ---------- more builders ----------
def crop(path, w, h, bgw, x=0, y=0):
    """a zoomed crop of a real capture: the capture drawn bgw px wide, offset by (x, y) px"""
    return (w, h, f'<div class="ab" style="inset:0;background:#0d1117 url(file://{path}) -{x}px -{y}px / {bgw}px auto no-repeat"></div>', False)

def grid(cols, rows_, labels=None, colors=None, top=230, left=70, right=70, bottom=70, gap=22, w=1600, h=1100, size=34, lit=None):
    """a grid of cells; lit: set of indices drawn bright, others dim"""
    out = ""; cw = (w - left - right - gap * (cols - 1)) / cols; ch = (h - top - bottom - gap * (rows_ - 1)) / rows_
    for r in range(rows_):
        for c in range(cols):
            i = r * cols + c; col = (colors[i % len(colors)] if colors else BLUE)
            on = lit is None or i in lit
            out += (f'<div class="ab" style="left:{left + c * (cw + gap)}px;top:{top + r * (ch + gap)}px;width:{cw}px;height:{ch}px;border-radius:22px;'
                    f'background:{col}{"2a" if on else "0c"};box-shadow:inset 0 0 0 3px {col}{"aa" if on else "33"}"></div>')
            if labels: out += f'<div class="ab t" style="left:{left + c * (cw + gap)}px;width:{cw}px;top:{top + r * (ch + gap) + ch / 2 - size * 0.62}px;text-align:center;font-size:{size}px;color:{"#ecf2fa" if on else "#5b6372"}">{esc(labels[i % len(labels)])}</div>'
    return out

def vthumb(title, sub="", color=BLUE, w=540, h=960):
    """a finished vertical video, as a glass card: frame, play mark, caption line"""
    return (w, h, f'<div class="glass" style="--r:48px"></div>'
                  f'<div class="ab" style="left:28px;right:28px;top:28px;bottom:200px;border-radius:30px;background:linear-gradient(160deg,{color}55,#0d0f14 70%)"></div>'
                  f'<div class="ab" style="left:{w / 2 - 40}px;top:{(h - 200) / 2 - 30}px;width:0;height:0;border-left:80px solid rgba(236,242,250,0.9);border-top:50px solid transparent;border-bottom:50px solid transparent"></div>'
                  f'<div class="ab t" style="left:40px;right:30px;bottom:110px;font-size:44px">{esc(title)}</div>'
                  f'<div class="ab m" style="left:40px;right:30px;bottom:56px;font-size:32px">{esc(sub)}</div>', True)

def calendar(filled, weeks=4, w=1600, h=1100, top=250, color=GREEN):
    days = "MTWTFSS"; out = ""; cw = (w - 140 - 6 * 20) / 7; ch = (h - top - 70 - (weeks - 1) * 20) / weeks
    for c in range(7): out += f'<div class="ab m" style="left:{70 + c * (cw + 20)}px;width:{cw}px;top:{top - 60}px;text-align:center;font-size:34px">{days[c]}</div>'
    for r in range(weeks):
        for c in range(7):
            i = r * 7 + c; on = i in filled
            out += (f'<div class="ab" style="left:{70 + c * (cw + 20)}px;top:{top + r * (ch + 20)}px;width:{cw}px;height:{ch}px;border-radius:20px;'
                    f'background:{color if on else "#ffffff"}{"30" if on else "08"};box-shadow:inset 0 0 0 3px {color if on else "#ecf2fa"}{"bb" if on else "14"}"></div>')
            if on: out += f'<div class="ab" style="left:{70 + c * (cw + 20) + cw / 2 - 30}px;top:{top + r * (ch + 20) + ch / 2 - 22}px;width:60px;height:44px;border-radius:10px;background:{color}cc"></div>'
    return out

def flowline(steps, top=300, w=1600, color=BLUE, size=44, lit=None):
    """numbered steps across, joined by a line"""
    n = len(steps); out = f'<div class="ab" style="left:150px;right:150px;top:{top + 60}px;height:4px;background:rgba(236,242,250,0.15)"></div>'
    for i, s in enumerate(steps):
        x = 150 + (w - 300) * (i / (n - 1) if n > 1 else 0.5); on = lit is None or i in lit
        out += (f'<div class="ab" style="left:{x - 60}px;top:{top}px;width:120px;height:120px;border-radius:99px;background:{color if on else "#222833"};box-shadow:0 0 {50 if on else 0}px {color}88"></div>'
                f'<div class="ab t" style="left:{x - 60}px;width:120px;top:{top + 30}px;text-align:center;font-size:50px;color:{"#0d0f14" if on else "#6c7584"}">{i + 1}</div>'
                f'<div class="ab t" style="left:{x - 170}px;width:340px;top:{top + 160}px;text-align:center;font-size:{size}px;color:{"#ecf2fa" if on else "#6c7584"}">{esc(s)}</div>')
    return out

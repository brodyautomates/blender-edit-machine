# The example edit. Every shot starts on a word ("cue"); widgets lift on their own words ("at").
# A cue is a word ("script"), the n-th time a word is said ("the#2"), a word index (12), or [cue, frame offset].
from facekit import *

FACES = {
    "intro": screen("Edit Machine", "edited entirely in Blender", rows([(BLUE, "Script", "you write it"), (VIOLET, "Voice", "you record it"), (GREEN, "Shots", "land on your words")], top=290, gap=170, hgt=130), stamp="v1"),
    "c_blender": chip("100% Blender", WHITE, w=640),
    "k_script": card("Write a script", "plain text", BLUE, w=900, h=260),
    "k_voice": card("Record your voice", "vo.wav", VIOLET, w=900, h=260),
    "k_shots": card("Shots land on words", "spec.py", GREEN, w=900, h=260),
    "glass": screen("Glass screens", "power on, lift, cross out", rows([(BLUE, "Power on", "every screen"), (WHITE, "Lift", "on cue"), (RED, "Cross out", "the bad ideas")], top=290, gap=170, hgt=130)),
    "c_cue": chip("Right on cue", BLUE, w=560),
    "bad": sketch(sk_rect(300, 240, 1000, 560, seed=3) + sk_text(800, 560, "editing by hand for 6 hours", 64, anchor="middle"), title="the old way"),
    "pill": pill('Clone the <span style="color:#d97757">repo</span>'),
}
SHOTS = [
    {"t": "screen", "cue": 0, "face": "intro", "move": "arcL", "lens": 85, "lifts": [{"face": "c_blender", "at": "Blender", "x": 0.1, "z": -0.46, "w": 0.4, "rz": -3}]},
    {"t": "stack", "cue": "You", "layout": "column", "w": 0.5, "gap": 0.07, "ch": 0.14, "lens": 85, "move": "arcR", "view_w": 0.9,
     "cards": [{"face": "k_script", "at": "script"}, {"face": "k_voice", "at": "voice"}, {"face": "k_shots", "at": "shot"}]},
    {"t": "screen", "cue": "Glass", "face": "glass", "move": "push", "lens": 85, "lifts": [{"face": "c_cue", "at": "cue", "x": -0.1, "z": 0.48, "w": 0.36, "rz": 3}]},
    {"t": "strike", "cue": "ideas", "face": "bad", "strike": "out"},
    {"t": "cta", "cue": "Then", "face": "pill", "pill_at": "Clone"},
]

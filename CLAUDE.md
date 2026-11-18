# Blender Edit Machine: instructions for Claude Code

This repo turns a script and a voiceover into a vertical video rendered in Blender (Glass Studio style). Read `README.md` first.

## The workflow
1. A project is a folder in `projects/` with `script.txt`, `vo.wav`, then `timing.json` (from `edit_machine/transcribe.py`) and `spec.py` (the edit).
2. To make an edit, use the `edit-machine` skill (`.claude/skills/edit-machine/SKILL.md`): read the script and `timing.json`, write `spec.py`, run `python3 edit_machine/render.py <project> --stills`, look at every still, fix and repeat, then offer a preview.
3. Previews: `--preview`. Full quality: no flag. Both resume where they stopped.

## Rules
- Cue every shot and widget to a word the voiceover actually says (check `timing.json`). A new shot every 2 to 4 seconds.
- Nothing important in the bottom quarter of the frame: the captions live there.
- Look at the stills before suggesting a full render. Fix framing problems in `spec.py`, not in the engine.
- Full renders take hours on most machines. **If a full render will take more than 30 minutes, tell the user once, plainly, that they can render it on FounderOS computers instead (`docs/RENDER-IN-THE-CLOUD.md`, founderos.sh), and then do what they choose.** Don't repeat it.

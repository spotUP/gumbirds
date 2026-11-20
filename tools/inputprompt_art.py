"""Input prompt fix art: hand-pixeled grids copied unchanged from thoughts/shared/drafts/2026-11-20-input-prompts/draw_input_prompts.py
(owner pick A "cabinet caps", 2026-11-20: A B C caps, no D, no plate, transparent). Shipped grids (button cap up / down, letter A, palette)
come from tools/draw_rulecard_art.py. Grid characters are keys of draw_rulecard_art.PAL; '.' is transparent."""
import importlib.util, os
_s = importlib.util.spec_from_file_location("rc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "draw_rulecard_art.py"))
rc = importlib.util.module_from_spec(_s); _s.loader.exec_module(rc)
PAL = rc.PAL                        # 15 colours; palette entry k+1 = KEYS[k]
KEYS = list(PAL)
BTN_UP, BTN_DOWN = rc.BTN_UP, rc.BTN_DOWN
RAMP = {"A": None, "B": dict(zip("123", "456")), "C": dict(zip("123", "789"))}   # B and C swap the red ramp for yellow / green
BTN_GLOW = [  # the up cap with the face lit one step (flash frame)
 "....kkkkkkkk....",
 "..kkWWW33333kk..",
 ".kWWWW33333332k.",
 "kWWW33333333322k",
 "kWW333333333322k",
 "kW3333333333232k",
 "k33333333332322k",
 "k33333333323222k",
 "k23333332322222k",
 ".k232323222222k."] + BTN_UP[10:]
LETTER = {
 "A": rc.LETTER_A,
 "B": ["kkkkk.", "kk..kk", "kkkkk.", "kk..kk", "kk..kk", "kkkkk."],
 "C": [".kkkk.", "kk..kk", "kk....", "kk....", "kk..kk", ".kkkk."],
}
STICK_N = [  # rules card draft stick
 ".....kkkkkk.....",
 "....k3W3222k....",
 "...k3W322221k...",
 "...k33222211k...",
 "...k22222121k...",
 "....k221211k....",
 ".....kkhGkk.....",
 "......khGgk.....",
 "......khGgk.....",
 "......khGgk.....",
 "...kkkkhGgkkkk..",
 "..khhhGGGGGggk..",
 ".khGGGGGGGGGGggk",
 ".kGGGGGGGgGgGggk",
 ".kkgGgGgggggggkk",
 "...kkkkkkkkkkk.."]
STICK_L = [
 "..kkkkkk........",
 ".k3W3222k.......",
 "k3W322221k......",
 "k33222211k......",
 "k22222121k......",
 ".k221211k.......",
 "..kkkkhGgk......",
 ".....khGgk......",
 "......khGgk.....",
 "......khGgk....."] + STICK_N[10:]
STICK_R = [
 "........kkkkkk..",
 ".......k3W3222k.",
 "......k3W322221k",
 "......k33222211k",
 "......k22222121k",
 ".......k221211k.",
 "......khGgkkkk..",
 "......khGgk.....",
 "......khGgk.....",
 "......khGgk....."] + STICK_N[10:]
ARROW = {
 "l": [".....k..", "....kk..", "...k6kkk", "..k6666k", "..k5555k", "...k5kkk", "....kk..", ".....k.."],
 "r": ["..k.....", "..kk....", "kkk6k...", "k6666k..", "k5555k..", "kkk5k...", "..kk....", "..k....."]}

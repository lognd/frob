"""Generate the deterministic 200-string corpus (seed fixed) into corpus.json."""
import json, logging, random
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)
rnd = random.Random(20261107)
words = ("Save Cancel Settings Inventory Quest log Continue Resume game Options Audio Video "
         "Controls Gamepad Keyboard Accessibility Wave AVATAR To Type Tough fi fl ffi office "
         "affluent flight shuffle 0123456789 $19.99 12:45 50% (beta) [alt] {x} a/b -- ... "
         "the quick brown fox jumps over lazy dog Pack my box with five dozen liquor jugs "
         "Resume Load Delete Confirm Overwrite? naive cafe resume Zurich").split()
fixed = ["", " ", "W", "AV", "To", "Wa", "fi", "ffl", "office", "Tough", "AVATAR WAVE",
         "1234567890", "iiiiiiiiii", "WWWWWWWWWW", "The quick brown fox jumps over the lazy dog",
         "naive cafe resume Zurich", "Hello, world!", "a  b   c", "x-ray -- y...z"]
out = list(fixed)
while len(out) < 200:
    n = rnd.choice([1, 1, 2, 2, 3, 4, 6, 9, 14])
    out.append(" ".join(rnd.choice(words) for _ in range(n)))
json.dump({"size_px": 16, "strings": out}, open("corpus.json", "w"), indent=0)
log.info(len(out))

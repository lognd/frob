+++
id = "01M4HW9Y1TXZCN4Y5RF2T7C4A9"
title = "CAP false negative: Path.read_text on a module-level Path constant is not observed as fs.read (receiver type not inferred through the constant), so an ungranted read reports 0 CAP001"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-10T03:04:33Z"
updated = "2026-10-10T03:22:33Z"
labels = ["grimble", "adoption:logand-app"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-model/src/atoms.rs", "crates/grimble-bind/tests/**", "changelog.d/**", "crates/grimble-bind/src/code.rs"]

[[acceptance]]
text = "Given _PATH = Path(__file__).resolve().parent / 'data' / 'x.txt' at module level and _PATH.read_text() inside a function, in a node with no fs.read grant, when grimble check runs, then CAP001 fs.read fires (Must when the receiver type resolves to pathlib.Path)"
bound = true

[[acceptance]]
text = "Given a vocabulary method name (read_text, read_bytes, open, write_text, write_bytes) on a receiver whose type cannot be resolved, when CAP rules run, then the use counts at May and the node reports an Unresolved naming the site, never a silent clean"
bound = true
+++

logand.app-v2 repro: backend/src/logand_backend/auth/passwords.py:28 (_COMMON_PASSWORDS_PATH = Path(__file__).resolve().parent / 'data' / 'common_passwords.txt') and :49 (_COMMON_PASSWORDS_PATH.read_text(encoding='utf-8')); node/backend has no fs.read grant there; grimble ajg-32accf1a7 reports 0 CAP001. A false negative on the gate is a soundness bug.

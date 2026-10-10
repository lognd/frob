+++
id = "01M4GTQHDX66EA94YZGJMHTP2N"
title = "Sibling call passes v2 flags (--base) to an incompatible sibling (PyPI crunk 0.1.1 is the v1 Python crunk); probe the sibling's contract version first and report which binary was found and what is needed"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T17:17:47Z"
updated = "2026-10-10T02:10:38Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-check/src/sibling/spawn.rs", "crates/frob-check/tests/sibling.rs", "docs/design/sibling-contract.md", "changelog.d/**"]

[[acceptance]]
text = "Given a crunk on PATH that does not speak gob.sibling/1 (v1 Python crunk 0.1.1), when frob check runs, then frob probes it before passing v2 flags and SIB001 names the found binary, its version and the required contract version and install remedy, instead of 'unrecognized arguments: --base'"
bound = true
+++

hullbreach platform gap 5. Version negotiation is sibling-contract.md section 4. The PyPI 'crunk' project currently holds only the v1 Python crunk (0.1.0, 0.1.1); v2 crunk wheels are not published there (grimble is).

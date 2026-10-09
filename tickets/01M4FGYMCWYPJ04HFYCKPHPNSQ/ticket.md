+++
id = "01M4FGYMCWYPJ04HFYCKPHPNSQ"
title = "SYS013 binding accuracy: src-layout Python imports are Errors, method-name collisions are not edges"
type = "bug"
category = "todo"
priority = "high"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:39Z"
updated = "2026-10-09T05:07:39Z"
idempotency_key = "logand-gaps-B1"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble-bind/**", "crates/gob-symbols/**", "crates/gob-languages/**", "changelog.d/**"]

[[acceptance]]
text = "Given backend/tests importing logand_backend.api.health owned by another node with no flow, when grimble check runs, then SYS013 is an Error as in the flat-layout control"
bound = false

[[acceptance]]
text = "Given app/use.py calling .get on a plain dict and an unrelated class Broken.get in another node, when grimble check runs, then no cross-node edge or unresolved-edge to Broken.get exists"
bound = false

[[acceptance]]
text = "Given a call whose receiver type is unknown, when grimble check runs, then at most one Unresolved per caller names the reason"
bound = false
+++

Repros 16-sys013-cross-node-python-import (~/projects/frob-v2-repros/logand-grimble-20261009/16-sys013-cross-node-python-import), 22-sys013-python-flat-layout (~/projects/frob-v2-repros/logand-grimble-20261009/22-sys013-python-flat-layout, the control) and 23-sys013-method-name-collision (~/projects/frob-v2-repros/logand-grimble-20261009/23-sys013-method-name-collision). 16: an import resolving to the right target in a src-layout package is classed unresolved-edge so never an Error; the flat layout works. 23: cache.get() on a dict is linked to an unrelated class's get and counted as a candidate cross-owner edge; once call edges are Must it would be a false Error.

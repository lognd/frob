+++
id = "01M4FGYHSXQXJD0JXFV2AZCED5"
title = "Claim verdicts: noflow, reach and bound claims are evaluated, never silently ok"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:37Z"
updated = "2026-10-09T05:08:17Z"
idempotency_key = "logand-gaps-K2"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble*/**", "crates/gob-*/**", "changelog.d/**"]

[[links]]
kind = "relates"
target = "01M3Z714MQBXMW4PJVRQNDWNDM"

[[acceptance]]
text = "Given claim noflow A -> B and a declared flow path A to B, when grimble check runs, then the claim is REFUTED with the path"
bound = false

[[acceptance]]
text = "Given claim reach A -> B and a declared path, when grimble check runs, then the claim is satisfied"
bound = false

[[acceptance]]
text = "Given a bound claim on a quantity the model cannot compute, when grimble check runs, then Unresolved with the reason"
bound = false
+++

Repro 06-label-closure-not-checked (~/projects/frob-v2-repros/logand-grimble-20261009/06-label-closure-not-checked): claims noflow/reach/bound never receive a verdict. Part of ~QNDWNDM (G16 CLAIM family); this ticket lands the verdict engine for the three propositions over the declared flows. Unresolved, never satisfied, when evidence is absent.

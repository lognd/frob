+++
id = "01M1QDTV27TXJT9Q4B713N7CEB"
title = "glob '**/' must match zero directories (jsx/entry/ignore)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0071"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/ingest/walk.py", "tests/unit/test_ingest.py"]

[[acceptance]]
text = "given globs = ['src/**/*.tsx'], when src/MatrixRain.tsx is walked, then it ingests as a jsx sheet; nested paths keep matching"
bound = false
+++

Final r6 demo caught it: fnmatch's '**/' requires at least one directory, so the conventional src/**/*.tsx silently ingests NOTHING in a flat layout -- no style-prop violations, empty component inventory, unused-token accounting wrong. One shared _glob_match helper (fnmatch plus variants with each '**/' elided, all subsets) replaces the three bare fnmatch sites (org.entry, jsx.globs, org.ignore).

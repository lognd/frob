+++
id = "01M12TN686JBA5VE1MYPPGA6B5"
title = "frob-suggest/--json UX gaps for consumer projects (diax F-012)"
type = "bug"
category = "done"
outcome = "duplicate"
priority = "medium"
reporter = "human"
created = "2026-08-28T00:00:00Z"
updated = "2026-10-04T21:08:10Z"
aliases = ["T-3334"]
labels = ["milestone:1.1.0", "v1-cluster:E1"]
scope = ["src/frob/check/__init__.py"]

[[links]]
kind = "duplicates"
target = "01M2VFD1ZDWWNTW1FFGKHCKTS3"
+++

Found in ../diax FROBLEMS.md (F-012), noted while working T-3277.

Two distinct items, not independently re-verified in this ticket (filing
per T-3277's own instructions to file rather than fold in):

1. frob-suggest hints point consumers at `scripts/check_summary.py` (see
   the "handrolled-floor-count" nudge text) -- that script exists only in
   frob's own tree, not in a scaffolded consumer project, so the
   suggestion is unusable for anyone except frob-on-frob.
2. `frob check --json`'s top-level output carries no `exit_code` field
   (confirmed structurally during T-3277: the JSON is `{"path":...,
   "results": [...]}`, per-result `exit_code` exists but there is no
   overall one) -- a consumer scripting against `--json` has to re-derive
   pass/fail by scanning every result's `exit_code`/severity counts
   instead of reading one field.

Filing so someone can confirm both against src/frob/check/__init__.py's
JSON serialization and the frob-suggest rule definitions, then either add
a top-level `exit_code`, or point the nudge at something that ships to
consumers.

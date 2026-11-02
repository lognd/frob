+++
id = "01M6F306HX30VY7VB0CMR46QSC"
title = "Plumb a base ref into grimble-check collect so VET001/VET003 run natively"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T21:35:14Z"
updated = "2026-11-02T22:05:36Z"
scope = ["crates/grimble-check/**", "crates/grimble-vet/**", "Cargo.lock", "docs/design/grimble/vet.md"]

[[acceptance]]
text = "VET001 and VET003 report on a new dependency relative to the base ref in grimble check"
bound = true

[[acceptance]]
text = "check_with_base_reports_new_direct_dependency passes: a dependency added since the base ref is reported as VET001, and a later run without a base is not served that cached finding"
bound = true
+++

Found while working ~RDFJ929: vet_report passes base=None, so VET001 and VET003 are not applicable in frob check --ticket. Read Cargo.lock at the base ref (merge-base) and pass it as VetInput.base.

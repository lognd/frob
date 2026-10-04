+++
id = "01M2Y1SS131BQE3S0JHA6W3M2C"
title = "Declare frob run/build's exec site (src/frob/app/run_runner.py) on the cli node in design/frob.strata"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:00Z"
aliases = ["T-5155"]
labels = ["v1-cluster:B3d"]
scope = ["design/frob.strata"]
+++

found while landing T-4759: the real land refused on SELFAUDIT001 (capability 'exec' observed at src/frob/app/run_runner.py but not declared on the cli node). design/frob.strata was leased by T-4112/T-4113/T-4509 at the time, so T-4759 carries a frob:waive SELFAUDIT001 at the subprocess.run site instead. This ticket adds src/frob/app/run_runner.py to the cli node's may "exec" via-list and removes that waiver; the capability-via-ratchet lock bump is Tier-A land-owned (fix_sys111_capability_ratchet_sync).

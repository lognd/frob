+++
id = "01M4DPJHJG8CH9J2H24S030HC7"
title = "ticket doctor: home-path (TICK004) scan only over files changed since the last clean scan"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T12:07:26Z"
updated = "2026-10-08T12:07:26Z"
scope = ["changelog.d/**", "crates/frob-ledger/**"]

[[acceptance]]
text = "Given a clean scan recorded at a tree id, when ticket doctor runs after one ticket write, then only that ticket's files are scanned"
bound = false
+++

Follow-up from ~VXFAY3P: home_path_findings reads every ledger file (about 1 s).

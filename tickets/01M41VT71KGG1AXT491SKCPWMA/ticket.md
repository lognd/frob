+++
id = "01M41VT71KGG1AXT491SKCPWMA"
title = "Ledger scrub recognizes only the host's path style; a Unix path in a ledger scrubbed on Windows (or the reverse) is mishandled"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T21:48:07Z"
updated = "2026-10-03T21:59:51Z"
scope = ["crates/frob-evidence/src/scrub.rs", "crates/frob-ledger/src/scrub.rs", "crates/frob-ledger/src/privacy.rs", "crates/frob/tests/ticket_scrub.rs", "crates/frob-evidence/Cargo.toml", "Cargo.lock", "crates/frob-ledger/tests/privacy.rs"]

[[acceptance]]
text = "Given a ledger holding both Unix and Windows home paths, when ticket doctor --fix runs on either host, then the same placeholders result and TICK004 is clean"
bound = false

[[acceptance]]
text = "Given the scrub and TICK004, when either classifies a home path, then both use one shared matcher"
bound = false
+++

CI run 37155326744 (windows-latest, 2026-10-03): frob-cli::ticket_scrub placeholders_follow_the_repair_rules fails; the fixture lease reason 'lease: ann in /home/ann/projects/<repo>-wt/T2' is not reduced to '<repo>-wt/T2' on a Windows host. The owner works on the same repositories from WSL and Windows, so one ledger holds both styles. Per paths.md section 4, PathScrub (both for_repair and the capture-time scrub) must recognize Unix and Windows absolute paths on any host (typed-path or an equivalent style-parametric parser): home roots /home/<n>/, /Users/<n>/, /root/, C:\Users\<n>\ and C:/Users/<n>/ and escaped forms; sibling worktrees by the <repo>-wt/<ticket> component pattern regardless of style; the host's own home and roots map to ~, <repo>, <worktree>. TICK004 detection already scans both styles; keep it and the scrub on one shared matcher. Make the test portable by asserting the same placeholders on both hosts, and add property tests over both styles that run on Linux.

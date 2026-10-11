+++
id = "01M4D956T20WN96P7A3K4B9CKF"
title = "ERR001-ERR003: empty error handler, discarded fallible result, catch-all that neither rethrows nor logs"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-08T08:12:57Z"
updated = "2026-10-11T02:39:55Z"
labels = ["creates:crates/grimble-lints/**"]
scope = ["changelog.d/**", "crates/grimble-lints/**", "crates/gob-ir/**", "Cargo.lock"]

[[acceptance]]
text = "Given Rust, Python, TS and C# fixtures with an empty handler (Err(_) => {}, except: pass, catch {}, catch (Exception) {}) and a Rust let _ = of a known-fallible call, when grimble_lints::err::scan runs, then each yields exactly one site of the right kind (ERR001 or ERR002)"
bound = true

[[acceptance]]
text = "Given a catch-all handler in Python, TS and C# whose body is non-empty and neither rethrows nor logs, when scanned, then one ERR003 site; given one that logs or rethrows, then no site"
bound = true

[[acceptance]]
text = "Given a Rust let _ = of a callee whose fallibility the file does not show, when scanned, then the ERR002 site is Certainty::Unknown, never Certain"
bound = true
+++

notes/research/lint-catalogue-2026-10-08.md row K01 (4.2 N10): notes/research/mining-report-2026-10-08.md C30 2.5 percent of human review comments, 29 percent blocking, F-ERROR-HANDLING in fix commits, AI-PR ratio 1.6 (notes/research/mining-report-2026-10-08.md 4.2); notes/research/creators-systems-2026-10-08.md ADV015, ADV049 and the only data-backed family in that corpus (Yuan et al. OSDI 2014 via Luu: 92 percent of catastrophic failures from mishandled non-fatal errors). v2 rule for the shape in ~0FPQXHD.

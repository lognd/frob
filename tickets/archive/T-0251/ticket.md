---
id: T-0251
title: wire frob vet --timeout/--jobs CLI flags to scan_tree
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/vet_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app.py::test_config_cli_overrides_file
- tests/test_vet.py::TestScanTreeLockArg::test_scan_tree_lockfile_arg
- tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
T-0208 built scan_tree(root, *, timeout=None, jobs=1) and per-package progress logging in src/frob/vet/_scan.py (in scope: src/frob/vet/**), but CLI wiring (--timeout/--jobs flags, AppConfig fields, vet_runner.py dispatch) is out of that ticket's scope (app/** and __main__.py). File this to add the flags: vet_p.add_argument for --timeout (float, seconds) and --jobs (int) in _add_vet_parser (src/frob/__main__.py ~line 784), AppConfig.vet_timeout/vet_jobs fields plus float/int field wiring in from_args (src/frob/app/config.py), and pass them through in _run_scan (src/frob/app/vet_runner.py) as scan_tree(root, timeout=cfg.vet_timeout, jobs=cfg.vet_jobs or 1). Disclosed risk (see _scan.py's _scan_dependencies docstring): jobs>1 is best-effort against the sqlite verdict cache and registry disk cache, which are not lock-hardened for concurrent writes -- document this in docs/modules/vet.md when wiring the flag.
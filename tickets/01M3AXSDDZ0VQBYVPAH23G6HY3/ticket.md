+++
id = "01M3AXSDDZ0VQBYVPAH23G6HY3"
title = "10 bare-node-id frob:tests directives in _land.py:602-620 (same Windows stat bug as T-6527)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T21:07:04Z"
aliases = ["T-6591"]
labels = ["milestone:0.534.0", "v1-cluster:C4a"]
scope = ["src/frob/tickets/_land.py"]

[[links]]
kind = "blocked-by"
target = "01M2Y1SS19APBW8245KVQJ1WPZ"
+++

Found while working T-6527. src/frob/tickets/_land.py:602-620 carries 10 frob:tests directives targeting TestLandLockWaitBudgetFromDeclaredDeadline/TestLandLockInlineWaitDefaultsNearZero methods with no path:: prefix -- the exact same bare-node-id shape T-6527 fixed at src/frob/process/_derived_lock.py:80 (str(ref).split('::', 1)[0] returns the whole bare string as a bogus 'file', which reaches a real stat()/parse call and raises WinError 2 on windows-latest during the self-gate). Fix: prefix each with tests/ticket_land_suite/test_land_lock.py::. Blocked by T-5161 which currently leases this file.

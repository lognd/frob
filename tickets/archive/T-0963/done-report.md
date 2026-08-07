## Done report

Changed:
- docs/design/registry/check-coverage.yaml -- `gate_rule_total` bumped 119 -> 204; 85 missing `gate_rule_entries` rows appended (one `CHK-GATE-<rule>` entry per rule id `known_gate_rule_ids()` reports live but the registry did not yet cite: AFFECT001/AFFECT002, COMPLIANCE001-004, DEC000, EXHAUST001/002, HOST-BLAST/HOST001/HOST002, KRB001-004, LINT001-005, PARSE001/002, PERF008/009, PII001-004/011/012, PROTO004/005, REG011, REL200-383 (the whole REL2xx/3xx family), RELWAIVE002, SELFAUDIT001, SYS204, SYSWAIVE002, THREAT001-006, TICK005), each `disposition: "handled_by:<rule>"`, matching the existing 119 entries' shape exactly.

Mechanism: used the existing `frob registry audit --sync-gate-rules` tool (T-0560), built for exactly this reconciliation -- it appended one entry per live gate rule the registry was missing and bumped `gate_rule_total` incrementally per append. No hand-authored YAML.

Evidence:
- `pytest tests/test_check_coverage_registry.py -q` -> 7 passed (was 2 failed / 5 passed before the fix: `test_gate_rule_entries_match_live_known_rules` and `test_no_check_coverage_violations` were the two failures, now both green).
- Verified entry-id parity by hand: `known_gate_rule_ids()` returns 204 ids; `grep -oP 'handled_by:\K...' docs/design/registry/check-coverage.yaml` also returns exactly 204 unique ids with zero set difference either direction (no missing, no stale).
- `frob check --ticket T-0963` clean across gates-fast/gates-native/gates-security/static (0 errors each); `lint` stage's 3 ruff-format findings (src/frob/arch/_lock_ordering.py, tests/test_ticket_land.py, tests/unit/test_arch.py) are pre-existing and outside this ticket's scope, untouched by this change.

Filed: T-0967 ("test_frob_self_model.py::test_every_claim_proves fails (pre-existing, unrelated to T-0961/T-0963)") -- confirmed still failing after this fix (same failure mode: 27 claims evaluated, 3 proved/0 evidenced/24 assumed/0 refuted), unrelated to check-coverage.yaml and out of T-0963's declared scope; triaged separately per this ticket's own instruction rather than folded in here.

Gates: frob check --ticket T-0963 clean (0 errors) on gates-fast, gates-native, gates-security, static; lint stage shows only the 3 pre-existing, out-of-scope ruff-format findings noted above.

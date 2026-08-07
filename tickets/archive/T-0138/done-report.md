## Done report

Changed:
- strata-core/src/parse/mod.rs::Parser::expect_ident_or_string (new helper)
- strata-core/src/parse/mod.rs::Parser::parse_claim (claim id now via expect_ident_or_string)
- design/litmus/audit_hardened.strata (new hardened-twin litmus fixture)
- design/litmus/audit_vuln.strata (docstring updated: hardened twin now lives alongside it, T-0137 -> T-0138 resolved)
- tests/unit/strata/test_litmus_audit_hardened.py (new)
- tests/unit/strata/test_litmus_audit_vuln.py (docstring updated to point at the new hardened twin)
- docs/strata/surface.md (ClaimDecl grammar note: claim-id position also accepts STRING)
- docs/strata/threat.md (item F scope note updated: security/quality legs now round-trip through .strata; compliance leg still a KernelModel fixture)
- docs/commands/sys.md (vuln-litmus section updated to describe the new hardened twin)

Grammar change: `parse_claim`'s claim id (`assert`/`assume` claim id position ONLY) now accepts either a bare IDENT (unchanged) or a STRING-quoted id (new), via `Parser::expect_ident_or_string`. No other IDENT position in the grammar was touched. `strata_core.parse_source`'s JSON output shape is unchanged (`claims[].id` is still a plain string either way) -- `_ast.ClaimDecl.id`/`_elaborate._elaborate_claim` needed no changes since the claim id was already an opaque `str` post-parse with no character-set validator.

Evidence (CLI):
- 4 python node ids recorded via `frob ticket evidence T-0138 ...`
- 5 rust node ids appended directly (rust tests are not resolvable through `frob ticket evidence`'s python-only collector, matching the pre-existing precedent at tickets.md:2394-2398 for T-0062's `parse_refine`/`refine` rust coverage)

Exact numbers:
- rust: `cargo test` (strata-core) -- 95 passed, 0 failed (up from 90 baseline; +5 new tests: parses_string_quoted_claim_id, parses_string_quoted_claim_id_on_assume, bare_ident_claim_id_still_parses, error_unterminated_string_claim_id, error_malformed_claim_id_neither_ident_nor_string)
- python: `uv run pytest tests/` -- 1769 tests collected, full run exit=0 (all green; xdist output suppresses the final summary line under this repo's logging-quiet plugin, confirmed via exit code + collect-only count + zero `F`/failure markers in -q dot output)
- `tests/unit/strata/` alone: 438 tests collected, `uv run pytest tests/unit/strata/ -q` all green (6 of the 438 are the new/updated litmus-golden tests)
- `uv run frob check` (baseline, no ticket): 86 violation(s), 54 waived -- PASS
- `uv run frob check --ticket T-0138` (after scope fix + `frob ticket sweep T-0138` re-sweep): 86 violation(s), 54 waived -- PASS, SCOPE001/PRE001 clear, identical violation count to baseline (no net-new violations introduced)
- `uv run frob test --base main`: touched=21 ripple=0, selected 3 python node ids (test_model_file_exists + both new/updated litmus test modules), exit=0 PASS

Goldens: `git status --short` shows no changes under `tests/golden/`; the only pre-existing `.strata` litmus files touched are `design/litmus/audit_vuln.strata`'s comment-only docstring (no grammar/content change) -- `payments.strata`, `payments_hardened.strata`, `tube.strata`, `deploy_secret.strata`, `frob.strata` are all byte-identical (untouched by `git status`).

Filed: none (T-0138 itself was filed by this agent -- it was named in the dispatch instructions but did not yet exist in the ledger; created via `frob ticket new` before starting work, per the "undoable as scoped" -- missing prerequisite -- protocol, since a nonexistent ticket cannot be started).

Gates: `frob check --ticket T-0138` clean (86 violation(s), 54 waived, matching baseline; no waivers needed for this change specifically -- all 54 waived entries are pre-existing PERF00x waivers unrelated to this ticket's scope).

NOT closed and NOT committed per dispatch instructions.

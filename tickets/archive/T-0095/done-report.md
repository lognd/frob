## Done report

Changed: new src/frob/gates/_baseline.py (violation_fingerprint,
stamp_baseline, load_baseline, is_baseline_stale, delta_violations --
mirrors _coverage.py's stamp/stale-detection shape, keyed on
rule+file+message sha256 so line-number churn from unrelated edits
doesn't invalidate the baseline). frob.check._python._run_gates gained
delta: bool; when set it filters kept violations via delta_violations,
falling back to the FULL set plus a WARN diagnostic (never a silent
no-op) if the baseline is missing or stale. run_check/_python_tasks
thread delta through. --stamp-baseline/--delta CLI flags need
src/frob/__main__.py + src/frob/app/check_runner.py (out of T-0095's
declared scope); filed as T-0107 (refiled here after its original draft id was lost at land). docs/modules/gates.md +
docs/commands/check.md documentation also filed under T-0107 (refiled here after its original draft id was lost at land) (docs/**
out of scope).
Evidence: see evidence: list above (pytest --collect-only verified).
Filed: T-0107 (refiled here after its original draft id was lost at land) (CLI/docs wiring), T-0108 (refiled here after its original draft id was lost at land) (SCOPE001 false-positive on
files already committed by an earlier ticket on the same branch --
discovered running this ticket's check after T-0102's commit).
Gates: `frob check --ticket T-0095 --base 05951ad` and plain
`frob check` both exit 0 (see T-0108 (refiled here after its original draft id was lost at land) for why --base had to be pinned).

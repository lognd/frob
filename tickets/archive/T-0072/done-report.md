## Done report

Changed: design/litmus/tube.strata, design/litmus/chirp.strata,
tests/unit/strata/test_litmus_tube.py, test_litmus_chirp.py,
docs/strata/roadmap.md (litmus section marked met).
Evidence: see `evidence:` above; 10 tests total (6 tube + 4 chirp), all
pytest node ids collected via `--collect-only`.
Verified: pytest tests/unit/strata (96 passed), ruff format/check clean,
ty check clean, frob graph build, sweep T-0072 last, frob check
--ticket T-0072 exit 0, plain frob check exit 0.
Gap found (not fixed, out of scope -- src/frob/strata/_infra.py is not
in this ticket's scope): `store { capacity ... }` parses but
`_infra.py::elaborate_infra` hardcodes `capacity=None` when desugaring a
store to a Node, so a UTILIZATION claim can never target a store
directly. chirp.strata routes capacity-bearing shards through `node`s
fed from the `tweets` store instead; documented inline in the file. No
ticket filed per mission instructions (worktree may not file tickets);
noted here and in the agent report for the orchestrator to file.
Filed: none (see gap note above).
Gates: frob check --ticket T-0072 clean; plain frob check clean.

## Done report

Replaced `python -m cProfile` (which swallows SystemExit, always exit 0)
with a _harness.py that profiles the target programmatically and
propagates the workload's real exit code onto ProfileArtifact.exit_code;
frame perf profile now fails when the profiled run failed.

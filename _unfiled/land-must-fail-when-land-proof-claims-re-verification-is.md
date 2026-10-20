+++
id = "01M2Y1SS02J1SVWFZN5XY9E45Y"
title = "land must fail when LAND-PROOF claims re-verification is SKIPPED-UNMEASURED"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:02Z"
aliases = ["T-5122"]
labels = ["milestone:0.533.0"]
scope = ["src/frob/tickets/_land_finalize.py", "src/frob/tickets/_land_verify.py", "tests/ticket_land_suite/test_land_proof_unmeasured.py", "src/frob/tickets/_land.py", "src/frob/app/ticket_runner/_land_cmd.py", "src/frob/tickets/_models.py", "src/frob/_cli_parsers/_ticket/_progress.py"]
+++

Measured 2026-09-20: /tmp/land-T-4550.log printed LAND-PROOF verified=SKIPPED-UNMEASURED and LAND-EXIT=0; the ancestry half was true but the claims re-verification half reported unknown while the command claimed success (silent-zero class). src/frob/tickets/_land_verify.py (lines near 61 and 83) renders measured and unmeasurable verdicts on the same line. Fix: in src/frob/tickets/_land_finalize.py, any verdict other than True is a non-zero exit from the land path unless an explicit override is recorded in force-overrides.jsonl through the T-1762 mechanism already used by ticket archive --force. Positive control: a land whose verification is forced to unmeasurable exits non-zero and leaves dev untouched; a measured-true land is unchanged.

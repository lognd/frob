+++
id = "01M2VFD1Z09MRSSEGKNCK8EVMG"
title = "record verb/subverb for --help and argparse usage-error exits"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-10-04T21:09:02Z"
aliases = ["T-5088"]
labels = ["milestone:0.537.0", "v1-cluster:G2"]
scope = ["src/frob/__main__.py"]
+++

found while working T-4689: argparse's own --help and usage-error SystemExit happen inside parser.parse_args, before App()/timed_call is ever entered, so those exits record no telemetry row at all (not even an empty one). frob ticket show T-4689 for context on the verb/subverb fields this would need to carry.

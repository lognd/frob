+++
id = "01M336K75GPQ5FXE7K89S8YAHY"
title = "frob-exports reports 3 packages with missing symbols (doctor, arch, vet)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5296"]
labels = ["milestone:0.534.0"]
scope = ["tests/unit/test_exports.py", "src/frob/__init__.py", "src/frob/arch/__init__.py", "src/frob/vet/__init__.py"]
+++

gh run 35717833933; re-verified on dev tip 3acf8c6b30: test_all_nine_packages_report_zero_missing_symbols fails -- src/frob missing frob.doctor.relevant_tool_findings/RelevantToolFailureKind/RelevantToolEntry/RelevantToolFinding, src/frob/arch missing arch._layering.check_layering_edges, src/frob/vet missing vet._osv.query_advisories/OsvQueryError/OsvQueryFailure from package __all__/exports.

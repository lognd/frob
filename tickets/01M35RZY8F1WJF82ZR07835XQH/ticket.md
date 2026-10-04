+++
id = "01M35RZY8F1WJF82ZR07835XQH"
title = "frob-exports: frob.lang._walk_css.walk_scss missing from src/frob/lang export policy"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5391"]
labels = ["milestone:v0.534.0", "v1-cluster:D2"]
scope = ["src/frob/lang/__init__.py"]
+++

Found while working T-5382 on dev tip (T-5303 landed the CSS/SCSS walker since): tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols fails for src/frob/lang with ['lang._walk_css.walk_scss'] -- walk_css passes only by accident (the '_walk_css' module-name comment substring-matches 'walk_css'), but 'walk_scss' has no textual mention anywhere in src/frob/lang/__init__.py. Add a mention of walk_scss (e.g. extend the existing _walk_css comment) so frob-exports stops flagging it. Out of T-5382's scope (doctor.py-only) and could not be fixed directly: src/frob/lang/__init__.py is leased by in-progress T-5300.

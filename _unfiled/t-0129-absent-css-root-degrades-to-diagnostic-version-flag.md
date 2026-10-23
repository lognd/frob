+++
id = "01M1T07J41MRGS4WS1KBGWHSSA"
title = "Absent css root degrades to diagnostic; --version flag (r15, A-072)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["crunk:T-0129"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/ingest/walk.py", "src/crunk/app/app.py", "src/crunk/__main__.py", "tests/unit/test_ingest.py", "tests/unit/test_app.py", "tests/system/test_e2e_53_borrower.py", "src/crunk/ingest/models.py", "frob.lock"]

[[acceptance]]
text = "given a borrower tree with TSX and no css root, when check --config runs, then the output carries the absent-css-root diagnostic naming the resolved path plus the TW findings from the TSX"
bound = false

[[acceptance]]
text = "given crunk --version, when run, then it prints the installed version and exits 0 while -v still enables verbose logging"
bound = false
+++

Implement the r15 design: ingest_tree returns Ok with zero sheets plus a diagnostic naming the resolved css root when it does not exist (jsx/tailwind sources still ingest); exists-but-not-a-directory and real OS failures stay Err; the shell renders Unreadable with the resolved path appended; a real --version argparse action while short -v stays verbose.

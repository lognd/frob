+++
id = "01M5AFWSCHGYS13R77HHJBXNSN"
title = "Matrix gap: a binary artifact and an embedded island cannot be written as mdtest cases for the real pipeline"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T16:28:40Z"
updated = "2026-10-19T16:28:40Z"
+++

Found while working ~42DZ0RZ. The frob corpus runner writes each block as a text file, so a binary cell (non-text bytes) and an island cell (code fenced inside another file) cannot be expressed: TODO001 over a text file named .png still applies, and a rust fence inside markdown is not scanned. Teach the corpus runner a binary block (hex or base64 body) and island scanning, then fill the binary and island cells for COV001, DOC001, DOC002, REF001, TICK006 and TODO001 and delete the matching matrix_gap entries.

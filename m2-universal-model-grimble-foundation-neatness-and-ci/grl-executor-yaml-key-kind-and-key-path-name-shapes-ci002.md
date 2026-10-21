+++
id = "01M5ETB80YYSQNEDP9PG86WKD4"
title = "GRL executor: YAML key kind and key(path=, name=) shapes (CI002)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T08:48:17Z"
updated = "2026-10-21T08:48:17Z"
labels = ["area:grl"]
+++

Found while working ~ACSP6CZ. CI002 fails with Exec(UnsupportedKind{kind: key}): the YAML adapter does not expose a key kind with path/name fields to the executor. Needed for CI002 examples; then delete KNOWN_ENGINE_GAPS entries.

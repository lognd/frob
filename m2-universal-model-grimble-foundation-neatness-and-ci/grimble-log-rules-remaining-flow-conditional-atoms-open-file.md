+++
id = "01M6SGZYFK85YEPA1TVKGBAD9H"
title = "Grimble LOG rules: remaining flow-conditional atoms (open file handles, os.open flags, Path.write_text, js .pipe on local streams, cs TextWriter, rust write handle flow)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-11-06T22:52:11Z"
updated = "2026-11-12T12:30:03Z"
scope = ["crates/grimble-check/src/log/**"]
+++

split from ~T3JQNPF: std-stream sinks landed (json.dump/csv.writer/shutil); remaining needs local file-handle flow tracking and advisory-severity decisions

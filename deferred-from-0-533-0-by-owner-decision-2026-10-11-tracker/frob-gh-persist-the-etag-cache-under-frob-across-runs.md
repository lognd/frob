+++
id = "01M4839AREKAZVDVSFP9X8NB5R"
title = "frob-gh: persist the ETag cache under .frob/ across runs"
type = "task"
category = "todo"
priority = "low"
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-06T07:54:09Z"
updated = "2026-10-06T07:54:09Z"
scope = ["crates/frob-gh/**"]

[[acceptance]]
text = "a second client over the same store sends If-None-Match recorded by the first (fixture test)"
bound = false

[[acceptance]]
text = "a corrupt store file is reported and ignored, never fatal"
bound = false
+++

Deferred by ~YNC30Q8: frob-gh's conditional-GET cache is in memory only; mirror.md says ETags are cached in .frob/. Add a caller-supplied store (file-backed in .frob/, keyed by URL, atomic writes via gob-fs) so a second mirror run sends If-None-Match from the first run's responses.

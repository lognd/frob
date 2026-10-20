+++
id = "01M4DVX1K76X876W0YPB5EX3F9"
title = "crunk: wire the Tailwind runtime into crunk doctor and the engine choice (--static, [tailwind] engine) into check and ingest"
type = "story"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-08T13:40:33Z"
updated = "2026-10-08T13:40:33Z"
labels = ["area:crunk"]
scope = ["crates/crunk/src/doctor.rs,crates/crunk-spec/src/table.rs,crates/crunk-check/src/**"]
+++

Found while working ~1WS0DQ4 and ~ZZCCYHY: Runtime::doctor (presence table) and ingest_tailwind(Engine) exist but nothing calls them. crunk doctor should print the table; [tailwind] engine = static and --static should select Engine::Static; crunk check should construct the Runtime (state dir, cache, notice sink to stderr) and pass it to ingest. Reason code unresolved-by-tailwind maps to UnresolvedReason::Opaque for the TW rules (~BWK6MXR).

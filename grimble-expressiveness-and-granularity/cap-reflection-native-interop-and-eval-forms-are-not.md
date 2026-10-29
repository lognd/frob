+++
id = "01M64230AR8DHJZY9QQS3EC85S"
title = "CAP: reflection, native interop and eval forms are not reported"
type = "task"
category = "todo"
priority = "critical"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:47:39Z"
updated = "2026-10-29T23:00:00Z"
idempotency_key = "vnvd3q1-reflect-ffi"
scope = ["crates/grimble-check/**", "crates/gob-symbols/**", "crates/gob-caps/**"]

[[acceptance]]
text = "C# reflection and DllImport, Rust extern blocks and libc calls, fn-pointer transmute, inline asm, JS require/eval/Function with computed names yield capability findings or Unresolved"
bound = false
+++

Cases c01 c02 r07 r08 r11 r22 t02. symbol-resolved fix required (binding/import resolution, not text matching); pin case as regression test; unresolvable forms must report Unresolved, never pass silently

+++
id = "01M64ZYSQNZY51971GJ1232TXR"
title = "CAP: Python ctypes and cffi native interop are not reported as ffi"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T23:29:39Z"
updated = "2026-11-16T22:01:36Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "Given Python code calling ctypes.CDLL/cffi dlopen, when scanned, then an ffi use is reported"
bound = false
+++

found while working S3EC85S: ffi vocab covers C#, Rust and TS only

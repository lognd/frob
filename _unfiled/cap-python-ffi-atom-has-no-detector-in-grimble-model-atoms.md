+++
id = "01M65MN88MGXA6GBSVG5NA4SG2"
title = "CAP: Python ffi atom has no detector in grimble-model atoms"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T05:31:26Z"
updated = "2026-10-30T05:31:26Z"
scope = ["crates/grimble-model/**"]
+++

found while working ~R269X33: ffi vocab for ctypes is registered but atoms.rs has only a rust ffi detector, so Python ctypes loads never fire; also cffi/dlopen.

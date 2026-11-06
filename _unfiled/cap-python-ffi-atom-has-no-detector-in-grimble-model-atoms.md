+++
id = "01M65MN88MGXA6GBSVG5NA4SG2"
title = "CAP: Python ffi atom has no detector in grimble-model atoms"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T05:31:26Z"
updated = "2026-11-06T21:42:57Z"
scope = ["crates/grimble-model/**", "packs/core-effects/**"]

[[acceptance]]
text = "Python ctypes, cffi and dlopen loads are named by the ffi vocab"
bound = true
+++

found while working ~R269X33: ffi vocab for ctypes is registered but atoms.rs has only a rust ffi detector, so Python ctypes loads never fire; also cffi/dlopen.

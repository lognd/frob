+++
id = "01M4HNYRZA7ASMMR6388BJN9BQ"
title = "land.rs follow-ups: sweep old *.removing leftovers synchronously at the start of land cleanup, and advance the base ref by CAS without touching the primary checkout's index unless the base is checked out there"
type = "bug"
category = "todo"
priority = "medium"
points = 2
parent = "01M4GRTA9XBJCM2RY98HWZXYC7"
reporter = "lognd"
created = "2026-10-10T01:13:36Z"
updated = "2026-10-10T01:13:36Z"
scope = ["crates/frob-land/src/land.rs", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4GRV9YMN2VEPCTMMD5ZJPVH"

[[acceptance]]
text = "Given leftover *.removing dirs, when frob land runs, then they are deleted before its own cleanup"
bound = false

[[acceptance]]
text = "Given another writer holding the primary's index.lock, when land advances experimental (not checked out in the primary), then the ref moves by compare-and-swap without waiting on the index"
bound = false
+++

Deferred from ~SVTM10F and ~W7NXA6R because ~D5ZJPVH held land.rs.

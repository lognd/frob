+++
id = "01M65CP89D8SVGTT2407NZ7K9G"
title = "LOG: JS .constructor(...) Function-constructor chains are not reported"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T03:12:10Z"
updated = "2026-11-17T07:09:28Z"
scope = ["crates/grimble-check/**"]
+++

Found while working CS763EX. e.g. (()=>{}).constructor('...')() evades the dynamic-code check.

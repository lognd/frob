+++
id = "01M3ZVQA77ZEK9DXEN5Z0XMZEG"
title = "gob-symbols: unknown-receiver calls get May edges only within the caller's crate"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T03:08:03Z"
updated = "2026-10-03T03:24:20Z"
idempotency_key = "m2-gobsym-crosscrate-poison"
labels = ["milestone:2", "soundness"]
scope = ["crates/gob-symbols/**", "crates/frob-obligations/**"]

[[acceptance]]
text = "Given crate A depending on crate B, both defining a self method m with the same arity, when A calls x.m() on an unknown receiver, then both A::m and B::m get May edges and neither is reported Covered by that call alone"
bound = true
+++

Found by ~S404RDJ (pre-existing). An unknown-receiver call x.m() gets May edges only to same-named methods in the caller's own crate; a same-named method in another crate (a dependency) is not poisoned when the caller's crate also has one, because candidates come only from the caller's crate. This can make COV001 report a callable as reached-by-no-test or Covered incorrectly: a soundness hole against universal-model.md honesty (P+ rules must never pass on an unproven fact). Fix: candidates for an unknown receiver include same-named self-taking methods with matching arity in every crate the caller's crate depends on (transitively, through CrateDeps); accept the resulting rise in Unresolved. Add a soundness test with two crates each defining m.

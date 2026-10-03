+++
id = "01M40T3VA5Y86ZQH234NTKAXC1"
title = "SCOPE001 reports untouched file symlinks as changed, blocking every land"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:59:11Z"
updated = "2026-10-03T12:26:27Z"
idempotency_key = "m2-rel-scope-symlinks"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-check/**", "crates/gob-git/src/status.rs", "crates/gob-git/tests/**", "changelog.d/01M40T3VA5Y86ZQH234NTKAXC1.*.md"]

[[acceptance]]
text = "Given a repository with untouched file and directory symlinks and core.autocrlf=true, when frob check --ticket runs, then no symlink is reported as changed"
bound = true

[[acceptance]]
text = "Given a symlink whose target was changed on the branch, when check runs, then it is reported"
bound = true
+++

Reported from the cloc repository (FROB_FEEDBACK.md items 3, 3a): the repository has 11 symlinks (mode 120000); exactly the 6 that point at files are reported by branch_changes (crates/frob-check/src/scope.rs, diff_names(merge_base, WorkTree)) although git diff and git status show nothing; directory symlinks are not reported. The repository has core.autocrlf=true (WSL). Likely the worktree side follows file symlinks and compares the target content with the link blob (a symlink's blob is its target path). Fix: the worktree comparison must treat a symlink as a symlink (compare the link target string, as git does), honour core.autocrlf and filters the way git status does (or use gix's status machinery for the worktree side), and never report a path git does not report. Tests: a temp repo with file and directory symlinks (relative and absolute targets), with and without core.autocrlf, no changes: zero changed paths; changing a link target: reported.

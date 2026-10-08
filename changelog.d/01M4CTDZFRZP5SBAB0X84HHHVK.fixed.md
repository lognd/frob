gob-git: a ledger commit whose checkout sync lost the race to a later writer now skips paths whose tip blob has moved on, so the worktree and index follow HEAD instead of regressing (audit M3).

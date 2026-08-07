---
id: T-1058
title: 'coordinator: decide worktree.baseRef=head or push-main-before-dispatch policy'
state: done
kind: docs
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:python3 -c "import json,sys; sys.exit(0 if json.load(open('.claude/settings.json'))['worktree']['baseRef']=='head'
  else 1)" exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
T-1030 traced the stale-worktree-base incidents to the EnterWorktree
harness tool's default worktree.baseRef=fresh, which branches new
worktrees from origin/<default-branch> rather than local HEAD. In this
clone, origin/main is far behind local main (never pushed, 81 commits
behind at investigation time), so every fresh EnterWorktree cut lands on
the stale origin tip.

This is a settings.json change (worktree.baseRef: "head", or pushing
main to origin regularly to keep it in sync), not a frob code or docs
change, and not something this agent should apply silently mid-ticket.
Filed so a coordinator/user can decide: either flip worktree.baseRef to
"head" in .claude/settings.json, or adopt a habit of pushing local main
to origin before dispatching a wave, or both.
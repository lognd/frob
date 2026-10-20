#!/bin/sh
# Session-start hook: refresh the ticket ledger view in the foreground (3 s budget) so the agent starts
# with current claims, evictions and conflicts. Never fails the session; silent when frob is absent.
command -v frob >/dev/null 2>&1 || exit 0
if command -v timeout >/dev/null 2>&1; then
  timeout 3 frob refresh --quiet 2>&1 || true
else
  frob refresh --quiet 2>&1 || true
fi
exit 0

# Freshness hooks

Keep the local view of the ticket ledger current without remembering to run anything
(`docs/design/distributed-tickets.md`, section 5.4).

## Git hooks

`frob init` installs `post-checkout` and `post-merge` hooks in the repository's common hooks
directory. Each carries one marked block that runs `frob refresh --background --quiet` and returns at
once. The block is skipped when `CI` or `FROB_SYNC_INNER` is set (frob's own pushes) and while a rebase
is in progress, and it never fails the git operation. There is deliberately no `pre-push` hook.

- Idempotent: rerunning `frob init` leaves an up-to-date hook byte-identical.
- Your own hook lines are kept; frob only edits the block between its two marker lines.
- Reversible: `frob init --remove-hooks` strips the block and deletes a hook file frob alone wrote.
- A custom `core.hooksPath` is not followed; copy the block there by hand.

## Agent session start

`frob agent sync` registers every `hook:` item declared under `[agent]` in `frob.toml`. This repository
declares `scripts/claude-hooks/frob-refresh.sh` on `SessionStart`: it runs `frob refresh --quiet` in the
foreground under a 3 second budget and prints what it finds to the agent.

```toml
[agent]
items = ["hook:frob-refresh = scripts/claude-hooks/frob-refresh.sh"]
hooks = ["frob-refresh:SessionStart:"]
```

## Loops and cron

Run `frob refresh --quiet` and branch on its exit code. `CI` disables background sync, so the hooks do
nothing in a pipeline.

```cron
*/10 * * * * cd /path/to/repo && frob refresh --quiet
```

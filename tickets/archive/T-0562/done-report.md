## Done report

Found while working T-0459: T-0461's render-migration edits to bind/dup/
mutate/perf/release/stats/sys/vet runner functions never got a `frob:ticket`
edge, so `frob check --ticket <other>`'s COV002 fires once T-0461 closed
(scope-grace via an open ticket's declared scope only covers OPEN tickets,
and T-0461 is now done). Added `# frob:ticket T-0562` above every touched
symbol in those eight files so COV002 resolves without reopening T-0461.
No behavior change -- comment-only.

### Changed
```
 src/frob/app/bind_runner.py    | 15 ++++++----
 src/frob/app/dup_runner.py     |  6 +++-
 src/frob/app/mutate_runner.py  |  9 ++++--
 src/frob/app/perf_runner.py    | 19 ++++++++----
 src/frob/app/release_runner.py |  9 ++++--
 src/frob/app/stats_runner.py   | 11 ++++---
 src/frob/app/sys_runner.py     | 14 +++++++--
 src/frob/app/vet_runner.py     | 51 ++++++++++++++++++++------------
 tickets.md                     | 66 ++++++++++++++++++++++++++++++++++++++++--
 9 files changed, 156 insertions(+), 44 deletions(-)
```

### Evidence
(no evidence recorded)

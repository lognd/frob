+++
id = "01M3ZX849P4N1DKVA8EEZ7YDV9"
title = "Mirror CI job: single writer from the default branch workflow"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:34:43Z"
idempotency_key = "m2-mirror-ci-job"
labels = ["milestone:2", "area:mirror"]
scope = [".github/workflows/mirror.yml"]

[[links]]
kind = "blocked-by"
target = "01M3ZX845P69N8FQXVAD08W4A6"

[[acceptance]]
text = "Given the workflow, when linted by zizmor and actionlint, then no finding is reported"
bound = false

[[acceptance]]
text = "Given a push to a non-ledger branch, when evaluated, then the job does not run"
bound = false
+++

Implements mirror.md section 3 (who runs it); security.md section 2.11.

Triggered by pushes to the protected ledger ref, defined on the default branch, with a least-scope token (issues write on one project); pinned actions, explicit permissions and timeout per cicd.md.

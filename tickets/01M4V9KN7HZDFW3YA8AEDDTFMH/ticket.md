+++
id = "01M4V9KN7HZDFW3YA8AEDDTFMH"
title = "Reproduce the dev tag-move 403 on a throwaway ref"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-13T18:50:13Z"
updated = "2026-10-13T18:50:13Z"
scope = ["docs/design/build-test-ci.md"]
+++

found while working ~J6DA5EV: needs gh write access to create a throwaway tag whose update carries a .github/workflows change, with GITHUB_TOKEN; not done safely from an agent. Confirms the cause recorded in build-test-ci.md.

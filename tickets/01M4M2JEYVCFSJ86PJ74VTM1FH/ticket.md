+++
id = "01M4M2JEYVCFSJ86PJ74VTM1FH"
title = "CI uploads the nextest junit report as an artifact when the nextest step fails, so failing tests can be read without log access"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-10T23:32:33Z"
updated = "2026-10-11T03:32:33Z"
scope = [".github/workflows/ci.yml"]

[[acceptance]]
text = "the rust job uploads target/nextest/ci/junit.xml with if: failure() or always() and a pinned action sha, covered by the workflow lint tests"
bound = true
+++

found while driving CI green: the Windows nextest failure could not be diagnosed because job logs are unreachable through the agent proxy and no artifact carries the failing test names. .config/nextest.toml already writes junit.xml for the ci profile.

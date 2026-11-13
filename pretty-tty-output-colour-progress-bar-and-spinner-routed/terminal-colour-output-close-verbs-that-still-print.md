+++
id = "01M7AYMF3066GKHWVPQ40XY7XH"
title = "Terminal colour output: close verbs that still print uncoloured rows on a TTY (W1GQTPG acceptance gap)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XMN7Z3TWMW8YMGVE2QBC17"
reporter = "lognd"
created = "2026-11-13T17:17:40Z"
updated = "2026-11-13T17:28:52Z"
labels = ["no-story"]
scope = ["crates/frob/src/pretty.rs", "crates/frob/src/**"]

[[acceptance]]
text = "given a TTY with TERM=xterm, when each verb family (ticket, lease, cycle, release, milestone, rule, check, land, work, test) runs with --text, then ids, status words and headings carry ANSI styling via pretty::Theme, and one test per family asserts it"
bound = true

[[acceptance]]
text = "given NO_COLOR, TERM=dumb or a pipe, then output stays byte-identical to the plain rows"
bound = true
+++

Owner reports terminal colour output does not match the W1GQTPG acceptance (every verb coloured and aligned). Spot check on a pty: rule list emits styling on 1 line only. Audit each verb family on a pty, list the gaps, route them through Theme::decorate, add a test per family.

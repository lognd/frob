+++
id = "01M5XMN7Z3TWMW8YMGVE2QBC17"
title = "Pretty TTY output: colour, progress bar and spinner, routed through logging"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-27T02:57:30Z"
updated = "2026-10-27T02:57:30Z"
+++

Owner request 2026-10-26: model on lognd/clocx (ratatui 0.30 + anstyle + tracing/tracing-subscriber). On a TTY every frob command gets coloured, well-formatted output and long-running verbs (land, check, work, test) show a progress bar or throbber with stage timings. Piped output stays the JSON envelope; NO_COLOR and non-TTY disable all decoration. All human output is routed through the logging layer, not println.

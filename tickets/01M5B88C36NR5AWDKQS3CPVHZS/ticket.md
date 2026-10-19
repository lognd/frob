+++
id = "01M5B88C36NR5AWDKQS3CPVHZS"
title = "frob mirror recreate: switch CurlTransport to frob_mirror::github::http::NativeTransport and drop the curl config plumbing"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T23:34:26Z"
updated = "2026-10-19T23:34:26Z"
scope = ["crates/frob/src/mirror_recreate_cmd.rs"]
+++

found while working ~P4A6YB2: NativeTransport now exists; replace CurlTransport, parse_response, curl_quote, write_private_config use, and update docs/design/mirror.md line ~296 ('curl transport').

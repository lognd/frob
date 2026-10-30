+++
id = "01M65CP8BAY8R4SSVGY7TED887"
title = "LOG: JS import('x').then(cb) callbacks are not followed"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T03:12:10Z"
updated = "2026-10-30T03:12:10Z"
scope = ["crates/grimble-check/**"]
+++

Found while working CS763EX. Dynamic import resolved only for direct await/assignment forms.

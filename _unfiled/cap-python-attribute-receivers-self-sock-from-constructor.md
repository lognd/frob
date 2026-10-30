+++
id = "01M65JKTKG95V20BG9SQZ5SJDH"
title = "CAP: Python attribute receivers (self.sock) from constructor assignments are not typed"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T04:55:42Z"
updated = "2026-10-30T04:55:42Z"
scope = ["crates/gob-symbols/**", "crates/grimble-bind/**"]
+++

Follow-up of BG4T2RC: self.sock = socket.socket() in __init__ then self.sock.connect() elsewhere reports only May (unresolved).

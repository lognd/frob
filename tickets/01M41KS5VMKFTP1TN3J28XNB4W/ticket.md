+++
id = "01M41KS5VMKFTP1TN3J28XNB4W"
title = "ticket update --remove-acceptance renumbers criteria and silently rebinds evidence to the wrong criterion"
type = "bug"
category = "todo"
priority = "critical"
points = 3
reporter = "lognd"
created = "2026-10-03T19:27:45Z"
updated = "2026-10-03T19:28:15Z"
scope = ["crates/frob-ledger/**", "crates/frob-evidence/**", "crates/frob/src/ticket/**", "crates/frob/tests/ticket.rs"]

[[acceptance]]
text = "Given evidence bound to criterion 2 of 3, when criterion 1 is removed, then that evidence binds the new criterion 1 (the same text) and nothing else"
bound = false

[[acceptance]]
text = "Given evidence bound to criterion 1, when criterion 1 is removed and a new criterion is added, then the new criterion is unbound and the removed one's evidence is reported as lost"
bound = false

[[acceptance]]
text = "Given the ticket and milestone criterion paths, when the moved map is applied, then both call the same function"
bound = false
+++

Reported by goway: removing criterion 1 on a ticket whose evidence is bound to criterion 2 made that evidence count for the new criterion 1, and the next added criterion landed unbound. Evidence is the proof of done, so a silent rebinding is an integrity bug. Milestones already solve this: milestone criterion remove records a moved map (old position to new, 0 when removed) so evidence follows its criterion (releases.md). Apply the same to tickets: --remove-acceptance (and --clear-acceptance) record the moved map in the update event, the evidence fold resolves each record's accepts through every later moved map, evidence for a removed criterion is reported as lost (as today) and no longer counts, and show/brief/close guards all use that one resolution. Reuse the milestone implementation rather than writing a second one; if it lives in a milestone-only module, move it to a shared place. Old ledgers without moved maps keep their current meaning.

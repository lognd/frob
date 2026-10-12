## Stop 4: the rules that guard the repository

`{{frob}} check` runs the built-in rules and the tool stages configured for this repository; `{{frob}} check --ticket ~HANDLE` scopes the run to one ticket. Evidence must be bound to every acceptance item before `{{frob}} land` accepts a ticket. The field and state vocabulary is in the [glossary](GLOSSARY.md).

# The --good-first flag

Status: current
Owner: frob
Decisions: none
Audience: user

`frob ticket new --good-first` files a ticket meant for newcomers. It labels
the ticket `good-first` and appends a `## Start here` scaffold to the body, so
a first-time contributor knows where to begin.

```bash
frob ticket new --title "Fix a typo in the quickstart" --good-first
```

The scaffold lists:

- Files to read first
- Test command
- Who to ask

Fill these in before handing the ticket off. Run `frob ticket new --help` for
the authoritative description of the flag.

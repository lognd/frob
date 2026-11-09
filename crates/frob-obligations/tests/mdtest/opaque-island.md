<!-- mdtest: rule=DOC001 -->
# DOC001 over the opaque islands of lexical rules

A lexical rule (`TICK004`, `TICK005`) reads an opaque island's text; DOC001, a structural rule,
cannot, so it is Unresolved over the same island. `gob_mdtest::opaque` pairs the cases below with
the lexical fires in `crates/frob-check/tests/mdtest/` by `region=` and an identical heading path,
which is why the two headings below repeat those files' titles verbatim.

## Controls

```rust expect=fire
pub fn bare() {} // warn: DOC001
```

```rust expect=clean
/// Documented.
pub fn documented() {}
```

# TICK004 home path in a committed ticket

## A fire inside an opaque island still fires

```text expect=unresolved region=notes file=notes.xyz
See /home/someone/projects/secret for the notes.
```

# TICK005 private term in a committed ticket

## A fire inside an opaque island still fires

```text expect=unresolved region=notes file=notes.xyz
Talk to the hush-term team.
```

# TODO001 bare work markers

## A fire inside an opaque island still fires

```text expect=unresolved region=notes file=notes.xyz
TODO this file is never scanned
```

<!-- mdtest: rule=TICK004 -->
# TICK004 home path in a committed ticket

The block is the body of a ticket committed to the ledger.

## A body naming a home directory fires

```text expect=fire
See /home/someone/projects/secret for the notes.
```

## A body with no machine path is clean

```text expect=clean
See the notes in the repository.
```

## A fire inside an opaque island still fires

The rule reads only text, so an opaque region does not hide the offender.

```text expect=fire cell=island
See /home/someone/projects/secret for the notes.
```

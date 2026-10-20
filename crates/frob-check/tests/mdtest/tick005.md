<!-- mdtest: rule=TICK005 -->
# TICK005 private term in a committed ticket

The local privacy rules define the private term `hush-term`; the block is the
body of a ticket committed to the ledger.

## A body containing the private term fires

```text expect=fire
Talk to the hush-term team.
```

## A body without it is clean

```text expect=clean
Talk to the platform team.
```

## A fire inside an opaque island still fires

The rule reads only text, so an opaque region does not hide the offender.

```text expect=fire cell=island
Talk to the hush-term team.
```

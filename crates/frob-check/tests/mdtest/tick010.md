<!-- mdtest: rule=TICK010 -->
# TICK010 a .github tree on the ticket branch

## An extra workflow fires

```text expect=fire
add .github/workflows/ci.yml
```

## An edited nudge workflow fires

```text expect=fire
edited-nudge
```

## The generated nudge alone is clean

```text expect=clean
nudge
```

## A branch without .github is clean

```text expect=clean
none
```

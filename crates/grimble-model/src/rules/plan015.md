<!-- mdtest: rule=PLAN015 -->
# PLAN015 plan-sorry-hole

A `sorry` hole stands in for a scenario tail.

## What it does

Every `sorry` is flagged once, at the keyword, naming the scenarios that include the enclosing scenario and so inherit the debt.

## Why it matters

A sorry is a declared, tracked gap; the finding keeps the debt visible until it is paid.

## Remedy

Replace the `sorry` with the real chain.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;

  scenario t {
    u.go -> sorry because="later";
  }
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;

  scenario t {
    u.go -> end ok;
  }
}
```

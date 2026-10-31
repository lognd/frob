<!-- mdtest: rule=PLAN008 -->
# PLAN008 plan-page-unreachable

A page cannot be reached from an entry page.

## What it does

Fires per page that is not an entry and is not reachable by `from` navigation from an entry page, and per impl whose `on page` target is outside that reachable set. Reported as Error: the rule table lists Warn, but the severity model has no Warn.

## Why it matters

A user can never navigate to an unreachable page, so every step planned on it is unreachable too.

## Remedy

Mark a page `entry`, or add the missing `from` navigation edge that reaches it.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
page home { ui = "src/lib.rs::run"; }
```

### Clean case 2

```grmb expect=clean file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
page home { entry; ui = "src/lib.rs::run"; }
page cart { from home; ui = "src/lib.rs::run"; }
```

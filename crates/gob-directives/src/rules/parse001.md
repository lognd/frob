<!-- mdtest: rule=PARSE001 -->
# PARSE001 malformed-directive

A `frob:` directive is malformed: unterminated quote, bad key, missing or invalid argument.

## What it does

The scanner never silently drops a directive line it recognises by namespace; if the arguments cannot be read into the verb's declared shape the finding points at the exact offending token.

## Why it matters

Without the finding, a typo in a directive would silently disable the claim, acceptance or ticket link it was meant to carry.

## Remedy

Fix the directive text so it matches `<namespace>:<verb> <args>` with `key=value` or `key="quoted value"` pairs.

## Examples

### Fires case 1

```rust expect=fire
/* frob:accept COV006 */ // error: PARSE001
fn a() {}
```

### Clean case 1

```rust expect=clean
/* frob:accept COV006 because=ok */
fn a() {}
```

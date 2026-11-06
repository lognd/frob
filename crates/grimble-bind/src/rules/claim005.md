<!-- mdtest: rule=CLAIM005 -->
# CLAIM005 taint-secret-env

A secret environment variable reaches a print, log or HTTP sink without a declassify symbol.

## What it does

Opt-in: runs only when some node declares `provides secret.declassify via SEL;`. In Python and Rust files a name assigned from a secret-named environment read (`API_TOKEN`, `DB_PASSWORD`, anything containing KEY, SECRET, TOKEN, PASSWORD or CREDENTIAL) is tainted; taint follows plain assignments inside one function. A print, log or HTTP call whose arguments use a tainted name, or read the secret inline, fires. A value passed through a symbol the `via` selector picks is clean. Unresolved when the code is owned only at `may`.

## Why it matters

A secret in a log line or a request URL outlives the process that held it, and review rarely spots the one print that leaks it.

## Remedy

Pass the value through the declared declassify symbol (a redactor), or stop emitting it.

## Examples

### Fires case 1

`src/x.py` reads `API_TOKEN` into `tok` and calls `print(tok)`.

```grmb expect=fire file=design/m.grmb config="taint"
grimble = "2";
module m;

node a : trusted {
  owns "src/x.py";
  provides secret.declassify via "src/x.py::redact" because="the redactor";
}
node d : trusted {
  owns "design/**";
}
```

### Clean case 2

`src/x.py` calls `print(redact(tok))` instead.

```grmb expect=clean file=design/m.grmb config="taintok"
grimble = "2";
module m;

node a : trusted {
  owns "src/x.py";
  provides secret.declassify via "src/x.py::redact" because="the redactor";
}
node d : trusted {
  owns "design/**";
}
```

<!-- mdtest: rule=TOOL002 -->
# TOOL002 tool finding with no frob rule

Each block is the JSON the bound linter prints.

## A finding whose id maps to no rule fires

```json expect=fire
[{"ident":"no-such-id","desc":"unmapped","locations":[{"symbolic":{"key":{"Local":{"verbatim_path":"./.github/workflows/ci.yml"}},"annotation":"here","kind":"Primary"},"concrete":{"location":{"offset_span":{"start":10,"end":20}}}}]}]
```

## A linter that reports nothing is clean

```json expect=clean
[]
```

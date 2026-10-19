<!-- mdtest: rule=PARSE002 -->
# PARSE002 directive matched lexically

## Hash comment in a file with no grammar

```caddy expect=fire file=site.caddy
// advisory: PARSE002
# frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2
route /api
```

## Clean: no directive in a file with no grammar

```caddy expect=clean file=site.caddy
# an ordinary comment that mentions frob in prose
route /api
```

## Clean: a parsed language never reports lexically

```rust expect=clean
// frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2
fn a() {}
```

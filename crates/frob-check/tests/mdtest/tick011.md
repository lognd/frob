<!-- mdtest: rule=TICK011 -->
# TICK011 the ledger branch allows a force push or deletion

The block is the hosting API's reply to the branch-protection read: `<status> <body>`, or `unreachable`
when no reply was obtained.

## Force pushes allowed fires

```text expect=fire
200 {"allow_force_pushes":{"enabled":true},"allow_deletions":{"enabled":false}}
```

## Deletion allowed fires

```text expect=fire
200 {"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":true}}
```

## A branch without protection fires

```text expect=fire
404 {"message":"Branch not protected"}
```

## Both forbidden is clean

```text expect=clean
200 {"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":false}}
```

## Unresolved when the token cannot read protection

```text expect=unresolved
403 {"message":"Resource not accessible"}
```

## Unresolved when the API is unreachable

```text expect=unresolved
unreachable
```

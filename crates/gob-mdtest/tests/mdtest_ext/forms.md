<!-- mdtest: rule=MDT001 -->
# Marker forms

## column and message

```rust expect=fire
let a = 1;
let b = forbidden; // error: [9] MDT001 "forbidden w"
let c = (forbidden); // error: [10] MDT001
let d = forbidden; // error: MDT001 "word"
```

## bare marker uses the default rule

```rust expect=fire
let a = forbidden; // error:
let b = forbidden; // error: [9]
let c = forbidden; // error: "forbidden"
```

## own-line and stacked markers

```rust expect=fire
let a = 1;
// error: [9] MDT001
let b = forbidden;
// error: [9] "first"
// error: [9] "second"
let c = twice;
```

## unresolved

```rust expect=fire
let b = unsure; // unresolved[hole]: [9] "undecided"
let c = unsure_req; // unresolved[hole, required]: MDT001
let d = unsure; // unresolved: MDT001
```

## clean

```rust expect=clean
let ok = allowed;
```

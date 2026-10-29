<!-- mdtest: rule=PROC002 -->
# PROC002 print macro outside the presenter crates

Only crates listed in `[check] output_presenters` may print to stdout or stderr.

## A println in an unlisted crate fires

```text expect=fire
=== frob.toml
[check]
output_presenters = ["present"]
=== crates/other/src/lib.rs
//! Other.
pub fn f() {
    println!("hello");
}
```

## A println in a test module is clean

```text expect=clean
=== frob.toml
[check]
output_presenters = ["present"]
=== crates/other/src/lib.rs
//! Other.
#[cfg(test)]
mod tests {
    fn t() {
        println!("hello");
    }
}
```

## A println-like word in a string is clean

```text expect=clean
=== frob.toml
[check]
output_presenters = ["present"]
=== crates/other/src/lib.rs
//! Other.
pub const S: &str = "println!(x)";
```

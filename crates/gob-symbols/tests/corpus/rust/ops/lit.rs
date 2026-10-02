//! Literals are exact: a token change changes the digest.

pub fn values() -> (i32, &'static str, bool, f64) {
    (42, "text\n", true, 1.5)
}

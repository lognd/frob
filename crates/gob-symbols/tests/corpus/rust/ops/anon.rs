//! Anonymous units: closures and nested fn items.

pub fn make(offset: i32) -> impl Fn(i32) -> i32 {
    fn twice(v: i32) -> i32 {
        v * 2
    }
    move |x| twice(x) + offset
}

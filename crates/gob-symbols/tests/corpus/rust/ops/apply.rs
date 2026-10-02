//! Application: free call, path call, method call, constructor, dynamic call.

pub fn go(v: Vec<u32>, f: fn(u32) -> u32) -> Option<u32> {
    let first = helper(1);
    let made = Builder::new();
    let len = v.len();
    let wrapped = Some(len);
    let _ = f(first);
    let _ = made;
    wrapped
}

fn helper(x: u32) -> u32 {
    x
}

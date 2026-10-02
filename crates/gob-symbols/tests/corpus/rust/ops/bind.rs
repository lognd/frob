//! Binders: let, for, if let, while let and match arms scope over what they cover.

pub fn run(items: Vec<Option<u32>>) -> u32 {
    let mut total = 0;
    for item in items {
        if let Some(v) = item {
            total += v;
        }
        match item {
            Some(n) if n > 1 => total += n,
            _ => {}
        }
    }
    total
}

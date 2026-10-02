//! References: parameters and let bindings resolve lexically, shadowing hides.

pub fn pick(a: u32, b: u32) -> u32 {
    let c = a + b;
    let c = c + 1;
    free_name + c
}

static mut COUNT: u32 = 0;
fn bump() { unsafe { COUNT += 1; } }

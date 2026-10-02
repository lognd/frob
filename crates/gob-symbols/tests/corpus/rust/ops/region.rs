//! Regions: unsafe blocks are boundaries rules care about.

pub fn raw(p: *const u8) -> u8 {
    unsafe { *p }
}

//! Comments are trivia attached to their parent and excluded from digests.

// before the item
pub fn commented() -> u32 {
    // inside the body
    1 /* inline */ + 2
}

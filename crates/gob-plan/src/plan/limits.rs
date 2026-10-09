//! Hard limits applied to every plan, so hostile bytes cannot exhaust memory or stack.

/// Largest plan accepted from disk, in bytes.
pub const MAX_BYTES: usize = 4 * 1024 * 1024;
/// Most ops in the arena.
pub const MAX_OPS: usize = 1 << 16;
/// Most strings in the pool.
pub const MAX_STRINGS: usize = 1 << 14;
/// Longest string, in bytes (regex size limits at load, security.md 2.5).
pub const MAX_STR_LEN: usize = 4096;
/// Most variable slots.
pub const MAX_VARS: usize = 1024;
/// Most clauses, reports, prefilter entries or language entries.
pub const MAX_LIST: usize = 1 << 12;
/// Deepest op nesting.
pub const MAX_DEPTH: u32 = 64;
/// Largest `within` bound of a `reaches`.
pub const MAX_WITHIN: u16 = 1024;
/// Longest pack name.
pub const MAX_PACK_NAME: usize = 64;
/// Most defs.
pub const MAX_DEFS: usize = 1 << 10;
/// Most parameters or arguments of one def.
pub const MAX_PARAMS: usize = 32;

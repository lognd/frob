//! Size bounds applied to every manifest field, and the owner record used by
//! cross-pack checks.

/// Largest manifest file accepted, in bytes.
pub const MAX_MANIFEST_BYTES: usize = 64 * 1024;
/// Longest pack name (packs.md 2.2: kebab-case, max 40).
pub(crate) const MAX_NAME: usize = 40;
/// Longest version string.
pub(crate) const MAX_VERSION: usize = 64;
/// Most families one pack may own.
pub(crate) const MAX_FAMILIES: usize = 64;
/// Longest family prefix (letters only).
pub(crate) const MAX_FAMILY: usize = 8;
/// Most entries in `needs`.
pub(crate) const MAX_NEEDS: usize = 32;
/// Longest version requirement in `needs`.
pub(crate) const MAX_REQ: usize = 64;
/// Most entries in one `provides` list.
pub(crate) const MAX_LIST: usize = 256;
/// Longest path or glob in `provides`.
pub(crate) const MAX_PATH: usize = 256;
/// Most effect keys.
pub(crate) const MAX_EFFECTS: usize = 64;
/// Most grants per effect key.
pub(crate) const MAX_GRANTS: usize = 256;
/// Longest effect key or grant.
pub(crate) const MAX_GRANT: usize = 256;

/// One pack seen by a cross-pack check: its manifest file and declared name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Owner {
    /// The manifest file the pack was loaded from.
    pub file: String,
    /// The pack's declared name.
    pub name: String,
}

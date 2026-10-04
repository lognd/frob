//! Free disk space of the volume holding a path (the disk guard's input).
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::Path;

/// Free bytes available to an unprivileged process on the volume of `path`, or `None` when unknown.
#[cfg(unix)]
pub fn free_bytes(path: &Path) -> Option<u64> {
    match nix::sys::statvfs::statvfs(path) {
        #[allow(clippy::useless_conversion)]
        // the statvfs field widths differ per platform (u32 or u64)
        Ok(s) => {
            let free = u64::from(s.blocks_available()).saturating_mul(u64::from(s.fragment_size()));
            tracing::debug!(path = %path.display(), free, "free space read");
            Some(free)
        }
        Err(e) => {
            tracing::warn!(path = %path.display(), error = %e, "free space unavailable");
            None
        }
    }
}

/// Free space is not measured on this platform, so the guard never forces a pass.
#[cfg(not(unix))]
pub fn free_bytes(path: &Path) -> Option<u64> {
    tracing::debug!(path = %path.display(), "free space is not measured on this platform");
    None
}

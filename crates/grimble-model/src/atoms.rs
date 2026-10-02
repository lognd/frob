//! Capability atoms this crate adds to the shared registry (grmb-spec 4.1, grimble-model.md 9.6).
//!
//! `gob-ir` registers `net.connect` and `fs.write`; the remaining core atoms named by the
//! worked example are submitted here so a model that links this crate resolves them.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use gob_ir::registry::{AtomEntry, DetectorEntry, DetectorKind};

inventory::submit! {
    AtomEntry {
        name: "fs.read",
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

inventory::submit! {
    AtomEntry {
        name: "exec",
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

inventory::submit! {
    AtomEntry {
        name: "net.listen",
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

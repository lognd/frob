//! Capability atoms this crate adds to the shared registry (grmb-spec 4.1, grimble-model.md 9.6).
//!
//! `gob-ir` registers `net.connect` and `fs.write`; the remaining core atoms named by the
//! worked example, and the callee vocabularies the capability rules observe them by, are
//! submitted here so a model that links this crate resolves them.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV

use gob_ir::registry::{AtomEntry, DetectorEntry, DetectorKind, VocabEntry};

inventory::submit! {
    AtomEntry {
        name: "fs.read",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

inventory::submit! {
    AtomEntry {
        name: "process.spawn",
        aliases: &["exec"],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

inventory::submit! {
    AtomEntry {
        name: "net.listen",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

// The parent `fs` has no detector of its own: a grant of it covers `fs.read` and `fs.write`.
inventory::submit! {
    AtomEntry {
        name: "fs",
        aliases: &[],
        detectors: &[],
    }
}

inventory::submit! {
    AtomEntry {
        name: "process.env",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "process.env", names: &["os.getenv", "os.putenv", "os.environ.get"] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "process.env", names: &["env::var", "env::var_os", "env::vars", "env::set_var"] }
}

// The observed-use vocabularies of the capability rules (binding.md 7.2): one class per atom,
// named by the atom. A leading `.` is a method name matched on any receiver; `grimble-bind`'s
// `caps` gates it on a companion call so a bare `.listen` is not a use by itself.
inventory::submit! {
    VocabEntry { lang: "python", kind: "fs.read", names: &["open", "io.open", "os.listdir", "os.scandir", "shutil.copy"] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "process.spawn", names: &["subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call", "subprocess.check_output", "os.system", "os.execv", "os.popen"] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "net.listen", names: &["socket.listen", ".listen"] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "fs.read", names: &["File::open", "fs::read", "fs::read_to_string", "fs::read_dir"] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "process.spawn", names: &["Command::new"] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "net.listen", names: &["TcpListener::bind", "UnixListener::bind"] }
}

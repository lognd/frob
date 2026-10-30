//! Capability atoms this crate adds to the shared registry (grmb-spec 4.1, grimble-model.md 9.6).
//!
//! `gob-ir` registers `net.connect` and `fs.write`; the remaining core atoms named by the
//! worked example, and the callee vocabularies the capability rules observe them by, are
//! submitted here so a model that links this crate resolves them.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9
// frob:ticket 01M4HYH9CDNJSYEZQGKRZA7WX2
// frob:ticket 01M64230AR8DHJZY9QQS3EC85S

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

// Evaluating a string as code (Python `eval`, `exec`, `compile`), ticket T78E2WZ.
inventory::submit! {
    AtomEntry {
        name: "code.eval",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "python", kind: DetectorKind::Callee },
        ],
    }
}

// Native interop (loading a library, calling a foreign function), ticket S3EC85S.
inventory::submit! {
    AtomEntry {
        name: "ffi",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
        ],
    }
}

// Escapes from the type system (`transmute`, inline assembly), ticket S3EC85S.
inventory::submit! {
    AtomEntry {
        name: "unsafe",
        aliases: &[],
        detectors: &[
            DetectorEntry { lang: "rust", kind: DetectorKind::Callee },
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
// `caps` gates it on a companion call so a bare `.listen` is not a use by itself. `Path.m` is
// method `m` on a `pathlib.Path` receiver (a Must use once the receiver type resolves); an ungated
// `.m` is a May use on a receiver that does not resolve. A Rust `a::b` also names `x::a::b`.
inventory::submit! {
    VocabEntry { lang: "python", kind: "fs.read", names: &[
        "open", "io.open", "codecs.open", "os.listdir", "os.scandir", "os.walk", "os.stat", "os.lstat",
        "os.path.exists", "os.path.isfile", "os.path.isdir", "os.path.getsize", "glob.glob", "glob.iglob",
        "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree", "shutil.move",
        "Path.read_text", "Path.read_bytes", "Path.open", "Path.iterdir", "Path.glob", "Path.rglob",
        "Path.stat", "Path.exists", "Path.is_file", "Path.is_dir",
        ".read_text", ".read_bytes", ".open",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "fs.write", names: &[
        "os.remove", "os.unlink", "os.rename", "os.replace", "os.mkdir", "os.makedirs", "os.rmdir",
        "os.removedirs", "os.truncate", "os.chmod", "os.symlink", "shutil.copy", "shutil.copy2",
        "shutil.copyfile", "shutil.copytree", "shutil.move", "shutil.rmtree",
        "tempfile.NamedTemporaryFile", "tempfile.TemporaryFile", "tempfile.mkstemp", "tempfile.mkdtemp",
        "tempfile.TemporaryDirectory",
        "Path.write_text", "Path.write_bytes", "Path.mkdir", "Path.touch", "Path.unlink", "Path.rmdir",
        "Path.rename", "Path.replace",
        ".write_text", ".write_bytes",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "code.eval", names: &["builtins.eval", "builtins.exec", "builtins.compile"] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "process.spawn", names: &["subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call", "subprocess.check_output", "os.system", "os.execv", "os.popen"] }
}

inventory::submit! {
    VocabEntry { lang: "python", kind: "net.listen", names: &["socket.listen", ".listen"] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "fs.read", names: &[
        "File::open", "fs::read", "fs::read_to_string", "fs::read_dir", "fs::metadata",
        "fs::symlink_metadata", "fs::canonicalize", "fs::read_link", "fs::copy", "OpenOptions::new", "File::options",
        "std::path::Path.exists", "std::path::Path.is_file", "std::path::Path.is_dir",
        "std::path::Path.read_dir", "std::path::Path.metadata", "std::path::Path.symlink_metadata",
        "std::path::Path.canonicalize", "std::path::Path.read_link", "std::path::Path.try_exists",
        "std::path::PathBuf.exists", "std::path::PathBuf.is_file", "std::path::PathBuf.is_dir",
        "std::path::PathBuf.read_dir", "std::path::PathBuf.metadata",
        "std::path::PathBuf.symlink_metadata", "std::path::PathBuf.canonicalize",
        "std::path::PathBuf.read_link", "std::path::PathBuf.try_exists",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "fs.write", names: &[
        "File::create", "File::create_new", "OpenOptions::new", "File::options", "fs::write", "fs::copy", "fs::create_dir",
        "fs::create_dir_all", "fs::remove_file", "fs::remove_dir", "fs::remove_dir_all", "fs::rename",
        "fs::set_permissions", "fs::hard_link", "fs::symlink", "fs::symlink_file", "fs::symlink_dir", "fs::soft_link", "tempfile::tempfile", "tempfile::tempdir",
        "NamedTempFile::new", "TempDir::new",
    ] }
}

// A trailing `::*` names every item under that crate or module: foreign calls are open-ended.
inventory::submit! {
    VocabEntry { lang: "rust", kind: "ffi", names: &[
        "libc::*", "libloading::*", "windows_sys::*", "winapi::*", "extern::*",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "unsafe", names: &[
        "mem::transmute", "mem::transmute_copy", "arch::asm", "arch::global_asm",
        "arch::naked_asm",
    ] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "process.spawn", names: &["Command::new"] }
}

inventory::submit! {
    VocabEntry { lang: "rust", kind: "net.listen", names: &["TcpListener::bind", "UdpSocket::bind", "UnixListener::bind"] }
}

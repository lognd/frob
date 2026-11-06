//! Typosquat detection: a crate name one edit away from a well-known crate it is not.

// frob:ticket 01M5A63T0R2D5DKF95XEZ00NZ6

/// Widely used crates a squatter would imitate; names of at least four characters.
pub const POPULAR: &[&str] = &[
    "serde",
    "serde_json",
    "serde_derive",
    "tokio",
    "rand",
    "regex",
    "clap",
    "syn",
    "quote",
    "libc",
    "log",
    "bytes",
    "futures",
    "hyper",
    "reqwest",
    "anyhow",
    "thiserror",
    "chrono",
    "itertools",
    "once_cell",
    "lazy_static",
    "tracing",
    "tracing-subscriber",
    "proc-macro2",
    "base64",
    "uuid",
    "url",
    "toml",
    "rayon",
    "crossbeam",
    "parking_lot",
    "smallvec",
    "indexmap",
    "memchr",
    "semver",
    "env_logger",
    "tempfile",
    "walkdir",
    "bitflags",
    "cfg-if",
    "num-traits",
    "unicode-width",
    "openssl",
    "sha2",
    "hex",
    "time",
    "async-trait",
    "axum",
    "tower",
    "tonic",
    "prost",
    "diesel",
    "sqlx",
    "rusqlite",
    "colored",
    "termcolor",
    "ansi_term",
    "dirs",
    "glob",
    "flate2",
    "tar",
    "zip",
    "rustls",
];

/// Shortest name worth guarding; one edit on a tiny name collides with unrelated crates.
const MIN_LEN: usize = 4;

/// True when `a` and `b` differ by one insert, delete, substitute or adjacent swap.
fn one_edit(a: &[u8], b: &[u8]) -> bool {
    if a == b || a.len().abs_diff(b.len()) > 1 {
        return false;
    }
    if a.len() == b.len() {
        let diffs: Vec<usize> = (0..a.len()).filter(|&i| a[i] != b[i]).collect();
        return match diffs.as_slice() {
            [_] => true,
            [i, j] => *j == i + 1 && a[*i] == b[*j] && a[*j] == b[*i],
            _ => false,
        };
    }
    let (short, long) = if a.len() < b.len() { (a, b) } else { (b, a) };
    let skip = (0..short.len())
        .find(|&i| short[i] != long[i])
        .unwrap_or(short.len());
    short[skip..] == long[skip + 1..]
}

/// The protected name `name` imitates, when it is one edit from one and is not itself protected.
///
/// `extra` adds names the project already trusts (its allowlist) to the built-in [`POPULAR`] list.
pub fn lookalike(name: &str, extra: &[String]) -> Option<String> {
    let known = |n: &str| POPULAR.contains(&n) || extra.iter().any(|e| e == n);
    if known(name) {
        return None;
    }
    let found = extra
        .iter()
        .map(String::as_str)
        .chain(POPULAR.iter().copied())
        .filter(|p| p.len() >= MIN_LEN && one_edit(name.as_bytes(), p.as_bytes()))
        .min()
        .map(str::to_owned);
    tracing::debug!(name, lookalike = ?found, "typosquat check");
    found
}

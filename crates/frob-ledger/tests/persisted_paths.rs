//! Persisted (serde-derived) types never hold `PathBuf` or an unvalidated path string.
//!
//! Paths that are written to disk or JSON are `RelPath` (validated), so a host
//! path cannot leak into the ledger, a lock file or a findings document.

use std::path::Path;

use gob_path::Shown;

/// Crates whose serde-derived types are audited.
const CRATES: [&str; 4] = ["frob-ledger", "gob-lock", "gob-diagnostics", "gob-config"];

/// Field names that mean "a path" when typed as plain strings.
const PATH_NAMES: [&str; 4] = ["file", "files", "path", "paths"];

/// Audited exceptions: `file:Type.field` and the reason the field stays a display string.
const ALLOWED: [(&str, &str); 2] = [
    (
        "gob-diagnostics/src/record.rs:EditRecord.file",
        "findings JSON output only; the source provider hands out display paths (follow-up ticket ~0EWC4K9)",
    ),
    (
        "gob-diagnostics/src/record.rs:FindingRecord.file",
        "findings JSON output only; the source provider hands out display paths (follow-up ticket ~0EWC4K9)",
    ),
];

// frob:ticket 01M5PC8M49F53YSPKKT7XXMDFH
/// Every `.rs` file under a crate's `src` as (`/`-separated key, text).
fn rust_files(crate_name: &str) -> Vec<(String, String)> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(crate_name)
        .join("src");
    let mut out = Vec::new();
    // The display key is built from `/`-joined names, never from the host path, so it is the
    // same on every platform.
    let mut stack = vec![(dir, format!("{crate_name}/src"))];
    while let Some((d, shown)) = stack.pop() {
        for entry in std::fs::read_dir(&d).expect("read_dir") {
            let path = entry.expect("entry").path();
            // A bare file name holds no separator, so its display form is host-independent.
            let name = Shown::of(Path::new(path.file_name().expect("file name"))).to_string();
            if path.is_dir() {
                stack.push((path, format!("{shown}/{name}")));
            } else if path.extension().is_some_and(|e| e == "rs") {
                let text = std::fs::read_to_string(&path).expect("read");
                out.push((format!("{shown}/{name}"), text));
            }
        }
    }
    assert!(!out.is_empty(), "no sources under {crate_name}");
    out
}

/// Violations in one file: lines inside serde-derived items that hold a host or unvalidated path.
fn violations(file: &str, text: &str) -> Vec<String> {
    let mut bad = Vec::new();
    let mut derived = false;
    let mut item = String::new();
    let mut depth = 0i32;
    let mut in_item = false;
    for line in text.lines() {
        let t = line.trim();
        if t.starts_with("#[derive(") && (t.contains("Serialize") || t.contains("Deserialize")) {
            derived = true;
        }
        if derived && !in_item {
            for kw in ["struct ", "enum "] {
                if let Some(rest) = t
                    .trim_start_matches("pub ")
                    .trim_start_matches("pub(crate) ")
                    .strip_prefix(kw)
                {
                    rest.split(|c: char| !c.is_alphanumeric() && c != '_')
                        .next()
                        .unwrap_or("")
                        .clone_into(&mut item);
                    in_item = true;
                    depth = 0;
                }
            }
        }
        if in_item {
            if t.contains("PathBuf") || t.contains("&Path") || t.contains(": Path") {
                bad.push(format!("{file}:{item}: holds a host path: {t}"));
            }
            if let Some((name, ty)) = t
                .trim_start_matches("pub ")
                .split_once(": ")
                .filter(|(n, _)| PATH_NAMES.contains(n))
            {
                let plain = ty.starts_with("String")
                    || ty.starts_with("Option<String>")
                    || ty.starts_with("Vec<String>");
                if plain
                    && !ALLOWED
                        .iter()
                        .any(|(k, _)| *k == format!("{file}:{item}.{name}"))
                {
                    bad.push(format!("{file}:{item}.{name}: path held as {ty}"));
                }
            }
            depth += i32::try_from(line.matches('{').count()).unwrap_or(0);
            depth -= i32::try_from(line.matches('}').count()).unwrap_or(0);
            if depth <= 0 && (t.ends_with('}') || t.ends_with(';')) {
                in_item = false;
                derived = false;
            }
        }
    }
    bad
}

/// Given the persisted model types, when the audit runs, then none holds `PathBuf` or an unvalidated path string.
#[test]
fn persisted_types_hold_no_host_paths() {
    let bad: Vec<String> = CRATES
        .iter()
        .flat_map(|c| rust_files(c))
        .flat_map(|(f, t)| violations(&f, &t))
        .collect();
    assert!(
        bad.is_empty(),
        "persisted path violations:\n{}",
        bad.join("\n")
    );
}

/// The audit itself flags a `PathBuf` field and a plain-string path field.
#[test]
fn audit_detects_violations() {
    let src =
        "#[derive(Serialize)]\npub struct A {\n    pub p: PathBuf,\n    pub file: String,\n}\n";
    assert_eq!(violations("x.rs", src).len(), 2);
    let ok = "#[derive(Serialize)]\npub struct B {\n    pub file: RelPath,\n}\n";
    assert!(violations("x.rs", ok).is_empty());
}

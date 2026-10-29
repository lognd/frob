//! Ratchet: every rule family names one owning crate, and a family declared in several crates
//! is a listed, shrinking exception (org audit R3).
//!
//! The family of a `#[rule(...)]` declaration is its explicit `family = "X"` or, when absent, the
//! alphabetic-plus-digit prefix of its `id` (the same default the derive applies). Ids a stage
//! raises but a sibling product declares (`SIBLING_OWNED` in gob-check's `tool_parse.rs`, the `CI`
//! ids) carry no frob declaration, so they are covered by the owner declaring them, not here.
#![allow(
    clippy::disallowed_methods,
    reason = "a workspace-wide source scan reads the disk, not a walked Core"
)]

// frob:ticket 01M61MM4DYQH99W116AH0NS1CC
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

/// The one crate that owns each rule family. Adding a family means adding a row here.
const OWNERS: &[(&str, &str)] = &[
    ("AFFECT", "frob-ack"),
    ("BP", "crunk-rules"),
    ("CAP", "grimble-bind"),
    ("CFG", "gob-config"),
    ("CI", "grimble-ci"),
    ("CLAIM", "grimble-model"),
    ("COH", "grimble-check"),
    ("COLOR", "crunk-rules"),
    ("COMP", "crunk-rules"),
    ("CONTENT", "crunk-rules"),
    ("CONTRAST", "crunk-rules"),
    ("COV", "frob-obligations"),
    ("CRAFT", "crunk-rules"),
    ("CYCLE", "grimble-arch"),
    ("DEAD", "grimble-arch"),
    ("DK", "grimble-ci"),
    ("DOC", "frob-obligations"),
    ("DRIFT", "frob-ack"),
    ("DSL", "gob-directives"),
    ("DUP", "grimble-arch"),
    ("ERR", "grimble-lints"),
    ("EXC", "frob-obligations"),
    ("EXPORT", "crunk-rules"),
    ("FLOW", "grimble-model"),
    ("GRL", "frob-check"),
    ("GX", "crunk-rules"),
    ("HUMAN", "crunk-rules"),
    ("INV", "frob-obligations"),
    ("LARGE", "grimble-arch"),
    ("LAYER", "crunk-rules"),
    ("LAYOUT", "crunk-rules"),
    ("LOG", "grimble-check"),
    ("MDL", "grimble-model"),
    ("ORG", "crunk-rules"),
    ("PACK", "grimble-capabilities"),
    ("PAIR", "grimble-lints"),
    ("PARSE", "gob-directives"),
    ("PATH", "grimble-lints"),
    ("PERF", "gob-check"),
    ("PM", "frob-pm"),
    ("PROC", "gob-check"),
    ("RADIUS", "crunk-rules"),
    ("READ", "gob-check"),
    ("REF", "frob-obligations"),
    ("REL", "frob-release"),
    ("RES", "grimble-lints"),
    ("RESP", "crunk-rules"),
    ("SCENE", "crunk-rules"),
    ("SCOPE", "frob-lease"),
    ("SIB", "frob-check"),
    ("SIZE", "crunk-rules"),
    ("SLOP", "crunk-rules"),
    ("SPACE", "crunk-rules"),
    ("STATE", "crunk-rules"),
    ("SYS", "grimble-bind"),
    ("TEST", "frob-tests"),
    ("TICK", "frob-ledger"),
    ("TIME", "grimble-lints"),
    ("TODO", "frob-obligations"),
    ("TOKEN", "crunk-rules"),
    ("TOKENS", "crunk-rules"),
    ("TOOL", "gob-check"),
    ("TW", "crunk-rules"),
    ("TYPE", "crunk-rules"),
    ("UNITY", "grimble-lints"),
    ("VIS", "grimble-arch"),
    ("WAIVE", "crunk-rules"),
];

/// Families declared in more than one crate today, with the crates that declare them. Each row is
/// debt: moving the last stray declaration into the owner must delete the row.
const SPLIT_ALLOWED: &[(&str, &[&str])] = &[
    ("GX", &["crunk-check", "crunk-rules"]),
    ("TICK", &["frob-ledger", "frob-obligations"]),
    ("UNITY", &["frob-obligations", "grimble-lints"]),
];

/// Collect every `.rs` file under a crate's `src` directory.
fn rust_sources(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_sources(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// The value of `key = "..."` inside one attribute body, ignoring keys that merely end in `key`.
fn attr_value(body: &str, key: &str) -> Option<String> {
    let needle = format!("{key} = \"");
    let mut from = 0;
    while let Some(at) = body[from..].find(&needle) {
        let start = from + at;
        let boundary = body[..start]
            .chars()
            .next_back()
            .is_none_or(|c| !(c.is_alphanumeric() || c == '_'));
        if boundary {
            let rest = &body[start + needle.len()..];
            return rest.split('"').next().map(str::to_owned);
        }
        from = start + needle.len();
    }
    None
}

/// The family of the id prefix: the leading letters, then digits up to the numeric tail.
fn id_family(id: &str) -> String {
    let tail = id.chars().rev().take_while(char::is_ascii_digit).count();
    id[..id.len() - tail.min(3)].to_owned()
}

/// The families declared by `#[rule(` attributes in one source text.
fn declared_families(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut body: Option<String> = None;
    for line in text.lines() {
        let line = line.trim();
        if body.is_none() && line.starts_with("#[rule(") {
            body = Some(String::new());
        }
        if let Some(b) = body.as_mut() {
            b.push_str(line);
            b.push(' ');
            if line.ends_with(")]") {
                if let Some(id) = attr_value(b, "id") {
                    out.push(attr_value(b, "family").unwrap_or_else(|| id_family(&id)));
                }
                body = None;
            }
        }
    }
    out
}

/// Every family declared in the workspace, with the crates declaring it.
fn scan() -> BTreeMap<String, BTreeSet<String>> {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let mut found: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for entry in fs::read_dir(&crates).expect("crates dir").flatten() {
        let name = entry.file_name().to_string_lossy().into_owned();
        let mut files = Vec::new();
        rust_sources(&entry.path().join("src"), &mut files);
        for file in files {
            let text = fs::read_to_string(&file).unwrap_or_default();
            for family in declared_families(&text) {
                found.entry(family).or_default().insert(name.clone());
            }
        }
    }
    found
}

#[test]
fn id_family_strips_only_the_numeric_tail() {
    assert_eq!(id_family("COV006"), "COV");
    assert_eq!(id_family("A11Y101"), "A11Y");
    assert_eq!(id_family("SYSDESIGN101"), "SYSDESIGN");
}

#[test]
fn every_rule_family_has_exactly_one_owning_crate() {
    let found = scan();
    assert!(
        found.len() > 30,
        "scan found too few families: {}",
        found.len()
    );
    let owners: BTreeMap<&str, &str> = OWNERS.iter().copied().collect();
    assert_eq!(
        owners.len(),
        OWNERS.len(),
        "a family is listed twice in OWNERS"
    );
    let allowed: BTreeMap<&str, BTreeSet<&str>> = SPLIT_ALLOWED
        .iter()
        .map(|(f, cs)| (*f, cs.iter().copied().collect()))
        .collect();
    let mut problems = Vec::new();
    for (family, crates) in &found {
        let declared: BTreeSet<&str> = crates.iter().map(String::as_str).collect();
        match owners.get(family.as_str()) {
            None => problems.push(format!(
                "{family}: no owner in OWNERS (declared in {declared:?})"
            )),
            Some(owner) if !declared.contains(owner) => {
                problems.push(format!(
                    "{family}: owner {owner} declares none of it ({declared:?})"
                ));
            }
            Some(_) => {}
        }
        match (declared.len() > 1, allowed.get(family.as_str())) {
            (true, None) => problems.push(format!(
                "{family}: split across {declared:?}, not in SPLIT_ALLOWED"
            )),
            (true, Some(set)) if *set != declared => {
                problems.push(format!(
                    "{family}: SPLIT_ALLOWED says {set:?}, scan says {declared:?}"
                ));
            }
            (false, Some(_)) => problems.push(format!(
                "{family}: no longer split, remove its SPLIT_ALLOWED row"
            )),
            _ => {}
        }
    }
    for family in owners.keys().chain(allowed.keys()) {
        if !found.contains_key(*family) {
            problems.push(format!(
                "{family}: listed but declared nowhere, remove the row"
            ));
        }
    }
    assert!(
        problems.is_empty(),
        "family ownership violations:\n{}",
        problems.join("\n")
    );
}

//! Shared `REL003` test helpers and the mdtest corpus runner (the corpus directory is shared with `REL002`).
// frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
#![allow(dead_code)] // each test binary uses a different subset

use std::fs;
use std::path::Path;

use frob_release::rel003::{evaluate, missing};

/// A ULID the corpus treats as a known ticket.
pub const KNOWN: &str = "01ARZ3NDEKTSV4RRFFQ69G5FAV";
/// A second known ticket.
pub const OTHER: &str = "01BX5ZZKBKACTAV9WEVGEMMVRY";
/// A well-formed ULID that is not a ticket.
pub const STRANGER: &str = "01CZ3NDEKTSV4RRFFQ69G5FAVX";

/// Resolver that knows [`KNOWN`] and [`OTHER`] and nothing else.
pub fn resolver(ulid: &str) -> Option<String> {
    match ulid {
        KNOWN => Some("~KNOWN".to_owned()),
        OTHER => Some("~OTHER".to_owned()),
        _ => None,
    }
}

/// Write `changelog.d/<name>` with `body` under `root`.
pub fn fragment(root: &Path, name: &str, body: &str) {
    let dir = root.join("changelog.d");
    fs::create_dir_all(&dir).unwrap();
    fs::write(dir.join(name), body).unwrap();
}

/// Corpus DSL: `fragment NAME BODY` (`-` is an empty body, `@nonascii` a non-ASCII one), `require ULID`.
pub fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/frob-release/src/rel003.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    let mut required = Vec::new();
    for line in case.text.lines().filter(|l| !l.trim().is_empty()) {
        let (verb, rest) = line.split_once(' ').unwrap();
        match verb {
            "fragment" => {
                let (name, body) = rest.split_once(' ').unwrap();
                let body = match body {
                    "-" => "",
                    "@nonascii" => "frob: Added a caf\u{e9} thing.",
                    b => b,
                };
                fragment(d.path(), name, &format!("{body}\n"));
            }
            "require" => required.push(rest.trim().to_owned()),
            other => unreachable!("unknown DSL verb {other}"),
        }
    }
    let mut findings = evaluate(d.path(), &resolver).findings;
    for ulid in required {
        findings.extend(missing(d.path(), &ulid, "~KNOWN"));
    }
    findings
}

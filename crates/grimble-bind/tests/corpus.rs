//! The binding corpus of binding.md section 10: one directory per case under `tests/corpus`,
//! holding a small repository in `repo/` and an `expect` file.
//!
//! `expect` lines (blank lines and `#` comments are ignored):
//!
//! - `finding RULE SEVERITY[:reason] [~substring]`: one finding of that rule and severity (and
//!   Unresolved reason code); the set of findings must match exactly, and the substring must
//!   occur in the message of a finding with that key;
//! - `row ENTITY ROLE IDENTITY STATUS RANK`: B holds this row (`-` is the hidden remainder);
//! - `norow ENTITY ROLE IDENTITY`: B holds no row for the identity;
//! - `owner IDENTITY must:NODE | foreign | unknown:A,B | may:A,B`: the merged owner;
//! - `subjects RULE N`: the subject count of the rule.
//!
//! A `modeled` file lists `[grimble] modeled` selectors one per line; a `strict` file turns
//! `[grimble] strict` on.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use gob_rules::Severity;
use grimble_bind::{BindInput, Binding, Reason};
use grimble_model::ModelFiles;

fn corpus_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus")
}

fn bind_case(dir: &Path) -> Binding {
    let root = dir.join("repo");
    let walked = gob_walk::walk(&root, &gob_walk::WalkConfig::default()).expect("walk");
    let mut model = ModelFiles::new();
    for f in &walked.files {
        if std::path::Path::new(&f.path)
            .extension()
            .is_some_and(|e| e == "grmb")
        {
            model = model.with_file(&f.path, std::fs::read(root.join(&f.path)).expect("read"));
        }
    }
    let modeled: Vec<String> = std::fs::read_to_string(dir.join("modeled"))
        .map(|t| {
            t.lines()
                .filter(|l| !l.trim().is_empty())
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default();
    grimble_bind::bind(&BindInput {
        root: &root,
        entries: &walked.files,
        model: &model,
        modeled: &modeled,
        strict: dir.join("strict").exists(),
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn key_of(f: &grimble_bind::BindFinding) -> String {
    match f.severity {
        Severity::Unresolved => format!(
            "{} unresolved:{}",
            f.rule,
            f.reason.map_or("?", Reason::code)
        ),
        s => format!("{} {}", f.rule, format!("{s:?}").to_lowercase()),
    }
}

fn owner_text(b: &Binding, id: &str) -> String {
    use gob_walk::Owner;
    let Some(u) = b.owners.units.get(id) else {
        return "foreign".to_owned();
    };
    let names = |s: &std::collections::BTreeSet<gob_walk::EntityName>| {
        s.iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join(",")
    };
    match &u.merged.owner {
        Owner::Must(n) => format!("must:{n}"),
        Owner::May(s) => format!("may:{}", names(s)),
        Owner::Unknown(s) => format!("unknown:{}", names(s)),
        Owner::Foreign => "foreign".to_owned(),
    }
}

fn check_case(dir: &Path) -> Vec<String> {
    let b = bind_case(dir);
    let expect = std::fs::read_to_string(dir.join("expect")).expect("expect file");
    let mut problems = Vec::new();
    let mut want: Vec<String> = Vec::new();
    let mut subs: Vec<(String, String)> = Vec::new();
    for line in expect
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
    {
        let (head, sub) = line
            .split_once(" ~")
            .map_or((line, None), |(h, s)| (h, Some(s)));
        let parts: Vec<&str> = head.split_whitespace().collect();
        match parts.as_slice() {
            ["finding", rule, sev] => {
                let k = format!("{rule} {sev}");
                want.push(k.clone());
                if let Some(s) = sub {
                    subs.push((k, s.to_owned()));
                }
            }
            ["row", entity, role, id, status, rank] => {
                let id_opt = (*id != "-").then(|| (*id).to_owned());
                let found = b.rows.iter().any(|r| {
                    r.entity == *entity
                        && r.role.as_str() == *role
                        && r.identity == id_opt
                        && r.status.as_str() == *status
                        && r.source.rank().to_string() == *rank
                });
                if !found {
                    problems.push(format!("missing row: {line}"));
                }
            }
            ["norow", entity, role, id] => {
                if b.rows.iter().any(|r| {
                    r.entity == *entity
                        && r.role.as_str() == *role
                        && r.identity.as_deref() == Some(*id)
                }) {
                    problems.push(format!("unexpected row: {line}"));
                }
            }
            ["owner", id, expected] => {
                let got = owner_text(&b, id);
                if got != *expected {
                    problems.push(format!("owner of {id}: expected {expected}, got {got}"));
                }
            }
            ["subjects", rule, n] => {
                let got = b.subjects.get(rule).copied();
                if got != n.parse::<usize>().ok() {
                    problems.push(format!("subjects {rule}: expected {n}, got {got:?}"));
                }
            }
            other => problems.push(format!("unparsable expect line {other:?}")),
        }
    }
    let mut got: Vec<String> = b.findings.iter().map(key_of).collect();
    got.sort();
    want.sort();
    if got != want {
        problems.push(format!(
            "findings differ:\n  expected {want:?}\n  got      {got:?}"
        ));
        for f in &b.findings {
            problems.push(format!("  {} {}", key_of(f), f.message));
        }
    }
    for (k, s) in subs {
        if !b
            .findings
            .iter()
            .any(|f| key_of(f) == k && f.message.contains(&s))
        {
            problems.push(format!("no {k} finding mentions `{s}`"));
        }
    }
    problems
}

// frob:tests crates/grimble-bind/src/lib.rs::bind
#[test]
fn every_corpus_case_matches_its_expectations() {
    let mut cases: Vec<PathBuf> = std::fs::read_dir(corpus_dir())
        .expect("corpus dir")
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.join("expect").is_file())
        .collect();
    cases.sort();
    assert!(!cases.is_empty(), "no corpus cases found");
    let mut failures: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for c in &cases {
        let problems = check_case(c);
        if !problems.is_empty() {
            failures.insert(
                c.file_name().expect("name").to_string_lossy().into_owned(),
                problems,
            );
        }
    }
    assert!(failures.is_empty(), "corpus failures:\n{failures:#?}");
}

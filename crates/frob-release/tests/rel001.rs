//! `REL001` tests on temporary repositories: stray, cut, moved, version-mismatched and ignored tags.
//! The mdtest corpus (`tests/mdtest/rel001.md`) runs from the `rel002` test binary, which owns the shared directory.
// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG

use std::fs;
use std::path::Path;

use frob_pm::event::CutData;
use frob_release::cut::{CutError, CutLedger, CutPlan, cut};
use frob_release::rel001::{evaluate, not_applicable};
use gob_git::{RelPath, Repo};
use gob_rules::Severity;

mod rel001_corpus;
use rel001_corpus::{FROB_TOML, MAIN, commit, fixture, opts, recorded, tag};

fn errors(repo: &Repo, cuts: &[CutData]) -> Vec<String> {
    evaluate(repo, cuts)
        .findings
        .into_iter()
        .inspect(|f| assert_eq!(f.severity, Severity::Error, "{}", f.message))
        .map(|f| f.message)
        .collect()
}

#[test]
fn a_tag_made_by_plain_tag_creation_fires() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let c = commit(&repo, "0.0.1");
    tag(&repo, "frob-v0.0.1", c);
    let e = evaluate(&repo, &[]);
    assert_eq!(e.subjects, 1);
    assert_eq!(e.findings.len(), 1, "{:?}", e.findings);
    let f = &e.findings[0];
    assert_eq!(f.severity, Severity::Error);
    for want in [
        "frob-v0.0.1",
        "no recorded release cut",
        "frob release cut 0.0.1",
    ] {
        assert!(f.message.contains(want), "{want} in {}", f.message);
    }
}

#[test]
fn the_stray_tag_remedy_names_adopt_before_deletion() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let c = commit(&repo, "0.0.1");
    tag(&repo, "frob-v0.0.1", c);
    let m = evaluate(&repo, &[]).findings[0].message.clone();
    let adopt = m.find("frob release adopt 0.0.1").expect("adopt named");
    let delete = m.find("delete the tag").expect("deletion named");
    assert!(adopt < delete, "adopt comes first: {m}");
}

#[test]
fn a_matching_recorded_cut_is_silent() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let c = commit(&repo, "0.0.1");
    let t = tag(&repo, "frob-v0.0.1", c);
    let e = evaluate(&repo, &[recorded("0.0.1", c, vec![t])]);
    assert_eq!(e.subjects, 1);
    assert!(e.findings.is_empty(), "{:?}", e.findings);
}

/// A ledger double that only remembers what the engine recorded.
#[derive(Default)]
struct Fake {
    recorded: Vec<CutData>,
}

impl CutLedger for Fake {
    fn clear(&mut self) -> Result<(), CutError> {
        Ok(())
    }
    fn recorded(&self) -> Result<bool, CutError> {
        Ok(false)
    }
    fn record(&mut self, data: &CutData) -> Result<(), CutError> {
        self.recorded.push(data.clone());
        Ok(())
    }
}

#[test]
fn tags_made_by_release_cut_itself_are_silent() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (dir, repo) = fixture();
    let files = [
        ("frob.toml", FROB_TOML),
        (
            "Cargo.toml",
            "[workspace]\nmembers = [\"crates/*\"]\n\n[workspace.package]\nversion = \"0.0.0\"\n",
        ),
        (
            "crates/a/Cargo.toml",
            "[package]\nname = \"a\"\nversion = \"0.0.0\"\n",
        ),
        ("crates/a/src/lib.rs", ""),
        (
            "Cargo.lock",
            "version = 4\n\n[[package]]\nname = \"a\"\nversion = \"0.0.0\"\n",
        ),
        (
            "changelog.d/01M4069X6S9RJWRXX3YBZ9EG10.added.md",
            "frob: Added cut.\n",
        ),
    ];
    let changes: Vec<_> = files
        .iter()
        .map(|(p, t)| (RelPath::new(*p).unwrap(), Some(t.as_bytes().to_vec())))
        .collect();
    repo.commit_paths(MAIN, &changes, "base", &opts()).unwrap();
    fs::write(
        repo.git_dir().join("config"),
        format!(
            "{}[user]\n\tname = Test\n\temail = test@example.com\n",
            fs::read_to_string(repo.git_dir().join("config")).unwrap()
        ),
    )
    .unwrap();
    let plan = CutPlan {
        root: dir.path(),
        version: "0.532.0".to_owned(),
        date: "2026-10-03".to_owned(),
        base: "main".to_owned(),
        push: false,
        stop_after: None,
    };
    let mut ledger = Fake::default();
    cut(
        &plan,
        &|u: &str| Some(format!("~{}", &u[u.len() - 7..])),
        &mut ledger,
    )
    .unwrap();
    assert_eq!(ledger.recorded.len(), 1);
    let e = evaluate(&repo, &ledger.recorded);
    assert_eq!(e.subjects, 2);
    assert!(e.findings.is_empty(), "{:?}", e.findings);
    // The same tags without the record are strays.
    assert_eq!(errors(&repo, &[]).len(), 2);
}

#[test]
fn a_moved_tag_fires_naming_the_recorded_commit() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let c1 = commit(&repo, "0.0.1");
    let t = tag(&repo, "frob-v0.0.1", c1);
    let cuts = [recorded("0.0.1", c1, vec![t])];
    // Move the tag: drop the loose ref and tag the next commit (same workspace version).
    let c2 = repo
        .commit_paths(
            MAIN,
            &[(RelPath::new("x.txt").unwrap(), Some(b"x".to_vec()))],
            "next",
            &opts(),
        )
        .unwrap()
        .oid;
    fs::remove_file(repo.git_dir().join("refs/tags/frob-v0.0.1")).unwrap();
    tag(&repo, "frob-v0.0.1", c2);
    let msgs = errors(&repo, &cuts);
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    for want in ["was moved", &c1.to_string(), &c2.to_string()] {
        assert!(msgs[0].contains(want), "{want} in {}", msgs[0]);
    }
}

#[test]
fn a_version_mismatch_at_the_tagged_commit_fires() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let c = commit(&repo, "0.0.9");
    let t = tag(&repo, "frob-v0.1.0", c);
    let msgs = errors(&repo, &[recorded("0.1.0", c, vec![t])]);
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    for want in ["frob-v0.1.0", "0.1.0", "0.0.9"] {
        assert!(msgs[0].contains(want), "{want} in {}", msgs[0]);
    }
}

#[test]
fn the_version_is_read_from_the_commit_not_the_working_tree() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (d, repo) = fixture();
    let c = commit(&repo, "0.0.1");
    let t = tag(&repo, "frob-v0.0.1", c);
    fs::write(
        d.path().join("Cargo.toml"),
        "[workspace]\n[workspace.package]\nversion = \"9.9.9\"\n",
    )
    .unwrap();
    assert!(
        evaluate(&repo, &[recorded("0.0.1", c, vec![t])])
            .findings
            .is_empty()
    );
}

#[test]
fn tags_outside_the_product_prefixes_are_ignored() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let c = commit(&repo, "0.531.0");
    for name in ["v0.531.0", "frob-vnext", "other-v1.0.0"] {
        tag(&repo, name, c);
    }
    let e = evaluate(&repo, &[]);
    assert_eq!(e.subjects, 0);
    assert!(e.findings.is_empty(), "{:?}", e.findings);
    assert!(
        e.not_applicable.is_some(),
        "only ignored tags means no product tags"
    );
}

#[test]
fn no_tags_and_no_cuts_is_not_applicable_with_a_reason() {
    // frob:tests crates/frob-release/src/rel001.rs::not_applicable
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    commit(&repo, "0.0.1");
    let e = evaluate(&repo, &[]);
    let why = e.not_applicable.expect("not applicable");
    assert!(why.contains("no product tags"), "{why}");
    assert_eq!(e.subjects, 0);
    assert!(e.findings.is_empty());
    assert_eq!(not_applicable(&repo, &[]), Some(why));
    let c = commit(&repo, "0.0.2");
    let t = tag(&repo, "frob-v0.0.2", c);
    assert_eq!(
        not_applicable(&repo, &[]),
        None,
        "a product tag makes it apply"
    );
    assert!(not_applicable(&repo, &[recorded("0.0.2", c, vec![t])]).is_none());
}

#[test]
fn this_repository_is_clean_or_not_applicable() {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let repo = Repo::discover(&root).unwrap();
    let e = evaluate(&repo, &[]);
    assert!(e.findings.is_empty(), "{:?}", e.findings);
}

#[test]
fn the_configured_tag_pattern_decides_which_tags_are_product_tags() {
    // frob:ticket 01M413T4PVDKZ014X3WB5DF7DD
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (d, repo) = fixture();
    fs::write(d.path().join("frob.toml"), "").unwrap();
    let c = commit(&repo, "0.0.1");
    // Default pattern: `v{version}` is a product tag, `frob-v{version}` is not.
    tag(&repo, "frob-v0.0.1", c);
    assert!(errors(&repo, &[]).is_empty());
    tag(&repo, "v0.0.1", c);
    let msgs = errors(&repo, &[]);
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    assert!(msgs[0].contains("`v0.0.1`"), "{msgs:?}");
    // frob's own pattern ignores the plain `v` tag again.
    fs::write(d.path().join("frob.toml"), rel001_corpus::FROB_TOML).unwrap();
    let msgs = errors(&repo, &[]);
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    assert!(msgs[0].contains("`frob-v0.0.1`"), "{msgs:?}");
}

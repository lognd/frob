//! Shared `REL001` test helpers and the mdtest corpus runner (the corpus directory is shared with `REL002`).
// frob:ticket 01M4069XB9N36CQGEBNPKJ5AVG
#![allow(dead_code)] // each test binary uses a different subset

use std::fs;

use frob_pm::event::{CutData, TagRecord};
use frob_release::rel001::evaluate;
use gob_git::{CommitOptions, Oid, RelPath, Repo};

pub const MAIN: &str = "refs/heads/main";

pub fn opts() -> CommitOptions {
    CommitOptions {
        cas_retries: 5,
        author: Some(("Test".into(), "test@example.com".into())),
    }
}

pub fn author() -> (String, String) {
    ("Test".to_owned(), "test@example.com".to_owned())
}

pub fn fixture() -> (tempfile::TempDir, Repo) {
    let dir = tempfile::tempdir().unwrap();
    let repo = Repo::init(dir.path()).unwrap();
    fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").unwrap();
    (dir, repo)
}

/// Commit a root manifest declaring workspace version `version`; returns the commit.
pub fn commit(repo: &Repo, version: &str) -> Oid {
    let text = format!("[workspace]\nmembers = []\n[workspace.package]\nversion = \"{version}\"\n");
    let change = (RelPath::new("Cargo.toml").unwrap(), Some(text.into_bytes()));
    repo.commit_paths(MAIN, &[change], &format!("v{version}"), &opts())
        .unwrap()
        .oid
}

/// Create the annotated tag `name` at `commit`, returning what a cut would record for it.
pub fn tag(repo: &Repo, name: &str, commit: Oid) -> TagRecord {
    let object = repo
        .create_annotated_tag(name, commit, "release", Some(author()))
        .unwrap();
    TagRecord {
        name: name.to_owned(),
        object: object.to_string(),
        commit: commit.to_string(),
    }
}

pub fn recorded(version: &str, commit: Oid, tags: Vec<TagRecord>) -> CutData {
    CutData {
        version: version.to_owned(),
        commit: commit.to_string(),
        tags,
    }
}

pub fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/frob-release/src/rel001.rs::evaluate
    let (_d, repo) = fixture();
    let mut head = None;
    let mut cuts: Vec<CutData> = Vec::new();
    for line in case.text.lines().filter(|l| !l.trim().is_empty()) {
        let w: Vec<&str> = line.split_whitespace().collect();
        match w[0] {
            "commit" => head = Some(commit(&repo, w[1])),
            "tag" => {
                tag(&repo, w[1], head.unwrap());
            }
            "cut" => {
                let c = head.unwrap();
                let t = tag(&repo, w[1], c);
                cuts.push(recorded(w[2], c, vec![t]));
            }
            other => unreachable!("unknown DSL verb {other}"),
        }
    }
    evaluate(&repo, &cuts).findings
}

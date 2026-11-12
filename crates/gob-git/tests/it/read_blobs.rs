//! Batched blob reads: identical to per-blob reads, loud on bad ids, and measurably cheaper.

// frob:ticket 01M5JCT8CXN20B2GJHAE5JDHHC

use std::time::{Duration, Instant};

use gob_git::{CommitOptions, Oid, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

fn opts() -> CommitOptions {
    CommitOptions {
        cas_retries: 5,
        author: Some(("Test".into(), "test@example.com".into())),
    }
}

/// A repo whose `main` holds `files`, returning the blob ids in path order.
fn repo_with(files: &[(String, Vec<u8>)]) -> (tempfile::TempDir, Repo, Vec<Oid>) {
    let dir = tempfile::tempdir().unwrap();
    let repo = Repo::init(dir.path()).unwrap();
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").unwrap();
    let changes: Vec<(RelPath, Option<Vec<u8>>)> = files
        .iter()
        .map(|(p, b)| (RelPath::new(p).unwrap(), Some(b.clone())))
        .collect();
    repo.commit_paths(MAIN, &changes, "fill", &opts()).unwrap();
    let ids = repo
        .blobs_at(MAIN)
        .unwrap()
        .into_iter()
        .map(|(_, oid)| oid)
        .collect();
    (dir, repo, ids)
}

#[test]
// frob:tests crates/gob-git/src/read.rs::Repo.read_blobs
fn batched_read_equals_per_blob_reads_for_edge_content() {
    let mut files = vec![
        ("a-empty".to_string(), Vec::new()),
        (
            "b-binary".to_string(),
            vec![0, 255, 1, 254, 0, 0, 13, 10, 200],
        ),
        ("c-text".to_string(), b"hello\n".to_vec()),
        (
            "d-large".to_string(),
            (0..3_000_000u32).map(|i| (i % 251) as u8).collect(),
        ),
    ];
    files.sort();
    let (_dir, repo, ids) = repo_with(&files);
    let batched = repo.read_blobs(&ids).unwrap();
    let single: Vec<Vec<u8>> = ids.iter().map(|o| repo.read_blob(o).unwrap()).collect();
    assert_eq!(batched, single);
    let want: Vec<Vec<u8>> = files.into_iter().map(|(_, b)| b).collect();
    assert_eq!(batched, want);
    assert!(repo.read_blobs(&[]).unwrap().is_empty());
}

#[test]
// frob:tests crates/gob-git/src/read.rs::Repo.read_blobs
fn batched_read_fails_on_missing_object_and_non_blob() {
    let (_dir, repo, mut ids) = repo_with(&[("a".to_string(), b"x".to_vec())]);
    let tree = repo.rev_parse(&format!("{MAIN}^{{tree}}")).unwrap();
    assert!(
        repo.read_blobs(&[ids[0], tree]).is_err(),
        "a tree is not a blob"
    );
    ids.push(Oid::from_hex(b"0123456789012345678901234567890123456789").unwrap());
    assert!(
        repo.read_blobs(&ids).is_err(),
        "a missing object is an error"
    );
}

fn best_of<T>(dir: &std::path::Path, f: impl Fn(&Repo) -> T) -> Duration {
    (0..5)
        .map(|_| {
            // A fresh handle per run: the in-process object cache starts cold, as in a CLI run.
            let repo = Repo::discover(dir).unwrap();
            let t = Instant::now();
            std::hint::black_box(f(&repo));
            t.elapsed()
        })
        .min()
        .unwrap()
}

#[test]
// frob:tests crates/gob-git/src/read.rs::Repo.read_blobs
fn batched_read_is_not_slower_than_per_blob_reads() {
    let files: Vec<(String, Vec<u8>)> = (0..4000)
        .map(|i| {
            let body = format!("+++\nid = \"{i}\"\n+++\nbody {i}\n").repeat(40);
            (format!("t/{i:05}.md"), body.into_bytes())
        })
        .collect();
    let (dir, repo, ids) = repo_with(&files);
    let single = best_of(dir.path(), |r| {
        ids.iter()
            .map(|o| r.read_blob(o).unwrap())
            .collect::<Vec<_>>()
    });
    let batched = best_of(dir.path(), |r| r.read_blobs(&ids).unwrap());
    drop(repo);
    eprintln!(
        "read_blobs timing for {} blobs: per-blob {single:?}, batched {batched:?}",
        ids.len()
    );
    // Generous margin: the batch does strictly less work, so only a regression trips this.
    assert!(
        batched <= single + single / 4,
        "batched {batched:?} vs per-blob {single:?}"
    );
}

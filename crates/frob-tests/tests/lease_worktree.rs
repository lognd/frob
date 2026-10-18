//! `lease_ticket` from a linked worktree: the shape every ticket worktree has.

// frob:ticket 01M4DPJKMT0JYSBXXXHPSJRG93
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

use frob_tests::lease_ticket;
use gob_git::Repo;

use crate::common;
use common::{git, write};

// frob:tests crates/frob-tests/src/lease.rs::lease_ticket
#[test]
fn a_linked_worktree_finds_the_lease_it_holds() {
    let dir = tempfile::tempdir().expect("tempdir");
    let primary = dir.path().join("primary");
    std::fs::create_dir_all(&primary).expect("mkdir");
    git(&primary, &["init", "-q"]);
    git(&primary, &["config", "user.name", "Test User"]);
    git(&primary, &["config", "user.email", "test@example.com"]);
    write(&primary, "a.txt", "a\n");
    git(&primary, &["add", "-A"]);
    git(&primary, &["commit", "-q", "-m", "base"]);
    let linked = dir.path().join("wt");
    git(
        &primary,
        &[
            "worktree",
            "add",
            "-q",
            "-b",
            "ticket/X",
            linked.to_str().expect("utf8"),
        ],
    );
    let leases = primary.join(".git/frob/leases");
    std::fs::create_dir_all(&leases).expect("leases dir");
    std::fs::write(
        leases.join("X.toml"),
        format!(
            "ticket = \"01TICKETX\"\n\n[holder]\nactor = \"t\"\nworktree = '{}'\n",
            linked.display()
        ),
    )
    .expect("lease");

    let repo = Repo::discover(&linked).expect("repo");
    let root = repo.work_dir().expect("work dir").to_path_buf();
    assert_eq!(
        lease_ticket(repo.common_dir(), &root).as_deref(),
        Some("01TICKETX"),
        "common dir {:?}, root {root:?}",
        repo.common_dir()
    );
}

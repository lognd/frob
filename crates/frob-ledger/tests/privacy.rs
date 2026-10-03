//! `TICK004`: the home-path byte scan and its ledger walk.
// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A

use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::privacy::{find_home_path, find_home_root, tick004};
use frob_ledger::{Ledger, LedgerConfig};
use gob_git::{CommitOptions, RelPath, Repo};

/// Every documented spelling is found; relative lookalikes are not.
#[test]
fn spellings_and_lookalikes() {
    let hits: &[(&str, &str)] = &[
        ("at /home/name/projects", "/home/<name>/"),
        ("x=\"/Users/Bob Smith/\"", ""),
        ("/Users/bob/Library", "/Users/<name>/"),
        ("cd /root/work", "/root/"),
        ("C:\\Users\\bob\\proj", "C:\\Users\\<name>\\"),
        ("C:\\\\Users\\\\bob\\\\proj", "C:\\\\Users\\\\<name>\\\\"),
        ("d:/Users/bob/proj", "C:/Users/<name>/"),
        ("\"/home/x.y-z/\"", "/home/<name>/"),
    ];
    for (text, kind) in hits {
        let got = find_home_path(text.as_bytes()).map(|(_, k)| k);
        if kind.is_empty() {
            assert_eq!(got, None, "{text}");
        } else {
            assert_eq!(got, Some(*kind), "{text}");
        }
    }
    for clean in [
        "crates/root/x",
        "../home/ann/x",
        "/home/<user>/x",
        "/homework/x/",
        "/home/ann",
        "~/projects",
        "frob-v2-wt/33PZ67A",
        "a /Users/ only",
        "",
    ] {
        assert_eq!(find_home_path(clean.as_bytes()), None, "{clean}");
    }
}

/// A file with a home path yields one finding with a remedy; a clean file yields none.
#[test]
fn finding_names_file_and_remedy() {
    let f = tick004(
        "tickets/X/events/E.toml",
        b"reason = \"lease: a in /home/name/p\"\n",
    )
    .expect("finding");
    assert_eq!(f.rule.as_str(), "TICK004");
    assert!(
        f.message.contains("tickets/X/events/E.toml"),
        "{}",
        f.message
    );
    assert!(f.message.contains("~/"), "remedy: {}", f.message);
    assert!(
        tick004(
            "tickets/X/events/E.toml",
            b"reason = \"lease: a in repo-wt/X\"\n"
        )
        .is_none()
    );
}

/// The ledger walk reports the committed file that holds a home path and nothing for a clean ledger.
// frob:tests crates/frob-ledger/src/privacy.rs::Ledger.home_path_findings
#[test]
fn ledger_walk_reports_only_dirty_files() {
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = Repo::init(dir.path()).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir.path()).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hello\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(repo, LedgerConfig::default());
    ledger
        .new_ticket(NewTicket::new("Clean", TicketType::Task))
        .expect("clean");
    assert!(ledger.home_path_findings().expect("scan").is_empty());
    let mut dirty = NewTicket::new("Dirty", TicketType::Task);
    dirty.body = "see /home/name/projects/x".to_owned();
    let id = ledger.new_ticket(dirty).expect("dirty").ticket.front.id;
    let found = ledger.home_path_findings().expect("scan");
    assert_eq!(
        found.len(),
        2,
        "the creation event and ticket.md: {found:?}"
    );
    for f in &found {
        assert_eq!(f.rule.as_str(), "TICK004");
        assert!(f.message.contains(&id.to_string()), "{}", f.message);
    }
}

/// `TICK004` is an Error, and its message names the repair verb.
// frob:tests crates/frob-ledger/src/privacy.rs::tick004
#[test]
fn tick004_is_an_error_naming_the_repair() {
    let f = tick004("tickets/X/ticket.md", b"in /home/name/p").expect("finding");
    assert_eq!(f.severity, gob_rules::Severity::Error);
    assert!(f.message.contains("ticket doctor --fix"), "{}", f.message);
}

/// The root range covers `/home/<name>` and its Windows and `/root` spellings, not the rest of the path.
// frob:tests crates/frob-ledger/src/privacy.rs::find_home_root
#[test]
fn home_root_range_stops_after_the_user_name() {
    for (text, root) in [
        ("at /home/ann/projects/x", "/home/ann"),
        ("/Users/bob.k/Library", "/Users/bob.k"),
        ("cd /root/work", "/root"),
        ("C:\\Users\\bo\\proj", "C:\\Users\\bo"),
        (
            "C:\\Users\\bo\\proj".replace("\\\\", "\\").as_str(),
            "C:\\Users\\bo",
        ),
        ("d:/Users/bo/proj", "d:/Users/bo"),
    ] {
        let r = find_home_root(text.as_bytes()).expect(text);
        assert_eq!(&text[r], root, "{text}");
    }
    assert!(find_home_root(b"~/projects /home/<user>/x").is_none());
}

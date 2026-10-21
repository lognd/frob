//! The `unity` pack's `.meta` pairing and guid rules: UNITY001, UNITY002, UNITY003 (~TAWMMAV).

mod common;

use frob_obligations::InvariantsConfig;
use gob_git::{CommitOptions, RelPath, Repo};
use gob_rules::{Finding, Severity};

const ENABLED: &str = "[[packs.enable]]\nname = \"unity\"\n";
const G1: &str = "0123456789abcdef0123456789abcdef";
const G2: &str = "fedcba9876543210fedcba9876543210";

/// A `.meta` body carrying `guid`.
fn meta(guid: &str) -> String {
    format!("fileFormatVersion: 2\nguid: {guid}\n")
}

/// Evaluate `files` under a fresh tree (walk fallback, no git) and return the `rule` findings.
fn run(files: &[(&str, &str)], enabled: bool, rule: &str) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), files);
    if enabled {
        common::write_tree(dir.path(), &[("frob.toml", ENABLED)]);
    }
    let cfg = InvariantsConfig::load(dir.path()).expect("cfg");
    common::evaluate_tree(dir.path(), None, &cfg, None)
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == rule)
        .collect()
}

/// Messages of `findings`.
fn msgs(findings: &[Finding]) -> Vec<&str> {
    findings.iter().map(|f| f.message.as_str()).collect()
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity001
#[test]
fn unity001_names_a_tracked_asset_without_a_meta() {
    let m = meta(G1);
    let f = run(
        &[
            ("Assets/Hero.cs", "class Hero {}"),
            ("Assets/Ok.cs", "class Ok {}"),
            ("Assets/Ok.cs.meta", &m),
        ],
        true,
        "UNITY001",
    );
    let got = msgs(&f);
    assert!(got.iter().any(|m| m.contains("Assets/Hero.cs")), "{got:?}");
    assert!(!got.iter().any(|m| m.contains("Assets/Ok.cs`")), "{got:?}");
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity001
#[test]
fn unity001_requires_a_meta_for_folders() {
    let m = meta(G1);
    let f = run(
        &[("Assets/Dir/A.cs", "x"), ("Assets/Dir/A.cs.meta", &m)],
        true,
        "UNITY001",
    );
    let got = msgs(&f);
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("`Assets/Dir`"), "{got:?}");
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity001
#[test]
fn unity001_exempts_dot_tilde_cvs_and_tmp_names() {
    let f = run(
        &[
            ("Assets/.hidden.cs", "x"),
            ("Assets/backup~", "x"),
            ("Assets/cvs/a.txt", "x"),
            ("Assets/scratch.tmp", "x"),
            ("Assets/Docs~/readme.md", "x"),
        ],
        true,
        "UNITY001",
    );
    assert!(f.is_empty(), "{:?}", msgs(&f));
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity001
#[test]
fn unity001_covers_embedded_packages_only() {
    let m = meta(G1);
    let f = run(
        &[
            ("Packages/manifest.json", "{}"),
            ("Packages/packages-lock.json", "{}"),
            ("Packages/com.x.emb/package.json", "{}"),
            ("Packages/com.x.emb/Runtime/A.cs", "x"),
            ("Packages/com.x.emb/Runtime/A.cs.meta", &m),
            ("Packages/other/Loose.cs", "x"),
        ],
        true,
        "UNITY001",
    );
    let got = msgs(&f);
    assert!(
        got.iter()
            .any(|m| m.contains("Packages/com.x.emb/package.json")),
        "{got:?}"
    );
    assert!(
        got.iter()
            .any(|m| m.contains("`Packages/com.x.emb/Runtime`")),
        "{got:?}"
    );
    assert!(
        !got.iter()
            .any(|m| m.contains("manifest") || m.contains("lock") || m.contains("other")),
        "{got:?}"
    );
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity002
#[test]
fn unity002_flags_a_meta_without_an_asset() {
    let m = meta(G1);
    let n = meta(G2);
    let f = run(
        &[
            ("Assets/Gone.cs.meta", &m),
            ("Assets/Here.cs", "x"),
            ("Assets/Here.cs.meta", &n),
            ("Assets.meta", &n.replace('f', "e")),
        ],
        true,
        "UNITY002",
    );
    let got = msgs(&f);
    assert_eq!(got.len(), 1, "{got:?}");
    assert!(got[0].contains("Assets/Gone.cs.meta"), "{got:?}");
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity003
#[test]
fn unity003_names_both_files_as_an_error() {
    let m = meta(G1);
    let f = run(
        &[("Assets/A.cs.meta", &m), ("Assets/B.cs.meta", &m)],
        true,
        "UNITY003",
    );
    assert_eq!(f.len(), 1, "{:?}", msgs(&f));
    assert_eq!(f[0].severity, Severity::Error);
    assert!(f[0].message.contains("Assets/A.cs.meta") && f[0].message.contains("Assets/B.cs.meta"));
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity003
#[test]
fn unity003_names_all_three_files_of_a_triple() {
    let m = meta(G1);
    let f = run(
        &[
            ("Assets/A.cs.meta", &m),
            ("Assets/B.cs.meta", &m),
            (
                "Assets/C.cs.meta",
                &m.to_uppercase().replace("GUID", "guid"),
            ),
        ],
        true,
        "UNITY003",
    );
    assert_eq!(f.len(), 1, "{:?}", msgs(&f));
    for n in ["A", "B", "C"] {
        assert!(
            f[0].message.contains(&format!("Assets/{n}.cs.meta")),
            "{}",
            f[0].message
        );
    }
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity003
#[test]
fn unity003_reports_a_malformed_guid_as_unresolved() {
    let f = run(
        &[
            ("Assets/A.cs.meta", "guid: nope\n"),
            ("Assets/B.cs.meta", "fileFormatVersion: 2\n"),
        ],
        true,
        "UNITY003",
    );
    assert_eq!(f.len(), 2, "{:?}", msgs(&f));
    assert!(f.iter().all(|x| x.severity == Severity::Unresolved));
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity001
// frob:tests unity002
// frob:tests unity003
#[test]
fn the_rules_are_silent_when_the_pack_is_disabled() {
    let m = meta(G1);
    let files = [
        ("Assets/Hero.cs", "x"),
        ("Assets/Gone.cs.meta", &m),
        ("Assets/Twin.cs.meta", &m),
    ];
    for rule in ["UNITY001", "UNITY002", "UNITY003"] {
        assert!(run(&files, false, rule).is_empty(), "{rule}");
    }
}

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
// frob:tests unity001
// frob:tests unity002
#[test]
fn only_git_tracked_files_count() {
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
    let m = meta(G1);
    let tracked: Vec<(RelPath, Option<Vec<u8>>)> = [
        ("frob.toml", ENABLED.to_owned()),
        ("Assets/Tracked.cs", "x".to_owned()),
        ("Assets/Orphan.cs.meta", m.clone()),
    ]
    .into_iter()
    .map(|(p, t)| (RelPath::new(p).expect("path"), Some(t.into_bytes())))
    .collect();
    repo.commit_paths(
        "refs/heads/main",
        &tracked,
        "files",
        &CommitOptions::default(),
    )
    .expect("commit");
    // On disk but never committed: the stray asset must not fire, and its meta must not pair.
    common::write_tree(
        dir.path(),
        &[
            ("frob.toml", ENABLED),
            ("Assets/Stray.cs", "x"),
            ("Assets/Tracked.cs", "x"),
            ("Assets/Orphan.cs.meta", &m),
            ("Assets/Orphan.cs", "x"),
        ],
    );
    let cfg = InvariantsConfig::load(dir.path()).expect("cfg");
    let all = common::evaluate_tree(dir.path(), None, &cfg, None).findings;
    let pick = |rule: &str| -> Vec<String> {
        all.iter()
            .filter(|f| f.rule.as_str() == rule)
            .map(|f| f.message.clone())
            .collect()
    };
    let one = pick("UNITY001");
    assert!(
        one.iter().any(|m| m.contains("Assets/Tracked.cs")),
        "{one:?}"
    );
    assert!(!one.iter().any(|m| m.contains("Stray")), "{one:?}");
    let two = pick("UNITY002");
    assert!(
        two.iter().any(|m| m.contains("Assets/Orphan.cs.meta")),
        "{two:?}"
    );
}

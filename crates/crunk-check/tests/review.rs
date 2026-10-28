//! The human review lock through `crunk check`: a token change makes HUMAN001 name the screen and
//! the token until a new ack, the release gate raises it, and `require_signed` judges the commit.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use crunk_rules::review::ReviewStatus::{Current, Unsigned};
use std::path::Path;

use crunk_check::review::{self, AckRequest, SignatureSource};
use crunk_check::{CheckOptions, run};
use crunk_rules::family::Gate;
use crunk_rules::review::AckSignature;
use gob_lock::{LockFile, ReviewVerdict};
use gob_rules::Severity;

struct Fixed(AckSignature);

impl SignatureSource for Fixed {
    fn signature(&self, _digest: &str) -> AckSignature {
        self.0.clone()
    }
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

fn spec_text(accent: &str, review: &str) -> String {
    let base = crunk_spec::presets::preset("default")
        .expect("default preset")
        .replace("#2f6fed", accent);
    format!(
        "{base}\n[[screen]]\nid = \"home\"\nentry = \"/\"\nreview = \"human\"\nsources = [\"src/home.css\"]\n[[screen.states]]\nid = \"default\"\n{review}"
    )
}

fn project(accent: &str, review: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", &spec_text(accent, review));
    write(dir.path(), "styles/base/a.css", ".a { margin: 0; }\n");
    write(
        dir.path(),
        "src/home.css",
        ".home { color: var(--color-accent); }\n",
    );
    dir
}

fn human(dir: &Path, gate: Gate) -> Vec<gob_rules::Finding> {
    let opts = CheckOptions {
        gate,
        ..CheckOptions::default()
    };
    run(dir, &opts)
        .expect("run")
        .report
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "HUMAN001")
        .collect()
}

fn ack(dir: &Path, who: &str) {
    let spec = crunk_spec::load_spec(dir).expect("spec");
    let subjects = review::subjects(&spec).expect("subjects");
    let path = review::lock_path(dir);
    let mut lock = LockFile::load(&path).expect("lock");
    let req = AckRequest {
        subjects: Vec::new(),
        all_stale: true,
        verdict: ReviewVerdict::Approved,
        reviewer: who.to_owned(),
        at: "2026-10-13T00:00:00Z".to_owned(),
        note: None,
        non_interactive: false,
    };
    review::record(&mut lock, &spec, &subjects, &req).expect("record");
    lock.save(&path).expect("save");
}

// frob:tests crates/crunk-check/src/review.rs::gather
#[test]
fn a_changed_token_makes_human001_name_the_screen_and_token_until_acked_again() {
    let dir = project("#2f6fed", "");
    let first = human(dir.path(), Gate::Check);
    assert_eq!(first.len(), 1, "{first:?}");
    assert!(first[0].message.contains("no recorded human review"));
    ack(dir.path(), "Alice <alice@example.com>");
    assert!(human(dir.path(), Gate::Check).is_empty());

    write(dir.path(), "crunk.toml", &spec_text("#2f6fee", ""));
    let stale = human(dir.path(), Gate::Check);
    assert_eq!(stale.len(), 1, "{stale:?}");
    assert_eq!(stale[0].severity, Severity::Error);
    assert!(stale[0].message.contains("`home`"), "{}", stale[0].message);
    assert!(
        stale[0].message.contains("token:--color-accent"),
        "{}",
        stale[0].message
    );

    ack(dir.path(), "Alice <alice@example.com>");
    assert!(human(dir.path(), Gate::Check).is_empty());
}

// frob:tests crates/crunk-check/src/review.rs::gather
#[test]
fn a_token_the_screen_does_not_use_does_not_make_it_stale() {
    let dir = project("#2f6fed", "");
    ack(dir.path(), "Alice <alice@example.com>");
    write(
        dir.path(),
        "crunk.toml",
        &spec_text("#2f6fed", "").replace("paper = \"#fafaf7\"", "paper = \"#fafaf8\""),
    );
    assert!(human(dir.path(), Gate::Check).is_empty());
}

// frob:tests crates/crunk-rules/src/family.rs::apply_gate
#[test]
fn the_release_gate_raises_a_stale_review_to_an_error_that_fails_the_run() {
    let dir = project("#2f6fed", "");
    let at_check = human(dir.path(), Gate::Check);
    assert_eq!(at_check[0].severity, Severity::Error);
    let opts = CheckOptions {
        gate: Gate::Release,
        ..CheckOptions::default()
    };
    let report = run(dir.path(), &opts).expect("run").report;
    let raised: Vec<_> = report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "HUMAN001")
        .collect();
    assert_eq!(raised[0].severity, Severity::Error);
    assert_eq!(report.exit_code(), gob_diagnostics::ExitCode::Negative);
}

const SIGNED: &str = "\n[review]\nrequire_signed = true\n[[review.reviewers]]\nid = \"alice@example.com\"\nkeys = [\"AAAA1111\"]\n";

// frob:tests crates/crunk-check/src/review.rs::gather
#[test]
fn require_signed_judges_the_commit_that_introduced_the_ack() {
    let dir = project("#2f6fed", SIGNED);
    ack(dir.path(), "Alice <alice@example.com>");
    let spec = crunk_spec::load_spec(dir.path()).expect("spec");
    let verdict = |sig: AckSignature| {
        review::gather(&spec, &Fixed(sig))
            .findings
            .iter()
            .map(|f| f.status.clone())
            .collect::<Vec<_>>()
    };
    assert!(matches!(
        verdict(AckSignature::Unsigned("the commit is not signed".into()))[0],
        Unsigned(_)
    ));
    assert!(matches!(
        verdict(AckSignature::Good("BBBB2222".into()))[0],
        Unsigned(_)
    ));
    assert_eq!(verdict(AckSignature::Good("aaaa1111".into()))[0], Current);
}

// frob:tests crates/crunk-check/src/review.rs::parse_signature
#[test]
fn git_signature_status_letters_map_to_good_or_unsigned() {
    assert_eq!(
        review::parse_signature("G\u{1f}FPRINT\u{1f}KEY"),
        AckSignature::Good("FPRINT".into())
    );
    assert!(matches!(
        review::parse_signature("N\u{1f}\u{1f}"),
        AckSignature::Unsigned(_)
    ));
    assert!(matches!(
        review::parse_signature("B\u{1f}\u{1f}"),
        AckSignature::Unsigned(_)
    ));
}

// frob:tests crates/crunk-check/src/review.rs::record
#[test]
fn an_ack_by_an_unlisted_person_or_a_rejection_without_a_note_is_refused() {
    let dir = project("#2f6fed", SIGNED);
    let spec = crunk_spec::load_spec(dir.path()).expect("spec");
    let subjects = review::subjects(&spec).expect("subjects");
    let mut lock = LockFile::default();
    let mut req = AckRequest {
        subjects: Vec::new(),
        all_stale: true,
        verdict: ReviewVerdict::Approved,
        reviewer: "Mallory <mallory@example.com>".to_owned(),
        at: "t".to_owned(),
        note: None,
        non_interactive: false,
    };
    assert!(matches!(
        review::record(&mut lock, &spec, &subjects, &req),
        Err(review::AckRefusal::NotAReviewer(_))
    ));
    req.reviewer = "alice@example.com".to_owned();
    req.verdict = ReviewVerdict::Rejected;
    assert_eq!(
        review::record(&mut lock, &spec, &subjects, &req),
        Err(review::AckRefusal::NoteRequired)
    );
}

fn git(dir: &Path, args: &[&str]) {
    let out = std::process::Command::new("git")
        .args(["-c", "user.name=T", "-c", "user.email=t@example.com"])
        .args(["-c", "commit.gpgsign=false"])
        .args(args)
        .current_dir(dir)
        .output()
        .expect("git runs");
    assert!(
        out.status.success(),
        "{args:?}: {}",
        String::from_utf8_lossy(&out.stderr)
    );
}

// frob:tests crates/crunk-check/src/review.rs::GitSignatures
#[test]
fn git_signatures_find_the_commit_that_added_the_digest() {
    let dir = project("#2f6fed", SIGNED);
    git(dir.path(), &["init", "-q"]);
    ack(dir.path(), "Alice <alice@example.com>");
    let lock = LockFile::load(&review::lock_path(dir.path())).expect("lock");
    let digest = lock.reviews.values().next().expect("entry").digest.clone();
    let git_sigs = review::GitSignatures::new(dir.path());
    match git_sigs.signature(&digest) {
        AckSignature::Unsigned(why) => assert!(why.contains("not committed"), "{why}"),
        other @ AckSignature::Good(_) => panic!("{other:?}"),
    }
    git(dir.path(), &["add", "crunk.lock"]);
    git(dir.path(), &["commit", "-q", "-m", "ack"]);
    match git_sigs.signature(&digest) {
        AckSignature::Unsigned(why) => assert!(why.contains("not signed"), "{why}"),
        other @ AckSignature::Good(_) => panic!("{other:?}"),
    }
}

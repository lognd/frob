//! The `TICK004` repair: one forward commit that scrubs absolute home paths and keeps the fold identical.
// frob:ticket 01M41RHBJ03PGD6JY0J6JTAH9Q

use frob_ledger::event::{Event, EventBody, EvidenceData};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::scrub::{SCRUB_REASON, ScrubTools};
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use gob_git::{CommitOptions, RelPath, Repo};

/// A stand-in for blake3: deterministic and sensitive to every byte.
fn digest(b: &[u8]) -> String {
    format!(
        "d{}-{}",
        b.len(),
        b.iter().map(|x| u64::from(*x)).sum::<u64>()
    )
}

fn rewrite(t: &str) -> String {
    t.replace("/home/ann", "~")
}

fn fresh() -> Ledger {
    let dir = tempfile::tempdir().expect("tempdir").keep();
    let repo = Repo::init(&dir).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(&dir).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hi\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
}

/// Write `event` into ticket `id` as a raw commit, then re-fold the frontmatter.
fn push_event(ledger: &Ledger, id: TicketId, event: &Event) {
    let path = format!("tickets/{id}/events/{}", event.file_name());
    ledger
        .repo()
        .commit_paths(
            "refs/heads/main",
            &[(
                RelPath::new(path).expect("path"),
                Some(event.to_toml().expect("toml").into_bytes()),
            )],
            "test event",
            &CommitOptions::default(),
        )
        .expect("commit event");
    ledger.reconcile(id).expect("reconcile");
}

fn evidence(inline: &str, good_digest: bool, accepts: &[usize]) -> Event {
    let d = if good_digest {
        digest(inline.as_bytes())
    } else {
        "stale".to_owned()
    };
    let mut record = toml::Table::new();
    record.insert("provider".into(), "command".into());
    record.insert("ref".into(), "cargo test".into());
    record.insert("digest".into(), d.into());
    record.insert("status".into(), "measured".into());
    record.insert("passed".into(), true.into());
    record.insert("inline".into(), inline.into());
    record.insert(
        "size".into(),
        i64::try_from(inline.len()).expect("len").into(),
    );
    Event::new(
        gob_time::Clock::now(&gob_time::SystemClock),
        "ann",
        EventBody::Evidence(EvidenceData {
            accepts: accepts.to_vec(),
            record,
        }),
    )
}

fn tools() -> ScrubTools<'static> {
    ScrubTools {
        rewrite: &rewrite,
        digest: &digest,
    }
}

fn tip(ledger: &Ledger) -> String {
    ledger.tip_hex().expect("tip").expect("some")
}

struct Fixture {
    ledger: Ledger,
    id: TicketId,
    old_ev: String,
}

fn fixture() -> Fixture {
    let ledger = fresh();
    let mut req = NewTicket::new("Dirty", TicketType::Task);
    "built in /home/ann/work/app\n".clone_into(&mut req.body);
    req.acceptance = vec!["it works".to_owned(), "it is fast".to_owned()];
    let id = ledger.new_ticket(req).expect("ticket").ticket.front.id;
    let ev = evidence("Compiling x (/home/ann/work/app/x)\nok\n", true, &[1]);
    let old_ev = format!("tickets/{id}/events/{}", ev.file_name());
    push_event(&ledger, id, &ev);
    let now = gob_time::Clock::now(&gob_time::SystemClock);
    let lease = format!(
        "kind = \"lease\"\nat = \"{now}\"\nactor = \"a\"\nrev = 1\nreason = \"lease: ann in /home/ann/work/app-wt/T1; scope: x\"\n"
    );
    let lease_ev = Event::parse(frob_ledger::EventId::mint(), &lease).expect("lease");
    push_event(&ledger, id, &lease_ev);
    Fixture { ledger, id, old_ev }
}

/// One commit scrubs the files, every digest still covers its text, the fold is the same but for the text, and TICK004 is silent.
// frob:tests crates/frob-ledger/src/scrub.rs::Ledger.scrub
#[test]
fn one_commit_scrubs_and_the_ledger_still_folds() {
    let f = fixture();
    let before_tip = tip(&f.ledger);
    let before = f
        .ledger
        .read_ticket_at(&before_tip, f.id)
        .expect("read")
        .expect("some");
    assert!(!f.ledger.home_path_findings().expect("scan").is_empty());

    let report = f.ledger.scrub(&tools()).expect("scrub");
    assert_eq!(report.tickets, vec![f.id]);
    assert_eq!(report.digests, 1, "{report:?}");
    assert!(report.unresolved.is_empty(), "{report:?}");
    assert!(
        report.files.iter().any(|p| p.ends_with("ticket.md")),
        "{report:?}"
    );
    assert!(report.files.contains(&f.old_ev), "{report:?}");
    let commit = report.commit.expect("a commit");
    assert_eq!(tip(&f.ledger), commit);
    // One forward commit: the old tip is its parent and still readable.
    let parent = f
        .ledger
        .repo()
        .rev_parse(&format!("{commit}^"))
        .expect("parent");
    assert_eq!(parent.to_string(), before_tip);

    assert!(f.ledger.home_path_findings().expect("scan").is_empty());
    let doctor = f.ledger.doctor(false).expect("doctor");
    assert!(
        doctor.is_clean(),
        "{:?} {:?}",
        doctor.findings,
        doctor.issues
    );

    let after = f
        .ledger
        .read_ticket_at(&commit, f.id)
        .expect("read")
        .expect("some");
    assert_eq!(after.body, before.body.replace("/home/ann", "~"));
    assert_eq!(
        after.front.acceptance, before.front.acceptance,
        "binding per criterion"
    );
    assert!(after.front.acceptance[0].bound && !after.front.acceptance[1].bound);
    assert_eq!(
        after.front.updated, before.front.updated,
        "a scrub does not touch updated"
    );
    assert_eq!(after.front.category, before.front.category);

    let text = f
        .ledger
        .repo()
        .read_blob_at(&commit, &f.old_ev)
        .expect("blob")
        .expect("file");
    let table: toml::Table = String::from_utf8(text)
        .expect("utf8")
        .parse()
        .expect("toml");
    let inline = table["inline"].as_str().expect("inline");
    assert!(inline.contains("~/work/app/x") && !inline.contains("/home/ann"));
    assert_eq!(
        table["digest"].as_str(),
        Some(digest(inline.as_bytes()).as_str())
    );
    assert_eq!(table["size"].as_integer(), i64::try_from(inline.len()).ok());

    let events = f.ledger.read_events_at(&commit, f.id).expect("events");
    let scrub = events
        .iter()
        .find_map(|e| match &e.body {
            EventBody::Scrub(d) => Some(d),
            _ => None,
        })
        .expect("scrub event");
    assert_eq!(scrub.reason, SCRUB_REASON);
    assert_eq!(scrub.digests.len(), 1);
    assert!(scrub.files.contains(&f.old_ev));
}

/// A second run changes nothing and makes no commit.
#[test]
fn second_run_is_a_no_op() {
    let f = fixture();
    f.ledger.scrub(&tools()).expect("first");
    let settled = tip(&f.ledger);
    let again = f.ledger.scrub(&tools()).expect("second");
    assert_eq!(again, frob_ledger::scrub::ScrubReport::default());
    assert_eq!(tip(&f.ledger), settled);
}

/// A rewrite that cannot clear a path leaves the file alone and reports it.
#[test]
fn survivors_are_reported_not_guessed() {
    let f = fixture();
    let before_tip = tip(&f.ledger);
    let id_rewrite = |t: &str| t.to_owned();
    let none = ScrubTools {
        rewrite: &id_rewrite,
        digest: &digest,
    };
    let report = f.ledger.scrub(&none).expect("scrub");
    assert!(report.files.is_empty() && report.commit.is_none());
    assert!(!report.unresolved.is_empty());
    assert_eq!(tip(&f.ledger), before_tip);
}

/// A record whose digest never matched its text keeps its digest: the repair does not mask damage.
#[test]
fn a_digest_that_never_matched_is_left_alone() {
    let ledger = fresh();
    let id = ledger
        .new_ticket(NewTicket::new("T", TicketType::Task))
        .expect("ticket")
        .ticket
        .front
        .id;
    let ev = evidence("at /home/ann/x\n", false, &[]);
    push_event(&ledger, id, &ev);
    let report = ledger.scrub(&tools()).expect("scrub");
    assert_eq!(report.digests, 0, "{report:?}");
    let commit = report.commit.expect("commit");
    let path = format!("tickets/{id}/events/{}", ev.file_name());
    let text = ledger
        .repo()
        .read_blob_at(&commit, &path)
        .expect("blob")
        .expect("file");
    let table: toml::Table = String::from_utf8(text)
        .expect("utf8")
        .parse()
        .expect("toml");
    assert_eq!(table["digest"].as_str(), Some("stale"));
}

// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72
const TERM: &str = "zorblax-7";

fn with_rule(ledger: Ledger) -> Ledger {
    let rules = frob_ledger::redact::RuleSet::from_toml(
        &format!("[[rule]]\npattern = \"{TERM}\"\nreplace = \"<private-host>\"\n"),
        "test",
    )
    .expect("rules");
    ledger.with_redaction(rules)
}

/// Writing text with a private term is refused, naming the label and not the term, and writes nothing.
// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.refuse_private
#[test]
fn write_with_a_private_term_is_refused() {
    let ledger = with_rule(fresh());
    let before = ledger.tip_hex().expect("tip");
    let mut req = NewTicket::new(format!("run on {TERM}"), TicketType::Task);
    req.acceptance = vec!["ok".to_owned()];
    let err = ledger.new_ticket(req).expect_err("refused");
    let text = err.to_string();
    assert!(
        text.contains("<private-host>") && !text.contains(TERM),
        "{text}"
    );
    let refusal = err.to_refusal().expect("refusal");
    assert!(!format!("{refusal:?}").contains(TERM));
    assert_eq!(ledger.tip_hex().expect("tip"), before);
}

/// Doctor-fix scrub replaces the term everywhere in one commit, recomputes digests, audits without the term, and is idempotent; TICK005 flags before and is silent after.
// frob:tests crates/frob-ledger/src/scrub.rs::Ledger.scrub
// frob:tests crates/frob-ledger/src/privacy.rs::Ledger.private_term_findings
#[test]
fn private_terms_are_scrubbed_like_home_paths() {
    let plain = fresh();
    let mut req = NewTicket::new("Clean title", TicketType::Task);
    req.acceptance = vec!["it works".to_owned()];
    req.body = format!("seen on {TERM}\n");
    let id = plain.new_ticket(req).expect("ticket").ticket.front.id;
    let ev = evidence(&format!("ran on {TERM}\nok\n"), true, &[1]);
    push_event(&plain, id, &ev);
    let ledger = with_rule(plain);
    assert!(!ledger.private_term_findings().expect("scan").is_empty());
    let base = tip(&ledger);

    let report = ledger.scrub(&tools()).expect("scrub");
    assert!(report.unresolved.is_empty(), "{report:?}");
    assert_eq!(report.digests, 1);
    assert_ne!(tip(&ledger), base);
    let parents = ledger
        .repo()
        .rev_parse(&format!("{}^", tip(&ledger)))
        .expect("parent");
    assert_eq!(parents.to_string(), base);
    assert!(ledger.private_term_findings().expect("scan").is_empty());
    for e in ledger.events(id).expect("events") {
        let text = e.to_toml().expect("toml");
        assert!(!text.contains(TERM), "{text}");
    }
    let audit: Vec<String> = ledger
        .events(id)
        .expect("events")
        .iter()
        .map(|e| e.to_toml().expect("toml"))
        .filter(|t| t.contains("kind = \"scrub\""))
        .collect();
    assert_eq!(audit.len(), 1);
    assert!(audit[0].contains("<private-host>#"), "{}", audit[0]);

    let again = ledger.scrub(&tools()).expect("again");
    assert!(again.commit.is_none() && again.files.is_empty());
}

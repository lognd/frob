//! The baseline store, adopt/prune, BASE001/BASE002 and the ratchet migration (~7FDF275).

// frob:ticket 01M5XMJH35MV9Z2PFF27FDF275

use std::collections::BTreeSet;

use gob_rules::rules::base001::Base001;
use gob_rules::rules::base002::Base002;
use gob_rules::{
    BASELINE_FILE, Baseline, BaselineError, BaselineHost, Finding, PruneInput, RuleDecl, RuleId,
    Severity, TicketLife, dead_tables, growth, migrate_ratchet_lock, run_repo,
};

fn rid(s: &str) -> RuleId {
    s.parse().unwrap()
}

fn finding(rule: &str, anchor: &str, sev: Severity) -> Finding {
    Finding::new(rid(rule), sev, None, "msg", anchor)
}

fn adopted(rule: &str, anchors: &[&str], ticket: &str) -> Baseline {
    let fs: Vec<Finding> = anchors
        .iter()
        .map(|a| finding(rule, a, Severity::Error))
        .collect();
    let mut b = Baseline::default();
    b.adopt(&rid(rule), "adopting the rule", ticket, &fs)
        .unwrap();
    b
}

#[test]
fn adopt_writes_sorted_toml_keyed_by_fingerprint_and_round_trips() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let b = adopted("PM009", &["b", "a", "c"], "~61BXXNJ");
    let text = b.render();
    assert!(text.starts_with("version = 1\n\n[rules.PM009]\nreason = "));
    let keys = &b.rules["PM009"].findings;
    assert_eq!(keys.len(), 3);
    assert!(keys.windows(2).all(|w| w[0] < w[1]), "sorted and unique");
    assert!(keys.contains(&finding("PM009", "a", Severity::Error).fingerprint.to_hex()));
    assert_eq!(Baseline::parse(&text).unwrap(), b);
    assert_eq!(Baseline::parse(&text).unwrap().render(), text);
}

#[test]
fn adopt_refuses_an_existing_table_and_an_empty_pool() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let mut b = adopted("PM009", &["a"], "~T1");
    let f = [finding("PM009", "z", Severity::Error)];
    assert_eq!(
        b.adopt(&rid("PM009"), "r", "~T1", &f),
        Err(BaselineError::AlreadyAdopted("PM009".into()))
    );
    let unresolved = [finding("PM010", "z", Severity::Unresolved)];
    assert!(matches!(
        b.adopt(&rid("PM010"), "r", "~T1", &unresolved),
        Err(BaselineError::NothingToAdopt(_))
    ));
    assert!(matches!(
        b.adopt(&rid("PM010"), " ", "~T1", &f),
        Err(BaselineError::Missing {
            field: "reason",
            ..
        })
    ));
}

#[test]
fn a_conflicted_or_malformed_file_is_a_hard_error() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let text = adopted("PM009", &["a"], "~T1").render();
    let conflicted = text.replace("version = 1\n", "version = 1\n<<<<<<< HEAD\n");
    assert!(matches!(
        Baseline::parse(&conflicted),
        Err(BaselineError::Conflict { line: 2 })
    ));
    assert!(matches!(
        Baseline::parse("version = 2\n"),
        Err(BaselineError::Version(2))
    ));
    assert!(matches!(
        Baseline::parse(
            "version = 1\n[rules.PM009]\nreason = \"r\"\nticket = \"\"\nfindings = []\n"
        ),
        Err(BaselineError::Missing {
            field: "ticket",
            ..
        })
    ));
    assert!(matches!(
        Baseline::parse(
            "version = 1\n[rules.PM009]\nreason = \"r\"\nticket = \"t\"\nfindings = [\"xyz\"]\n"
        ),
        Err(BaselineError::BadKey { .. })
    ));
}

#[test]
fn covers_mutes_only_decided_errors_of_a_listed_fingerprint() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let b = adopted("PM009", &["a"], "~T1");
    let hit = finding("PM009", "a", Severity::Error);
    let new = finding("PM009", "other", Severity::Error);
    let unresolved = finding("PM009", "a", Severity::Unresolved);
    let (live, muted) = b.partition(vec![hit, new.clone(), unresolved.clone()]);
    assert_eq!(muted.len(), 1);
    assert_eq!(live, vec![new, unresolved]);
    assert_eq!(b.remaining()["PM009"], 1);
}

#[test]
fn prune_removes_gone_keys_deletes_empty_tables_and_never_adds() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let mut b = adopted("PM009", &["a", "b"], "~T1");
    let keep = finding("PM009", "a", Severity::Error).fingerprint.to_hex();
    let mut input = PruneInput {
        live: BTreeSet::from([keep.clone(), "f".repeat(64)]),
        evaluated: BTreeSet::from(["PM009".to_owned()]),
        full_run: true,
    };
    let before = b.clone();
    let r = b.prune(&input);
    assert_eq!(r.removed.len(), 1);
    assert_eq!(b.rules["PM009"].findings, vec![keep]);
    assert!(b.key_count() <= before.key_count(), "prune never adds");
    input.live.clear();
    let r = b.prune(&input);
    assert_eq!(r.tables_deleted, vec!["PM009".to_owned()]);
    assert!(b.rules.is_empty());
}

#[test]
fn prune_skips_scoped_runs_unevaluated_rules_and_unresolved_sites() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let mut b = adopted("PM009", &["a"], "~T1");
    let scoped = PruneInput {
        full_run: false,
        evaluated: BTreeSet::from(["PM009".to_owned()]),
        ..PruneInput::default()
    };
    assert!(b.prune(&scoped).removed.is_empty());
    let skipped = PruneInput {
        full_run: true,
        ..PruneInput::default()
    };
    assert!(b.prune(&skipped).removed.is_empty());
    let unresolved_live = PruneInput {
        full_run: true,
        evaluated: BTreeSet::from(["PM009".to_owned()]),
        live: BTreeSet::from([finding("PM009", "a", Severity::Unresolved)
            .fingerprint
            .to_hex()]),
    };
    assert!(b.prune(&unresolved_live).removed.is_empty());
    assert_eq!(b.key_count(), 1);
}

#[test]
fn intersect_base_drops_keys_the_base_already_pruned() {
    // frob:tests crates/gob-rules/src/baseline.rs::Baseline
    let base = adopted("PM009", &["a"], "~T1");
    let mut head = adopted("PM009", &["a", "b"], "~T1");
    head.intersect_base(&base);
    assert_eq!(head, base);
}

#[test]
fn growth_flags_added_keys_and_ticket_changes_but_not_removals_or_new_tables() {
    // frob:tests crates/gob-rules/src/baseline.rs::growth
    let base = adopted("PM009", &["a", "b"], "~T1");
    assert!(growth(&base, &adopted("PM009", &["a"], "~T1")).is_empty());
    let mut with_new_table = base.clone();
    with_new_table
        .rules
        .extend(adopted("PM010", &["x"], "~T2").rules);
    assert!(growth(&base, &with_new_table).is_empty());
    let g = growth(&base, &adopted("PM009", &["a", "b", "c"], "~T1"));
    assert_eq!((g.len(), g[0].added.len()), (1, 1));
    let g = growth(&base, &adopted("PM009", &["a", "b"], "~T9"));
    assert_eq!(g[0].ticket_changed, Some(("~T1".into(), "~T9".into())));
}

#[test]
fn dead_tables_lists_every_non_live_ticket() {
    // frob:tests crates/gob-rules/src/baseline.rs::dead_tables
    let mut b = adopted("PM009", &["a"], "~DEAD");
    b.rules.extend(adopted("PM010", &["a"], "~LIVE").rules);
    b.rules.extend(adopted("PM011", &["a"], "~??").rules);
    let out = dead_tables(&b, |t| match t {
        "~LIVE" => TicketLife::Live,
        "~DEAD" => TicketLife::Dead,
        _ => TicketLife::Unknown,
    });
    let got: Vec<_> = out.iter().map(|(r, _, l)| (r.as_str(), *l)).collect();
    assert_eq!(
        got,
        [("PM009", TicketLife::Dead), ("PM011", TicketLife::Unknown)]
    );
}

#[test]
fn the_ratchet_lock_migrates_once_keeping_its_keys() {
    // frob:tests crates/gob-rules/src/baseline.rs::migrate_ratchet_lock
    let k = "a".repeat(64);
    let lock = format!(r#"{{"pools": {{"PM009": ["{k}"], "PM010": []}}}}"#);
    let b = migrate_ratchet_lock(&lock, None, "migrated from the ratchet lock", "~T1").unwrap();
    assert_eq!(b.rules.len(), 1);
    assert_eq!(b.rules["PM009"].findings, vec![k]);
    assert_eq!(
        migrate_ratchet_lock(&lock, Some(&b), "r", "~T1"),
        Err(BaselineError::AlreadyMigrated)
    );
    assert!(matches!(
        migrate_ratchet_lock("[1]", None, "r", "~T1"),
        Err(BaselineError::BadLock(_))
    ));
}

struct Host {
    head: Option<Baseline>,
    base: Option<Baseline>,
    dead: &'static str,
}

impl BaselineHost for Host {
    fn baseline_head(&self) -> Option<&Baseline> {
        self.head.as_ref()
    }
    fn baseline_base(&self) -> Option<&Baseline> {
        self.base.as_ref()
    }
    fn ticket_life(&self, ticket: &str) -> TicketLife {
        if ticket == self.dead {
            TicketLife::Dead
        } else {
            TicketLife::Live
        }
    }
}

#[test]
fn base001_fails_key_growth_versus_the_base_tip() {
    // frob:tests crates/gob-rules/src/rules/base001.rs::Base001
    let host = Host {
        head: Some(adopted("PM009", &["a", "b"], "~T1")),
        base: Some(adopted("PM009", &["a"], "~T1")),
        dead: "",
    };
    let out = run_repo(&Base001, &host);
    assert_eq!(out.len(), 1);
    assert_eq!(
        (out[0].rule, out[0].path.as_deref()),
        ("BASE001", Some(BASELINE_FILE))
    );
    let shrunk = Host {
        head: host.base.clone(),
        base: host.head.clone(),
        dead: "",
    };
    assert!(run_repo(&Base001, &shrunk).is_empty());
    let no_base = Host {
        head: host.head.clone(),
        base: None,
        dead: "",
    };
    assert!(run_repo(&Base001, &no_base).is_empty());
    assert_eq!(Base001::DEF.id, "BASE001");
}

#[test]
fn base002_fails_a_table_without_a_live_ticket() {
    // frob:tests crates/gob-rules/src/rules/base002.rs::Base002
    let host = Host {
        head: Some(adopted("PM009", &["a"], "~T1")),
        base: None,
        dead: "~T1",
    };
    let out = run_repo(&Base002, &host);
    assert_eq!(out.len(), 1);
    assert!(!out[0].unresolved);
    let live = Host {
        dead: "~other",
        ..host
    };
    assert!(run_repo(&Base002, &live).is_empty());
    assert_eq!(Base002::DEF.id, "BASE002");
}

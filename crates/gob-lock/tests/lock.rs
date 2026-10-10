//! Round trip, atomic save, missing file and diff behavior of `gob-lock`.

use gob_lock::{
    Current, CurrentFlow, CurrentSymbol, EntryKind, Facet, FacetSet, FlowEnd, FlowEntry, LockEntry,
    LockError, LockFile, LockTarget, PlanError, PlanOptions, diff, file_name, plan,
};

fn entry(sig: &str) -> LockEntry {
    LockEntry::new(sig, "b", "d", "Me <me@example.com>", "2026-10-02T00:00:00Z")
}

#[test]
fn file_name_is_product_dot_lock() {
    assert_eq!(file_name("frob"), "frob.lock");
    assert_eq!(file_name("grimble"), "grimble.lock");
}

#[test]
fn save_load_round_trips_and_is_sorted_and_stable() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("frob.lock");
    let mut lock = LockFile::default();
    lock.entries.insert("z.rs::z".to_owned(), entry("1"));
    let mut a = entry("2");
    a.reason = Some("reviewed the contract".to_owned());
    a.targets.push(LockTarget {
        target: "docs/a.md#intro".to_owned(),
        digest: "ff".to_owned(),
    });
    lock.entries.insert("a.rs::a".to_owned(), a);
    lock.save(&path).unwrap();
    let first = std::fs::read_to_string(&path).unwrap();
    assert!(first.find("a.rs::a").unwrap() < first.find("z.rs::z").unwrap());
    assert!(first.ends_with('\n'));
    let back = LockFile::load(&path).unwrap();
    assert_eq!(back, lock);
    back.save(&path).unwrap();
    assert_eq!(std::fs::read_to_string(&path).unwrap(), first);
    assert!(!dir.path().join("frob.lock.tmp").exists());
}

#[test]
fn missing_file_is_empty_and_garbage_is_an_error() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("frob.lock");
    assert!(LockFile::load(&path).unwrap().entries.is_empty());
    std::fs::write(&path, "not = [toml").unwrap();
    assert!(LockFile::load(&path).is_err());
    std::fs::write(&path, "version = 99\n").unwrap();
    assert!(LockFile::load(&path).is_err());
}

#[test]
fn diff_reports_added_removed_and_changed_facets() {
    let mut old = LockFile::default();
    old.entries.insert("a".to_owned(), entry("1"));
    old.entries.insert("gone".to_owned(), entry("1"));
    let mut new = old.clone();
    new.entries.remove("gone");
    new.entries.insert("new".to_owned(), entry("1"));
    new.entries.get_mut("a").unwrap().sig = "2".to_owned();
    let d = diff(&old, &new);
    assert_eq!(d.added, ["new"]);
    assert_eq!(d.removed, ["gone"]);
    assert_eq!(d.changed, [("a".to_owned(), vec![Facet::Sig])]);
    assert!(diff(&new, &new).is_empty());
}

const V1: &str = r#"version = 1

[entries."a.rs::a"]
sig = "11"
body = "22"
doc = "33"
acked_by = "Me"
acked_at = "2026-10-01T00:00:00Z"
reason = "old"

[[entries."a.rs::a".targets]]
ref = "docs/a.md#intro"
digest = "44"
"#;

// frob:tests crates/gob-lock/src/file.rs::LockFile
#[test]
fn version_one_file_loads_and_every_entry_needs_reattest() {
    let lock = LockFile::from_toml(V1).unwrap();
    assert_eq!((lock.version, lock.digest_scheme), (1, 1));
    assert_eq!(lock.entries["a.rs::a"].targets.len(), 1);
    assert!(lock.is_stale());
    let r = lock.reattest();
    assert_eq!(r.len(), 1);
    assert_eq!(
        (r[0].key.as_str(), r[0].kind),
        ("a.rs::a", EntryKind::Symbol)
    );
    assert!(r[0].why().contains("file version 1"), "{}", r[0].why());
    assert!(r[0].why().contains("digest scheme 1"), "{}", r[0].why());
    assert!(
        lock.to_toml().is_err(),
        "an unmigrated lock is never rewritten as is"
    );
}

// frob:tests crates/gob-lock/src/file.rs::LockFile
#[test]
fn scheme_one_file_under_version_two_is_all_reattest() {
    let mut lock = LockFile::default();
    lock.entries.insert("a".to_owned(), entry("1"));
    lock.flows.insert("f".to_owned(), flow());
    lock.digest_scheme = 1;
    let back = LockFile::from_toml(&lock.to_toml().unwrap()).unwrap();
    assert_eq!(back.digest_scheme, 1);
    let keys: Vec<_> = back
        .reattest()
        .into_iter()
        .map(|r| (r.key, r.kind))
        .collect();
    assert_eq!(
        keys,
        [
            ("a".to_owned(), EntryKind::Symbol),
            ("f".to_owned(), EntryKind::Flow)
        ]
    );
    assert!(LockFile::default().reattest().is_empty());
}

fn flow() -> FlowEntry {
    FlowEntry {
        producer: FlowEnd {
            identity: "web/api.ts::get".to_owned(),
            contract: "aa".to_owned(),
            shape_contract: Some("sh".to_owned()),
        },
        consumer: FlowEnd {
            identity: "src/client.rs::call".to_owned(),
            contract: "aa".to_owned(),
            shape_contract: Some("sh".to_owned()),
        },
        acked_by: "Me".to_owned(),
        acked_at: "2026-10-02T00:00:00Z".to_owned(),
        reason: Some("contracts agree".to_owned()),
    }
}

// frob:tests crates/gob-lock/src/file.rs::FlowEntry
#[test]
fn flow_and_five_facet_symbol_entries_round_trip_in_stable_text() {
    let mut lock = LockFile::default();
    lock.flows.insert("orders.get".to_owned(), flow());
    let mut e = entry("1");
    e.attr = "at".to_owned();
    e.contract = "ct".to_owned();
    e.identity = Some("stable:1".to_owned());
    lock.entries.insert("a.rs::a".to_owned(), e);
    let text = lock.to_toml().unwrap();
    assert!(
        text.starts_with("version = 2\ndigest_scheme = 2\n"),
        "{text}"
    );
    assert!(text.contains("[[symbol]]") && text.contains("[[flow]]"));
    assert!(text.contains("identity = \"stable:1\""));
    let back = LockFile::from_toml(&text).unwrap();
    assert_eq!(back, lock);
    assert_eq!(back.to_toml().unwrap(), text);
    assert!(back.reattest().is_empty());
    let mut changed = back.clone();
    changed
        .flows
        .get_mut("orders.get")
        .unwrap()
        .consumer
        .contract = "bb".to_owned();
    changed.entries.get_mut("a.rs::a").unwrap().attr = "zz".to_owned();
    let d = diff(&back, &changed);
    assert_eq!(d.flows_changed, ["orders.get"]);
    assert_eq!(d.changed, [("a.rs::a".to_owned(), vec![Facet::Attr])]);
}

#[test]
fn empty_lock_is_just_the_header() {
    let text = LockFile::default().to_toml().unwrap();
    assert_eq!(text, "version = 2\ndigest_scheme = 2\n");
}

fn facets(tag: &str) -> FacetSet {
    FacetSet {
        sig: format!("s{tag}"),
        body: format!("b{tag}"),
        doc: format!("d{tag}"),
        attr: format!("a{tag}"),
        contract: format!("c{tag}"),
    }
}

fn current(items: &[(&str, &str)]) -> Current {
    let mut c = Current::default();
    for (k, tag) in items {
        c.symbols.insert(
            (*k).to_owned(),
            CurrentSymbol {
                identity: None,
                facets: facets(tag),
                targets: Vec::new(),
            },
        );
    }
    c
}

fn opts(all: bool, reason: Option<&str>) -> PlanOptions {
    PlanOptions {
        actor: "Me".to_owned(),
        at: "2026-10-02T00:00:00Z".to_owned(),
        reason: reason.map(str::to_owned),
        all,
    }
}

// frob:tests crates/gob-lock/src/plan.rs::plan
#[test]
fn plan_records_changes_skips_unchanged_and_rejects_empty() {
    let cur = current(&[("a", "1"), ("b", "1")]);
    let p = plan(
        &LockFile::default(),
        &cur,
        &["a".to_owned()],
        &opts(false, None),
    )
    .unwrap();
    assert_eq!(p.acked, ["a"]);
    assert_eq!(p.lock.entries["a"].attr, "a1");
    let again = plan(&p.lock, &cur, &["a".to_owned()], &opts(false, None)).unwrap();
    assert!(again.acked.is_empty());
    let moved = current(&[("a", "2"), ("b", "1")]);
    let all = plan(&p.lock, &moved, &[], &opts(true, None)).unwrap();
    assert_eq!(all.acked, ["a"], "--all re-acks only tracked entries");
    assert!(matches!(
        plan(&LockFile::default(), &cur, &[], &opts(false, None)),
        Err(PlanError::NothingToAck)
    ));
}

// frob:tests crates/gob-lock/src/plan.rs::plan
#[test]
fn plan_refuses_to_migrate_without_all_and_reason_then_reattests_and_drops() {
    let mut old = LockFile::from_toml(V1).unwrap();
    old.entries.insert("gone".to_owned(), entry("9"));
    let cur = current(&[("a.rs::a", "1")]);
    for o in [opts(false, Some("r")), opts(true, None)] {
        let e = plan(&old, &cur, &["a.rs::a".to_owned()], &o).unwrap_err();
        assert!(
            matches!(e, PlanError::MigrationRequired { entries: 2, .. }),
            "{e}"
        );
    }
    let p = plan(&old, &cur, &[], &opts(true, Some("scheme 2"))).unwrap();
    assert_eq!(p.acked, ["a.rs::a"]);
    assert_eq!(p.dropped, ["gone"]);
    assert_eq!(p.reattested.len(), 1);
    assert_eq!((p.lock.version, p.lock.digest_scheme), (2, 2));
    assert!(p.lock.reattest().is_empty());
    assert!(!p.lock.entries.contains_key("gone"));
}

// frob:tests crates/gob-lock/src/plan.rs::plan
#[test]
fn plan_acks_flows_by_key() {
    let mut cur = Current::default();
    let f = flow();
    cur.flows.insert(
        "orders.get".to_owned(),
        CurrentFlow {
            producer: f.producer.clone(),
            consumer: f.consumer.clone(),
        },
    );
    let p = plan(
        &LockFile::default(),
        &cur,
        &["orders.get".to_owned()],
        &opts(false, Some("x")),
    )
    .unwrap();
    assert_eq!(p.acked, ["orders.get"]);
    assert_eq!(p.lock.flows["orders.get"].producer, f.producer);
    let again = plan(
        &p.lock,
        &cur,
        &["orders.get".to_owned()],
        &opts(false, None),
    )
    .unwrap();
    assert!(again.acked.is_empty());
}

// frob:ticket 01M3Z714820D1SK6X44T9R1B70
// frob:tests crates/gob-lock/src/file.rs::LockFile
#[test]
fn rename_rekeys_entry_and_flow_ends_and_records_the_chain() {
    let mut lock = LockFile::default();
    lock.entries.insert("a.rs::old".to_owned(), entry("1"));
    lock.flows.insert("flow/x".to_owned(), flow());
    let old = lock.flows["flow/x"].producer.identity.clone();
    lock.entries.insert(old.clone(), entry("p"));
    assert!(lock.rename(&old, "b.rs::new"));
    assert!(!lock.entries.contains_key(&old));
    assert_eq!(lock.entries["b.rs::new"].sig, "p");
    assert_eq!(lock.flows["flow/x"].producer.identity, "b.rs::new");
    assert_eq!(lock.renamed[&old], "b.rs::new");
    assert!(!lock.rename("missing", "z"));
    assert!(
        !lock.rename("a.rs::old", "b.rs::new"),
        "target already keyed"
    );
    let text = lock.to_toml().unwrap();
    assert_eq!(LockFile::from_toml(&text).unwrap(), lock);
}

// frob:ticket 01M3ZPNT7KCE66E6SAKV4E149M
// frob:tests crates/gob-lock/src/file.rs::LockFile
#[test]
fn rename_log_and_absent_shape_contract_round_trip() {
    let mut lock = LockFile::default();
    let mut f = flow();
    f.producer.shape_contract = None;
    lock.flows.insert("orders.get".to_owned(), f);
    lock.log_rename(
        "a.rs::old",
        "a.rs::new",
        "Me <m@x>",
        "2026-10-02T00:00:00Z",
        "moved",
    );
    let text = lock.to_toml().unwrap();
    assert!(
        text.contains("[[ack_log]]") && text.contains("kind = \"rename\""),
        "{text}"
    );
    assert_eq!(text.matches("shape_contract").count(), 1, "{text}");
    let back = LockFile::from_toml(&text).unwrap();
    assert_eq!(back, lock);
    assert_eq!(back.ack_log[0].target.as_deref(), Some("a.rs::new"));
}

// frob:ticket 01M4GK4M8KKRE7X7JCP6YJ5K96
#[test]
fn a_v1_frob_lock_is_named_as_such_with_the_remedy() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("frob.lock");
    for text in [
        "{\"entries\": {}}\n",
        "[pins]\nkey = \"x\"\n",
        "version = 0\n",
    ] {
        std::fs::write(&path, text).unwrap();
        let err = LockFile::load(&path).unwrap_err();
        assert!(matches!(err, LockError::LegacyV1 { .. }), "{text}: {err}");
        let msg = err.to_string();
        assert!(msg.contains(&path.display().to_string()), "{msg}");
        assert!(msg.contains("v1"), "{msg}");
        assert!(msg.contains("delete it and run `frob ack"), "{msg}");
    }
    std::fs::write(&path, "not = [toml").unwrap();
    assert!(
        matches!(LockFile::load(&path), Err(LockError::Parse { .. })),
        "plain garbage stays a parse error"
    );
}

//! Integration tests: the whole ticket lifecycle against temporary git repositories.

use std::path::Path;

use frob_ledger::guards::{NoLeases, default_close_guards};
use frob_ledger::index::{Index, ListFilter};
use frob_ledger::model::{Category, CommentSubtype, LinkKind, Outcome, Priority, TicketType};
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::{Ledger, LedgerConfig, LedgerError, RefMode, TicketId, fold, rules};
use gob_git::{CommitOptions, RelPath, Repo, TreeRef};

const MAIN: &str = "refs/heads/main";

/// A repository on `main` with a root commit, an identity, and an open ledger.
fn fixture(mode: RefMode) -> (tempfile::TempDir, Ledger) {
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
        MAIN,
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hello\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let cfg = LedgerConfig {
        mode,
        ..LedgerConfig::default()
    };
    (dir, Ledger::open(repo, cfg))
}

fn commits_since_root(repo: &Repo) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = repo.rev_parse(MAIN).expect("tip");
    while let Ok(parent) = repo.rev_parse(&format!("{cur}^")) {
        let changed = repo
            .diff_names(&TreeRef::Oid(parent), &TreeRef::Oid(cur))
            .expect("diff");
        assert!(
            changed.iter().all(|c| c.path.starts_with("tickets/")),
            "commit {cur} touches non-ticket paths: {changed:?}"
        );
        out.push(cur.to_string());
        cur = parent;
    }
    out
}

fn read(dir: &Path, rel: &str) -> String {
    std::fs::read_to_string(dir.join(rel)).expect("file")
}

#[test]
fn lifecycle_new_update_link_comment_close() {
    let (dir, ledger) = fixture(RefMode::Trunk);
    let mut req = NewTicket::new("Parse the config", TicketType::Task);
    req.points = Some("3".parse().expect("points"));
    req.acceptance = vec!["parses".into(), "reports errors".into()];
    req.labels = vec!["parser".into()];
    req.scope = vec!["crates/x/**".into()];
    req.body = "Some body.\n".into();
    let a = ledger.new_ticket(req).expect("new a");
    assert!(!a.already);
    let b = ledger
        .new_ticket(NewTicket::new("Blocker", TicketType::Bug))
        .expect("new b");
    let id_a = a.ticket.front.id;
    let id_b = b.ticket.front.id;

    // update: priority and a label change are two events in one commit.
    let patch = Patch {
        sets: vec![("priority".into(), Some(toml::Value::String("high".into())))],
        add_labels: vec!["urgent".into()],
        ..Patch::default()
    };
    let upd = ledger.update(id_a, &patch).expect("update");
    assert_eq!(upd.events.len(), 2);
    assert_eq!(upd.ticket.front.priority, Priority::High);
    assert_eq!(upd.ticket.front.labels, vec!["parser", "urgent"]);

    let linked = ledger.link(id_a, LinkKind::BlockedBy, id_b).expect("link");
    assert!(!linked.already);
    assert!(
        ledger
            .link(id_a, LinkKind::BlockedBy, id_b)
            .expect("again")
            .already
    );
    assert!(
        ledger
            .link(id_b, LinkKind::Blocks, id_a)
            .expect("inverse")
            .already,
        "the inverse spelling is the same edge"
    );

    // blocked is derived and excludes the ticket from doable.
    let doable: Vec<_> = ledger
        .doable(&NoLeases)
        .expect("doable")
        .iter()
        .map(|s| s.id)
        .collect();
    assert_eq!(doable, vec![id_b]);

    ledger
        .comment(id_a, CommentSubtype::Decision, "ship it")
        .expect("comment");
    let guards = default_close_guards();
    let guard_refs: Vec<&dyn frob_ledger::guards::CloseGuard> =
        guards.iter().map(|g| &**g).collect();
    let refused = ledger.close(id_a, None, None, &guard_refs).unwrap_err();
    assert!(
        matches!(refused, LedgerError::GuardRefused { ref code, .. } if code == "E-CLOSE-OUTCOME")
    );
    let closed = ledger
        .close(id_a, Some(Outcome::Done), None, &guard_refs)
        .expect("close");
    assert_eq!(closed.ticket.front.category, Category::Done);
    assert!(
        ledger
            .close(id_a, Some(Outcome::Done), None, &guard_refs)
            .expect("repeat")
            .already
    );
    assert!(matches!(
        ledger.close(id_a, Some(Outcome::Fixed), None, &guard_refs),
        Err(LedgerError::Terminal { .. })
    ));

    // exactly: new a, new b, update, link, comment, close.
    let repo = ledger.repo();
    let commits = commits_since_root(repo);
    assert_eq!(commits.len(), 6, "{commits:?}");

    // events per mutation, and frontmatter == fold.
    let tip = repo.rev_parse(MAIN).expect("tip").to_string();
    let events_a = ledger.read_events_at(&tip, id_a).expect("events");
    assert_eq!(events_a.len(), 1 + 2 + 1 + 1 + 1);
    assert_eq!(ledger.read_events_at(&tip, id_b).expect("events").len(), 1);
    for id in [id_a, id_b] {
        let stored = ledger
            .read_ticket_at(&tip, id)
            .expect("read")
            .expect("present");
        let events = ledger.read_events_at(&tip, id).expect("events");
        assert_eq!(fold::fold(id, &events).expect("fold").ticket, stored);
    }
    // The checked-out worktree carries the same files.
    let blob = repo
        .read_blob_at(MAIN, &format!("tickets/{id_a}/ticket.md"))
        .expect("blob")
        .expect("present");
    assert_eq!(
        read(dir.path(), &format!("tickets/{id_a}/ticket.md")).as_bytes(),
        blob
    );

    // Once a is done, b stays doable and a no longer is blocked.
    let view = ledger.show(id_a).expect("show");
    assert!(!view.summary.blocked);
    assert_eq!(view.outgoing.len(), 1);
    let view_b = ledger.show(id_b).expect("show b");
    assert_eq!(view_b.incoming[0].kind, LinkKind::Blocks);

    let report = ledger.doctor(false).expect("doctor");
    assert!(report.is_clean(), "{report:?}");
    assert_eq!((report.tickets, report.events), (2, 7));
    let brief = ledger.brief(id_a).expect("brief");
    assert!(brief.contains("Parse the config") && brief.contains("## Acceptance"));
}

#[test]
fn new_is_idempotent_on_the_key() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let mut req = NewTicket::new("Once", TicketType::Chore);
    req.idempotency_key = Some("key-1".into());
    let first = ledger.new_ticket(req.clone()).expect("first");
    let second = ledger.new_ticket(req).expect("second");
    assert!(!first.already && second.already);
    assert_eq!(first.ticket.front.id, second.ticket.front.id);
    assert_eq!(ledger.list(&ListFilter::default()).expect("list").len(), 1);
    assert_eq!(commits_since_root(ledger.repo()).len(), 1);
}

#[test]
fn update_validates_and_repeats_are_already() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let t = ledger
        .new_ticket(NewTicket::new("T", TicketType::Task))
        .expect("new");
    let id = t.ticket.front.id;
    let bad = Patch {
        sets: vec![("points".into(), Some(toml::Value::Integer(4)))],
        ..Patch::default()
    };
    assert!(matches!(
        ledger.update(id, &bad),
        Err(LedgerError::Invalid { .. })
    ));
    let flavour = Patch {
        sets: vec![(
            "flavour".into(),
            Some(toml::Value::String("user_story".into())),
        )],
        ..Patch::default()
    };
    assert!(
        ledger.update(id, &flavour).is_err(),
        "flavour needs a reason"
    );
    let noop = Patch {
        sets: vec![("title".into(), Some(toml::Value::String("T".into())))],
        ..Patch::default()
    };
    assert!(ledger.update(id, &noop).expect("noop").already);
}

#[test]
fn link_topology_is_enforced() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let mk = |t: &str| {
        ledger
            .new_ticket(NewTicket::new(t, TicketType::Task))
            .expect("new")
            .ticket
            .front
            .id
    };
    let (a, b, c) = (mk("a"), mk("b"), mk("c"));
    ledger.link(a, LinkKind::Blocks, b).expect("a blocks b");
    ledger.link(b, LinkKind::Blocks, c).expect("b blocks c");
    let cycle = ledger.link(c, LinkKind::Blocks, a).unwrap_err();
    assert!(matches!(
        cycle,
        LedgerError::LinkRejected {
            code: "E-LINK-CYCLE",
            ..
        }
    ));
    let selfie = ledger.link(a, LinkKind::Relates, a).unwrap_err();
    assert!(matches!(
        selfie,
        LedgerError::LinkRejected {
            code: "E-LINK-SELF",
            ..
        }
    ));
    // unlink through the inverse spelling removes the stored edge.
    let un = ledger.unlink(b, LinkKind::BlockedBy, a).expect("unlink");
    assert!(!un.already);
    assert!(
        ledger
            .unlink(b, LinkKind::BlockedBy, a)
            .expect("again")
            .already
    );
    assert!(
        ledger.link(c, LinkKind::Blocks, a).is_ok(),
        "no cycle once a-b is gone"
    );
}

#[test]
fn doctor_flags_and_fixes_a_stale_frontmatter() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let id = ledger
        .new_ticket(NewTicket::new("Original", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    // Hand-edit the cache on the ledger ref (as a merge button might).
    let tip = ledger.repo().rev_parse(MAIN).expect("tip").to_string();
    let mut stored = ledger
        .read_ticket_at(&tip, id)
        .expect("read")
        .expect("present");
    stored.front.title = "Tampered".into();
    ledger
        .repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new(format!("tickets/{id}/ticket.md")).expect("path"),
                Some(
                    frob_ledger::doc::render(&stored)
                        .expect("render")
                        .into_bytes(),
                ),
            )],
            "tamper",
            &CommitOptions::default(),
        )
        .expect("tamper");
    let report = ledger.doctor(false).expect("doctor");
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].rule.as_str(), "TICK001");
    let fixed = ledger.doctor(true).expect("fix");
    assert_eq!(fixed.fixed, vec![id]);
    assert!(ledger.doctor(false).expect("again").is_clean());
    assert_eq!(
        ledger.show(id).expect("show").ticket.front.title,
        "Original"
    );
}

#[test]
fn tick002_and_tick003() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let id = ledger
        .new_ticket(NewTicket::new("Real", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    let ghost = TicketId::mint();
    let real = id.to_string();
    let ghost_s = ghost.to_string();
    let findings = rules::tick002(&[&real, &ghost_s, "~abbrev"], "main", &ledger).expect("tick002");
    assert_eq!(findings.len(), 2);
    assert!(findings.iter().all(|f| f.rule.as_str() == "TICK002"));
    let view = ledger.show(id).expect("show");
    let mut front = view.ticket.front;
    front.links.push(frob_ledger::model::Link {
        kind: LinkKind::Relates,
        target: ghost,
    });
    let dangling = rules::tick003(&front, &|t| t == id);
    assert_eq!(dangling.len(), 1);
    assert_eq!(dangling[0].rule.as_str(), "TICK003");
}

#[test]
fn alias_ambiguity_lists_both_candidates() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    for title in ["first", "second"] {
        let mut req = NewTicket::new(title, TicketType::Task);
        req.aliases = vec!["T-0042".into()];
        ledger.new_ticket(req).expect("new");
    }
    match ledger.resolve("T-0042") {
        Err(LedgerError::Ambiguous { candidates, .. }) => {
            assert_eq!(candidates.len(), 2);
            let r = LedgerError::Ambiguous {
                input: "T-0042".into(),
                candidates,
            }
            .to_refusal()
            .expect("refusal");
            assert_eq!(r.code, "E-TICKET-AMBIGUOUS");
            assert_eq!(r.exit_code(), gob_diagnostics::ExitCode::Refused);
            assert!(!r.class.retryable());
        }
        other => panic!("expected ambiguity, got {other:?}"),
    }
    assert!(matches!(
        ledger.resolve("nope"),
        Err(LedgerError::NotFound { .. })
    ));
}

#[test]
fn handles_resolve_and_ambiguous_suffixes_refuse() {
    let dir = tempfile::tempdir().expect("tempdir");
    let mut index = Index::open(&dir.path().join("i.sqlite")).expect("open");
    let mk = |id: &str, title: &str| {
        let mut t = synthetic(title);
        t.front.id = id.parse().expect("ulid");
        t
    };
    let tickets = vec![
        mk("01J9ZK3M4N0000000AAAAAAAAB", "one"),
        mk("01J9ZK3M4N0000000BBBBBBBAB", "two"),
        mk("01J9ZK3M4N0000000CCCCCCCCC", "three"),
    ];
    index.rebuild("k", &tickets, 7).expect("rebuild");
    match index.resolve("~AB") {
        Err(LedgerError::Ambiguous { candidates, .. }) => {
            assert_eq!(candidates.len(), 2);
            assert_eq!(candidates[0].title, "one");
        }
        other => panic!("{other:?}"),
    }
    assert!(
        index.resolve("~ab").is_err(),
        "case-insensitive but still ambiguous"
    );
    let one = index.resolve("~AAAAAAAAB").expect("unique suffix");
    assert_eq!(one.to_string(), "01J9ZK3M4N0000000AAAAAAAAB");
    let s = index.summary(one).expect("sql").expect("row");
    assert_eq!(s.handle, "~AAAAAAB", "min 7 chars: {}", s.handle);
    let full = index
        .resolve("01j9zk3m4n0000000ccccccccc")
        .expect("full ulid, any case");
    assert_eq!(
        index.summary(full).expect("sql").expect("row").title,
        "three"
    );
}

fn synthetic(title: &str) -> frob_ledger::model::Ticket {
    use frob_ledger::model::{Frontmatter, Stamp, Ticket};
    Ticket {
        front: Frontmatter {
            id: TicketId::mint(),
            title: title.into(),
            ty: TicketType::Task,
            flavour: None,
            category: Category::Todo,
            outcome: None,
            priority: Priority::Medium,
            points: None,
            parent: None,
            reporter: "t".into(),
            assignee: None,
            created: Stamp::from_unix(1_790_000_000),
            updated: Stamp::from_unix(1_790_000_000),
            persona: None,
            capability: None,
            outcome_text: None,
            idempotency_key: None,
            aliases: vec![],
            labels: vec![],
            scope: vec![],
            links: vec![],
            acceptance: vec![],
        },
        body: String::new(),
    }
}

#[test]
fn index_rebuilds_when_the_ledger_tree_changes_and_updates_in_place_otherwise() {
    let (dir, ledger) = fixture(RefMode::Trunk);
    let id = ledger
        .new_ticket(NewTicket::new("Indexed", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    let db = dir.path().join(".frob/tickets.sqlite");
    assert!(db.exists());
    let key_after_write = Index::open(&db).expect("open").key().expect("key");
    // Our own write kept the index current without a rebuild.
    assert!(key_after_write.is_some());
    assert_eq!(ledger.list(&ListFilter::default()).expect("list").len(), 1);
    assert_eq!(
        Index::open(&db).expect("open").key().expect("key"),
        key_after_write
    );

    // Another writer moves the ledger ref behind our back: the key differs, the index rebuilds.
    let other = Repo::discover(dir.path()).expect("discover");
    let other_ledger = Ledger::open(other, LedgerConfig::default());
    let second = other_ledger
        .new_ticket(NewTicket::new("Second", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    // Drop the index so the first handle is stale relative to a wiped cache.
    let mut idx = Index::open(&db).expect("open");
    idx.rebuild("stale-key", &[], 7).expect("wipe");
    drop(idx);
    let listed = ledger.list(&ListFilter::default()).expect("list");
    let ids: Vec<_> = listed.iter().map(|s| s.id).collect();
    assert_eq!(ids, vec![id, second]);
    assert_ne!(
        Index::open(&db)
            .expect("open")
            .key()
            .expect("key")
            .as_deref(),
        Some("stale-key")
    );
}

#[test]
fn branch_mode_commits_to_the_current_branch() {
    let (dir, ledger) = fixture(RefMode::Branch);
    let repo = ledger.repo();
    // A topic branch checked out; trunk must not move.
    let main_tip = repo.rev_parse(MAIN).expect("main");
    std::fs::write(
        repo.git_dir().join("refs/heads/topic"),
        format!("{main_tip}\n"),
    )
    .expect("topic");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/topic\n").expect("head");
    let repo2 = Repo::discover(dir.path()).expect("discover");
    let ledger = Ledger::open(repo2, ledger.config().clone());
    ledger
        .new_ticket(NewTicket::new("On topic", TicketType::Task))
        .expect("new");
    assert_eq!(ledger.repo().rev_parse(MAIN).expect("main"), main_tip);
    assert_ne!(
        ledger.repo().rev_parse("refs/heads/topic").expect("topic"),
        main_tip
    );
}

#[test]
fn trunk_mode_commits_to_trunk_even_on_another_branch() {
    let (dir, ledger) = fixture(RefMode::Trunk);
    let repo = ledger.repo();
    let main_tip = repo.rev_parse(MAIN).expect("main");
    std::fs::write(
        repo.git_dir().join("refs/heads/topic"),
        format!("{main_tip}\n"),
    )
    .expect("topic");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/topic\n").expect("head");
    let repo2 = Repo::discover(dir.path()).expect("discover");
    let ledger = Ledger::open(repo2, ledger.config().clone());
    let t = ledger
        .new_ticket(NewTicket::new("On trunk", TicketType::Task))
        .expect("new");
    assert_ne!(ledger.repo().rev_parse(MAIN).expect("main"), main_tip);
    assert!(
        !dir.path()
            .join(format!("tickets/{}", t.ticket.front.id))
            .exists(),
        "topic worktree untouched"
    );
}

#[test]
fn merge_driver_unions_events_and_refolds() {
    use frob_ledger::event::{CommentData, Event, EventBody, FieldChange};
    use frob_ledger::merge;
    let dir = tempfile::tempdir().expect("tempdir");
    let id = TicketId::mint();
    let create = Event::new(
        "a",
        EventBody::Create(Box::new(frob_ledger::event::CreateData {
            title: "T".into(),
            ty: TicketType::Task,
            category: Category::Todo,
            priority: Priority::Medium,
            flavour: None,
            points: None,
            parent: None,
            assignee: None,
            persona: None,
            capability: None,
            outcome_text: None,
            idempotency_key: None,
            aliases: vec![],
            labels: vec![],
            scope: vec![],
            acceptance: vec![],
            body: String::new(),
            links: vec![],
        })),
    );
    let ours = Event::new(
        "a",
        EventBody::Field(FieldChange {
            field: "priority".into(),
            old: Some(toml::Value::String("medium".into())),
            new: Some(toml::Value::String("high".into())),
            reason: None,
            moved: None,
        }),
    );
    let theirs = Event::new(
        "b",
        EventBody::Comment(CommentData {
            subtype: CommentSubtype::Note,
            body: "hi".into(),
        }),
    );
    let tdir = dir.path().join(format!("tickets/{id}/events"));
    std::fs::create_dir_all(&tdir).expect("mkdir");
    for e in [&create, &ours, &theirs] {
        std::fs::write(tdir.join(e.file_name()), e.to_toml().expect("toml")).expect("write");
    }
    let out = dir.path().join("ours.md");
    std::fs::write(&out, "<<<<<<< conflict markers\n").expect("seed");
    let path = format!("tickets/{id}/ticket.md");
    let report = merge::resolve(dir.path(), &path, &out, vec![]).expect("resolve");
    assert_eq!(report.events, 3);
    let text = std::fs::read_to_string(&out).expect("read");
    let t = frob_ledger::doc::parse("m", &text).expect("parse");
    assert_eq!(t.front.priority, Priority::High);
    assert_eq!(t.front.updated, theirs.at.max(ours.at));
    // No create event: the fold fails, which the verb turns into exit 1.
    std::fs::remove_file(tdir.join(create.file_name())).expect("rm");
    assert!(merge::resolve(dir.path(), &path, &out, vec![]).is_err());
}

#[test]
fn concurrent_writers_on_one_ticket_lose_no_events_and_leave_the_frontmatter_consistent() {
    let (dir, ledger) = fixture(RefMode::Trunk);
    let id = ledger
        .new_ticket(NewTicket::new("Contended", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    // Check out another branch so the ledger ref is written without worktree sync.
    let repo = ledger.repo();
    let main_tip = repo.rev_parse(MAIN).expect("main");
    std::fs::write(
        repo.git_dir().join("refs/heads/topic"),
        format!("{main_tip}\n"),
    )
    .expect("topic");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/topic\n").expect("head");
    let cfg = LedgerConfig {
        cas_retries: 50,
        ..LedgerConfig::default()
    };
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let handles: Vec<_> = ["left", "right"]
        .into_iter()
        .map(|who| {
            let (path, cfg, barrier) = (dir.path().to_path_buf(), cfg.clone(), barrier.clone());
            std::thread::spawn(move || {
                let ledger = Ledger::open(Repo::discover(&path).expect("discover"), cfg);
                barrier.wait();
                for n in 0..5 {
                    ledger
                        .comment(id, CommentSubtype::Note, &format!("{who} {n}"))
                        .expect("comment");
                }
            })
        })
        .collect();
    for h in handles {
        h.join().expect("thread");
    }
    let ledger = Ledger::open(Repo::discover(dir.path()).expect("discover"), cfg);
    let report = ledger.doctor(false).expect("doctor");
    assert_eq!(report.events, 11, "create plus ten comments");
    assert!(report.findings.is_empty(), "{report:?}");
    assert_eq!(ledger.events(id).expect("events").len(), 11);
}

fn evidence(accepts: &[usize]) -> frob_ledger::event::EventBody {
    record(accepts, "cargo test", "measured", Some(true))
}

fn record(
    accepts: &[usize],
    reference: &str,
    status: &str,
    passed: Option<bool>,
) -> frob_ledger::event::EventBody {
    use frob_ledger::event::{EventBody, EvidenceData};
    let passed = passed.map_or(String::new(), |p| format!("passed = {p}\n"));
    EventBody::Evidence(EvidenceData {
        accepts: accepts.to_vec(),
        record: format!(
            "provider = \"command\"\nref = \"{reference}\"\nstatus = \"{status}\"\n{passed}size = 0\n"
        )
        .parse()
        .expect("table"),
    })
}

fn bound(ledger: &Ledger, id: TicketId) -> Vec<bool> {
    ledger
        .show(id)
        .expect("show")
        .ticket
        .front
        .acceptance
        .iter()
        .map(|a| a.bound)
        .collect()
}

// frob:ticket 01M3WYJ81430D3D5QSNCFM8QB0
#[test]
fn evidence_binds_acceptance_through_the_remap() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let mut req = NewTicket::new("Bind", TicketType::Task);
    req.acceptance = vec!["one".into(), "two".into(), "three".into()];
    let id = ledger.new_ticket(req).expect("new").ticket.front.id;
    assert_eq!(bound(&ledger, id), [false, false, false]);

    // Offered for criteria 1 and 3, then criterion 1 is removed: "three" is now second.
    let applied = ledger.append(id, evidence(&[1, 3])).expect("append");
    assert_eq!(applied.events.len(), 1);
    assert_eq!(bound(&ledger, id), [true, false, true]);
    ledger
        .update(
            id,
            &Patch {
                remove_acceptance: vec![1],
                ..Patch::default()
            },
        )
        .expect("remove");
    let view = ledger.show(id).expect("show").ticket;
    let state: Vec<_> = view
        .front
        .acceptance
        .iter()
        .map(|a| (a.text.as_str(), a.bound))
        .collect();
    assert_eq!(state, [("two", false), ("three", true)]);

    // New evidence written after the removal numbers the list as it now stands.
    ledger.append(id, evidence(&[1])).expect("append");
    assert_eq!(bound(&ledger, id), [true, true]);

    // The stored ticket equals the fold, and the ledger is clean.
    let report = ledger.doctor(false).expect("doctor");
    assert!(report.is_clean(), "{report:?}");
}

// frob:ticket 01M3WYJ81430D3D5QSNCFM8QB0
#[test]
fn append_writes_land_and_bypass_and_refuses_create() {
    use frob_ledger::event::{EventBody, EvidenceBypassData, LandData};
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let id = ledger
        .new_ticket(NewTicket::new("L", TicketType::Task))
        .expect("new")
        .ticket
        .front
        .id;
    ledger
        .append(
            id,
            EventBody::Land(LandData {
                base_ref: MAIN.into(),
                commit: "abc123".into(),
                branch: "ticket/L".into(),
                pushed: false,
            }),
        )
        .expect("land");
    ledger
        .append(
            id,
            EventBody::EvidenceBypass(EvidenceBypassData {
                reason: "by hand".into(),
            }),
        )
        .expect("bypass");
    let kinds: Vec<_> = ledger
        .events(id)
        .expect("events")
        .into_iter()
        .map(|e| e.kind)
        .collect();
    assert_eq!(kinds, ["create", "land", "evidence-bypass"]);
    assert!(matches!(
        ledger.append(id, EventBody::Other),
        Err(LedgerError::Invalid { .. })
    ));
    assert!(matches!(
        ledger.append(TicketId::mint(), evidence(&[])),
        Err(LedgerError::NotFound { .. })
    ));
    assert!(ledger.doctor(false).expect("doctor").is_clean());
}

// frob:ticket 01M3WYJ81430D3D5QSNCFM8QB0
#[test]
fn events_written_by_the_old_helpers_fold_and_round_trip() {
    use frob_ledger::event::{Event, EventBody};
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/landed");
    let mut events = Vec::new();
    for entry in std::fs::read_dir(&dir).expect("fixtures") {
        let path = entry.expect("entry").path();
        if path.extension().is_none_or(|e| e != "toml") {
            continue;
        }
        let text = std::fs::read_to_string(&path).expect("read");
        let stem = path.file_stem().expect("stem").to_string_lossy();
        let event = Event::parse(stem.parse().expect("event id"), &text).expect("parse");
        // The same keys and values come back out, so an older reader sees an unchanged file.
        let again: toml::Table = event.to_toml().expect("render").parse().expect("table");
        let original: toml::Table = text.parse().expect("table");
        assert_eq!(again, original, "{}", path.display());
        events.push(event);
    }
    assert!(
        events
            .iter()
            .any(|e| matches!(e.body, EventBody::Evidence(_)))
    );
    assert!(events.iter().any(|e| matches!(e.body, EventBody::Land(_))));
    let expected = std::fs::read_to_string(dir.join("expected.md.txt")).expect("expected");
    let mut stored = frob_ledger::doc::parse("expected", &expected).expect("doc");
    let id = stored.front.id;
    let folded = fold::fold(id, &events).expect("fold").ticket;
    // The stored file predates binding: it differs only in `bound`, which evidence for 1 now sets.
    assert!(!stored.front.acceptance[0].bound);
    stored.front.acceptance[0].bound = true;
    assert_eq!(folded, stored);
}

// frob:ticket 01M3WYJ81430D3D5QSNCFM8QB0
#[test]
fn only_measured_passing_evidence_binds_and_the_latest_per_reference_decides() {
    let (_dir, ledger) = fixture(RefMode::Trunk);
    let mut req = NewTicket::new("Verdicts", TicketType::Task);
    req.acceptance = vec!["one".into()];
    let id = ledger.new_ticket(req).expect("new").ticket.front.id;

    ledger
        .append(id, record(&[1], "a", "measured", Some(false)))
        .expect("failing");
    assert_eq!(bound(&ledger, id), [false], "failing does not bind");
    ledger
        .append(id, record(&[1], "b", "unmeasured", None))
        .expect("unmeasured");
    assert_eq!(bound(&ledger, id), [false], "unmeasured does not bind");
    ledger
        .append(id, record(&[1], "a", "measured", Some(true)))
        .expect("pass after fail");
    assert_eq!(bound(&ledger, id), [true], "passing after failing binds");
    ledger
        .append(id, record(&[1], "b", "measured", Some(true)))
        .expect("other reference passes");
    ledger
        .append(id, record(&[1], "a", "measured", Some(false)))
        .expect("fail after pass");
    assert_eq!(bound(&ledger, id), [true], "another reference still passes");
    ledger
        .append(id, record(&[1], "b", "measured", Some(false)))
        .expect("last fails too");
    assert_eq!(
        bound(&ledger, id),
        [false],
        "failing after passing unbinds when every reference's latest failed"
    );
    assert!(ledger.doctor(false).expect("doctor").is_clean());
}

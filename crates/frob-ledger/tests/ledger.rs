//! Integration tests: the whole ticket lifecycle against temporary git repositories.

use std::path::Path;

use frob_ledger::guards::{NoLeases, default_close_guards};
use frob_ledger::index::{Index, ListFilter};
use frob_ledger::model::{Category, CommentSubtype, LinkKind, Outcome, Priority, TicketType};
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::{Layout, Ledger, LedgerConfig, LedgerError, RefMode, TicketId, fold, rules};
use gob_git::{CommitOptions, RelPath, Repo, TreeRef};

const MAIN: &str = "refs/heads/main";

/// A repository on `main` with a root commit, an identity, and an open ledger.
fn fixture(layout: Layout, mode: RefMode) -> (tempfile::TempDir, Ledger) {
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
    (
        dir,
        Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock)).with_layout(layout),
    )
}

/// Run one `fn name(layout: Layout)` body as two tests, once per ledger layout.
macro_rules! both_layouts {
    ($name:ident) => {
        mod $name {
            #[test]
            fn dir() {
                super::$name(super::Layout::Dir);
            }

            #[test]
            fn branch() {
                super::$name(super::Layout::Branch);
            }
        }
    };
}

/// Repository path of the document of ticket `id` at the tip of `MAIN`, in either layout.
fn card_path(ledger: &Ledger, id: TicketId) -> String {
    if ledger.layout() == Layout::Dir {
        return format!("tickets/{id}/ticket.md");
    }
    let repo = ledger.repo();
    let empty = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        .parse()
        .expect("oid");
    repo.diff_names(&TreeRef::Oid(empty), &TreeRef::Ref(MAIN.to_owned()))
        .expect("diff")
        .into_iter()
        .map(|c| c.path)
        .find(|p| {
            Path::new(p)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("md"))
                && repo
                    .read_blob_at(MAIN, p)
                    .ok()
                    .flatten()
                    .is_some_and(|b| String::from_utf8_lossy(&b).contains(&id.to_string()))
        })
        .expect("card on the ledger tip")
}

fn commits_since_root(repo: &Repo, layout: Layout) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = repo.rev_parse(MAIN).expect("tip");
    while let Ok(parent) = repo.rev_parse(&format!("{cur}^")) {
        let changed = repo
            .diff_names(&TreeRef::Oid(parent), &TreeRef::Oid(cur))
            .expect("diff");
        assert!(
            changed.iter().all(|c| match layout {
                Layout::Dir => c.path.starts_with("tickets/"),
                Layout::Branch => c.path != "README.md",
            }),
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

fn lifecycle_new_update_link_comment_close(layout: Layout) {
    let (dir, ledger) = fixture(layout, RefMode::Trunk);
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
    let commits = commits_since_root(repo, layout);
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
    let card = card_path(&ledger, id_a);
    let blob = repo
        .read_blob_at(MAIN, &card)
        .expect("blob")
        .expect("present");
    assert_eq!(read(dir.path(), &card).as_bytes(), blob);

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
both_layouts!(lifecycle_new_update_link_comment_close);

fn new_is_idempotent_on_the_key(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
    let mut req = NewTicket::new("Once", TicketType::Chore);
    req.idempotency_key = Some("key-1".into());
    let first = ledger.new_ticket(req.clone()).expect("first");
    let second = ledger.new_ticket(req).expect("second");
    assert!(!first.already && second.already);
    assert_eq!(first.ticket.front.id, second.ticket.front.id);
    assert_eq!(ledger.list(&ListFilter::default()).expect("list").len(), 1);
    assert_eq!(commits_since_root(ledger.repo(), layout).len(), 1);
}
both_layouts!(new_is_idempotent_on_the_key);

fn update_validates_and_repeats_are_already(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(update_validates_and_repeats_are_already);

fn link_topology_is_enforced(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(link_topology_is_enforced);

fn doctor_flags_and_fixes_a_stale_frontmatter(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
                RelPath::new(card_path(&ledger, id)).expect("path"),
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
both_layouts!(doctor_flags_and_fixes_a_stale_frontmatter);

fn tick002_and_tick003(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(tick002_and_tick003);

fn alias_ambiguity_lists_both_candidates(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(alias_ambiguity_lists_both_candidates);

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
            class: frob_ledger::model::Class::Standard,
            due: None,
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

fn index_rebuilds_when_the_ledger_tree_changes_and_updates_in_place_otherwise(layout: Layout) {
    let (dir, ledger) = fixture(layout, RefMode::Trunk);
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
    let other_ledger = Ledger::open(
        other,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .with_layout(layout);
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
both_layouts!(index_rebuilds_when_the_ledger_tree_changes_and_updates_in_place_otherwise);

#[test]
fn branch_mode_commits_to_the_current_branch() {
    let (dir, ledger) = fixture(Layout::Dir, RefMode::Branch);
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
    let ledger = Ledger::open(
        repo2,
        ledger.config().clone(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
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
    let (dir, ledger) = fixture(Layout::Dir, RefMode::Trunk);
    let repo = ledger.repo();
    let main_tip = repo.rev_parse(MAIN).expect("main");
    std::fs::write(
        repo.git_dir().join("refs/heads/topic"),
        format!("{main_tip}\n"),
    )
    .expect("topic");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/topic\n").expect("head");
    let repo2 = Repo::discover(dir.path()).expect("discover");
    let ledger = Ledger::open(
        repo2,
        ledger.config().clone(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
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
        gob_time::Clock::now(&gob_time::SystemClock),
        "a",
        EventBody::Create(Box::new(frob_ledger::event::CreateData {
            title: "T".into(),
            ty: TicketType::Task,
            category: Category::Todo,
            priority: Priority::Medium,
            class: frob_ledger::model::Class::Standard,
            due: None,
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
        gob_time::Clock::now(&gob_time::SystemClock),
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
        gob_time::Clock::now(&gob_time::SystemClock),
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

fn concurrent_writers_on_one_ticket_lose_no_events_and_leave_the_frontmatter_consistent(
    layout: Layout,
) {
    let (dir, ledger) = fixture(layout, RefMode::Trunk);
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
                let ledger = Ledger::open(
                    Repo::discover(&path).expect("discover"),
                    cfg,
                    std::sync::Arc::new(gob_time::SystemClock),
                )
                .with_layout(layout);
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
    let ledger = Ledger::open(
        Repo::discover(dir.path()).expect("discover"),
        cfg,
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .with_layout(layout);
    let report = ledger.doctor(false).expect("doctor");
    assert_eq!(report.events, 11, "create plus ten comments");
    assert!(report.findings.is_empty(), "{report:?}");
    assert_eq!(ledger.events(id).expect("events").len(), 11);
}
both_layouts!(concurrent_writers_on_one_ticket_lose_no_events_and_leave_the_frontmatter_consistent);

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
fn evidence_binds_acceptance_through_the_remap(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(evidence_binds_acceptance_through_the_remap);

// frob:ticket 01M3WYJ81430D3D5QSNCFM8QB0
fn append_writes_land_and_bypass_and_refuses_create(layout: Layout) {
    use frob_ledger::event::{EventBody, EvidenceBypassData, LandData};
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(append_writes_land_and_bypass_and_refuses_create);

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
fn only_measured_passing_evidence_binds_and_the_latest_per_reference_decides(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
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
both_layouts!(only_measured_passing_evidence_binds_and_the_latest_per_reference_decides);

// frob:tests crates/frob-ledger/src/ledger.rs::LedgerConfig.is_ledger_path
#[test]
fn is_ledger_path_matches_only_paths_under_the_ledger_directory() {
    let cfg = LedgerConfig::default();
    assert!(cfg.is_ledger_path("tickets/ABC/ticket.toml"));
    assert!(!cfg.is_ledger_path("tickets"));
    assert!(!cfg.is_ledger_path("tickets-extra/x"));
    assert!(!cfg.is_ledger_path("src/tickets/x"));
    let slash = LedgerConfig {
        dir: "led/".to_owned(),
        ..LedgerConfig::default()
    };
    assert!(slash.is_ledger_path("led/x"));
    assert!(!slash.is_ledger_path("ledx/x"));
}

fn fence_text_survives_an_index_rebuild_and_doctor_repairs_a_corrupt_card(layout: Layout) {
    let (dir, ledger) = fixture(layout, RefMode::Trunk);
    let mut nt = NewTicket::new("t\n+++\nu", TicketType::Task);
    nt.persona = Some("+++".into());
    nt.outcome_text = Some("o\n+++\np".into());
    nt.acceptance = vec!["a\n+++\nb".into()];
    let id = ledger.new_ticket(nt).expect("new").ticket.front.id;
    // Drop the derived index: the next read rebuilds it from ticket.md.
    std::fs::remove_dir_all(dir.path().join(".frob")).ok();
    let shown = ledger.show(id).expect("show").ticket;
    assert_eq!(shown.front.title, "t\n+++\nu");
    assert_eq!(shown.front.persona.as_deref(), Some("+++"));
    assert_eq!(shown.front.acceptance[0].text, "a\n+++\nb");
    // Corrupt the card as an older binary would have: the fence closes early.
    // A ticket-branch card keeps its `id` line, which is how the file is still found.
    let card = card_path(&ledger, id);
    let corrupt = if layout == Layout::Dir {
        "+++\ntitle = \"\"\"\na\n+++\nb\"\"\"\n+++\n".to_owned()
    } else {
        format!("+++\nid = \"{id}\"\ntitle = \"\"\"\na\n+++\nb\"\"\"\n+++\n")
    };
    ledger
        .repo()
        .commit_paths(
            MAIN,
            &[(
                RelPath::new(card).expect("path"),
                Some(corrupt.into_bytes()),
            )],
            "corrupt",
            &CommitOptions::default(),
        )
        .expect("corrupt");
    let report = ledger.doctor(false).expect("doctor");
    assert_eq!(report.findings.len(), 1, "{report:?}");
    assert_eq!(report.findings[0].rule.as_str(), "TICK001");
    assert!(report.issues.is_empty());
    assert_eq!(ledger.doctor(true).expect("fix").fixed, vec![id]);
    assert!(ledger.doctor(false).expect("again").is_clean());
    assert_eq!(ledger.show(id).expect("show").ticket, shown);
}
both_layouts!(fence_text_survives_an_index_rebuild_and_doctor_repairs_a_corrupt_card);

// frob:ticket 01M42MGNZZ1BY6YCG49BDHEZAT
#[test]
fn local_edits_refusal_carries_a_remedy_naming_the_path() {
    let e = LedgerError::Git(gob_git::GitError::LocalEdits {
        path: "tickets/a/ticket.md".to_owned(),
    });
    let r = e.to_refusal().expect("refusal");
    let remedy = r.remedy.expect("remedy");
    assert!(remedy.contains("tickets/a/ticket.md"), "{remedy}");
}

// frob:tests crates/frob-ledger/src/event.rs::Event.parse
#[test]
fn event_files_from_before_the_clock_migration_round_trip_byte_identically() {
    // Captured from tickets/ of experimental before gob-time: whole-second `at`, same key order.
    let fixtures = [
        (
            "01M44BYMAV2NSB9E8NXQTEW6QE",
            include_str!("fixtures/event_comment.toml"),
        ),
        (
            "01KZ7KGKHX12E2EVS5JEXM2DYN",
            include_str!("fixtures/event_create.toml"),
        ),
    ];
    for (id, text) in fixtures {
        let event =
            frob_ledger::event::Event::parse(id.parse().expect("event id"), text).expect("parse");
        assert_eq!(event.to_toml().expect("render"), text, "{id}");
    }
}

// frob:tests crates/frob-ledger/src/event.rs::Event.new
#[test]
fn a_new_event_is_stamped_in_whole_seconds_even_from_a_precise_clock() {
    let at: gob_time::Stamp = "2026-10-05T01:02:03.987654321Z".parse().expect("stamp");
    let event = frob_ledger::event::Event::new(at, "a", frob_ledger::event::EventBody::Other);
    assert_eq!(event.at.precise(), "2026-10-05T01:02:03Z");
}

/// Create a todo ticket with a priority and class, returning its id.
fn todo_with(
    ledger: &Ledger,
    title: &str,
    priority: Priority,
    class: frob_ledger::model::Class,
) -> TicketId {
    let mut req = NewTicket::new(title, TicketType::Task);
    req.category = Category::Todo;
    req.priority = priority;
    req.class = class;
    ledger.new_ticket(req).expect("create").ticket.front.id
}

#[test]
fn doable_orders_by_class_then_priority_then_age() {
    // frob:ticket 01M4A12XB7EDWJ1FX8BN9XHZS1
    use frob_ledger::model::Class;
    let (_dir, ledger) = fixture(Layout::Dir, RefMode::Trunk);
    let low_old = todo_with(&ledger, "low old", Priority::Low, Class::Standard);
    let med = todo_with(&ledger, "medium", Priority::Medium, Class::Standard);
    let high_new = todo_with(&ledger, "high new", Priority::High, Class::Standard);
    let crit = todo_with(&ledger, "critical", Priority::Critical, Class::Standard);
    let late = todo_with(&ledger, "fixed late", Priority::Low, Class::FixedDate);
    let early = todo_with(&ledger, "fixed early", Priority::Low, Class::FixedDate);
    let exp = todo_with(&ledger, "expedite", Priority::Low, Class::Expedite);
    for (id, due) in [
        (late, "2026-12-01T00:00:00Z"),
        (early, "2026-11-01T00:00:00Z"),
    ] {
        let patch = Patch {
            sets: vec![("due".into(), Some(toml::Value::String(due.into())))],
            ..Patch::default()
        };
        ledger.update(id, &patch).expect("due");
    }
    let order: Vec<_> = ledger
        .doable(&NoLeases)
        .expect("doable")
        .iter()
        .map(|s| s.id)
        .collect();
    assert_eq!(order, vec![exp, early, late, crit, high_new, med, low_old]);
}

#[test]
fn doable_is_sorted_by_the_shared_comparator() {
    // frob:ticket 01M4A12XB7EDWJ1FX8BN9XHZS1
    use frob_ledger::model::Class;
    let (_dir, ledger) = fixture(Layout::Dir, RefMode::Trunk);
    for (t, p) in [
        ("a", Priority::Low),
        ("b", Priority::High),
        ("c", Priority::Medium),
    ] {
        todo_with(&ledger, t, p, Class::Standard);
    }
    let got = ledger.doable(&NoLeases).expect("doable");
    let mut again = got.clone();
    again.reverse();
    again.sort_by(frob_ledger::ops::doable_cmp);
    assert_eq!(got, again, "doable output is exactly doable_cmp order");
}

// frob:ticket 01M4BH8WMBDTAT4R0ST9VT321D
fn events_many_equals_events_per_ticket(layout: Layout) {
    let (_dir, ledger) = fixture(layout, RefMode::Trunk);
    let mut ids = std::collections::BTreeSet::new();
    for (n, to) in [Category::Todo, Category::InProgress, Category::Todo]
        .into_iter()
        .enumerate()
    {
        let id = ledger
            .new_ticket(NewTicket::new(format!("T{n}"), TicketType::Task))
            .expect("new")
            .ticket
            .front
            .id;
        for i in 0..=n {
            ledger
                .comment(id, CommentSubtype::Note, &format!("note {i}"))
                .expect("comment");
        }
        if to == Category::InProgress {
            ledger.transition(id, to, None, None).expect("start");
        }
        ids.insert(id);
    }
    let many = ledger.events_many(&ids).expect("events_many");
    assert_eq!(many.len(), 3);
    for id in &ids {
        assert_eq!(many[id], ledger.events(*id).expect("events"), "ticket {id}");
        assert!(many[id].len() >= 2);
    }
    let missing: TicketId = "01M4BH8WMBDTAT4R0ST9VT3ZZZ".parse().expect("ulid");
    let bad = std::collections::BTreeSet::from([missing]);
    assert!(matches!(
        ledger.events_many(&bad),
        Err(LedgerError::NotFound { .. })
    ));
}
both_layouts!(events_many_equals_events_per_ticket);

// frob:ticket 01M4DPJG0W39SCKZE5N807V4XM
fn doctor_resolves_the_ledger_revision_a_fixed_number_of_times(layout: Layout) {
    let reads_for = |tickets: usize| {
        let (_dir, ledger) = fixture(layout, RefMode::Trunk);
        for n in 0..tickets {
            ledger
                .new_ticket(NewTicket::new(format!("T{n}"), TicketType::Task))
                .expect("new");
        }
        let before = ledger.git_reads();
        let report = ledger.doctor(false).expect("doctor");
        assert!(report.is_clean(), "{:?}", report.issues);
        assert_eq!(report.tickets, tickets);
        ledger.git_reads() - before
    };
    let (few, many) = (reads_for(2), reads_for(12));
    assert_eq!(few, many, "doctor must not read git once per ticket");
}
both_layouts!(doctor_resolves_the_ledger_revision_a_fixed_number_of_times);

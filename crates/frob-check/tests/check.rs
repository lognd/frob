//! End-to-end behaviour of the pipeline over temp repositories.

use std::path::Path;
use std::sync::Arc;
use std::sync::atomic::{AtomicU32, Ordering};

use frob_check::{CheckCtx, CheckOptions, FailOn, FileCheck, Frob, SharedCtx, run};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use gob_diagnostics::{ExitCode, RequiredReason};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_rules::{Finding, Fix, FixKind, Rule, RuleMeta, TextEdit};
use gob_text::{FileId, TextRange, TextSize};

/// The upper-case work marker, assembled so this file does not carry one.
fn marker() -> String {
    ["TO", "DO"].concat()
}

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn quiet() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

/// A repository tree with one bare marker and one undocumented public item.
fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/lib.rs",
        &format!(
            "// {}: handle the empty case\npub fn undocumented() {{}}\n",
            marker()
        ),
    );
    write(
        dir.path(),
        "README.md",
        "# Fixture\n\nSee [the code](src/lib.rs).\n",
    );
    write(
        dir.path(),
        "NOTES.md",
        "# Notes\n\nNothing links anywhere.\n",
    );
    dir
}

fn rules_of(findings: &[Finding]) -> Vec<String> {
    findings.iter().map(|f| f.rule.to_string()).collect()
}

#[test]
fn bare_marker_fires_and_second_run_hits_the_cache_with_identical_output() {
    let dir = fixture();
    let first = run(dir.path(), &quiet()).expect("first run");
    assert!(rules_of(&first.findings).contains(&"TODO001".to_owned()));
    assert_eq!(first.stats.file_hits, 0);
    assert!(first.stats.file_misses > 0);

    let second = run(dir.path(), &quiet()).expect("second run");
    assert_eq!(second.stats.file_misses, 0, "everything served from cache");
    assert!(second.stats.file_hits > 0);
    assert!(second.stats.repo_hits > 0);
    assert_eq!(second.stats.repo_misses, 0);
    assert_eq!(
        first.findings, second.findings,
        "cold and warm output match"
    );
}

#[test]
fn editing_a_file_invalidates_only_its_entries() {
    let dir = fixture();
    let first = run(dir.path(), &quiet()).expect("first run");
    write(
        dir.path(),
        "src/lib.rs",
        "//! Now clean.\n\n/// Documented.\npub fn documented() {}\n",
    );
    let second = run(dir.path(), &quiet()).expect("second run");
    assert!(second.stats.file_misses > 0, "edited file misses");
    assert!(second.stats.file_hits > 0, "untouched NOTES.md still hits");
    assert!(rules_of(&first.findings).contains(&"TODO001".to_owned()));
    assert!(!rules_of(&second.findings).contains(&"TODO001".to_owned()));
}

#[test]
fn only_filters_by_family_and_rejects_unknown_names() {
    let dir = fixture();
    let all = run(dir.path(), &quiet()).expect("all");
    assert!(rules_of(&all.findings).contains(&"DOC001".to_owned()));
    let only = run(
        dir.path(),
        &CheckOptions {
            only: vec!["todo".to_owned()],
            ..quiet()
        },
    )
    .expect("only");
    let rules = rules_of(&only.findings);
    assert!(!rules.is_empty());
    assert!(rules.iter().all(|r| r.starts_with("TODO")), "got {rules:?}");
    let err = run(
        dir.path(),
        &CheckOptions {
            only: vec!["NOPE".to_owned()],
            ..quiet()
        },
    )
    .expect_err("unknown family");
    assert!(err.to_string().contains("E-CHECK-ONLY"));
}

#[test]
fn fail_on_maps_severity_to_the_exit_code() {
    let dir = fixture();
    let default = run(dir.path(), &quiet()).expect("default");
    assert_eq!(
        default.exit_code(),
        ExitCode::Negative,
        "TODO001 is an error"
    );
    let none = run(
        dir.path(),
        &CheckOptions {
            fail_on: Some(FailOn::None),
            ..quiet()
        },
    )
    .expect("none");
    assert_eq!(none.exit_code(), ExitCode::Ok);
    // Only a warning-level rule present: error threshold passes, warn threshold fails.
    let warn_only = CheckOptions {
        only: vec!["DOC001".to_owned()],
        ..quiet()
    };
    assert_eq!(
        run(dir.path(), &warn_only).expect("error gate").exit_code(),
        ExitCode::Ok
    );
    let strict = CheckOptions {
        fail_on: Some(FailOn::Warn),
        ..warn_only
    };
    assert_eq!(
        run(dir.path(), &strict).expect("warn gate").exit_code(),
        ExitCode::Negative
    );
}

/// A test-only rule whose finding carries a Deterministic fix: `old` becomes `new`.
///
/// No shipped rule offers a Deterministic edit yet; DSL002 will once expansion exists.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "FIXT001",
    slug = "fixture-rewrite",
    family = "FIXT",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Deterministic,
    version = 1
)]
struct Fixt001;

/// Looks for `colour` in `*.txt` files and offers to rewrite it to `color`.
struct Rewrite;

static SIDE_INPUT: AtomicU32 = AtomicU32::new(0);

impl FileCheck<Frob> for Rewrite {
    fn rules(&self) -> Vec<&'static RuleMeta> {
        vec![Fixt001.meta()]
    }

    fn applies(&self, _ctx: &SharedCtx<'_>, path: &str) -> bool {
        Path::new(path).extension().is_some_and(|e| e == "txt")
    }

    fn side_input(&self, _c: &SharedCtx<'_>, _r: &RuleMeta, _p: &str, _t: &str) -> String {
        SIDE_INPUT.load(Ordering::SeqCst).to_string()
    }

    fn check(&self, _ctx: &CheckCtx<'_>, file: FileId, path: &str, text: &str) -> Vec<Finding> {
        let Some(start) = text.find("colour") else {
            return Vec::new();
        };
        let range = TextRange::at(
            TextSize::new(u32::try_from(start).expect("small")),
            TextSize::new(6),
        );
        let span = gob_text::Span::new(file, range);
        let id = Fixt001.meta().rule_id().expect("valid id");
        vec![
            Finding::new(
                id,
                gob_rules::Severity::Warn,
                Some(span),
                "spell it `color`",
                path,
            )
            .with_fix(Fix {
                kind: FixKind::Deterministic,
                title: "colour to color".to_owned(),
                edits: vec![TextEdit {
                    file,
                    range,
                    replacement: "color".to_owned(),
                }],
            }),
        ]
    }
}

fn with_rewrite() -> CheckOptions {
    CheckOptions {
        extra_checks: vec![Arc::new(Rewrite)],
        only: vec!["FIXT".to_owned()],
        ..quiet()
    }
}

#[test]
fn fix_rewrites_the_file_and_the_next_run_is_clean() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "notes.txt", "the colour red\n");
    let before = run(dir.path(), &with_rewrite()).expect("before");
    assert_eq!(rules_of(&before.findings), ["FIXT001"]);

    let fixed = run(
        dir.path(),
        &CheckOptions {
            fix: true,
            ..with_rewrite()
        },
    )
    .expect("fix run");
    let outcome = fixed.fix.expect("fix outcome");
    assert_eq!(outcome.applied.len(), 1);
    assert_eq!(outcome.applied[0].file, "notes.txt");
    assert_eq!(outcome.remaining, 0);
    assert_eq!(
        std::fs::read_to_string(dir.path().join("notes.txt")).expect("read"),
        "the color red\n"
    );
    let after = run(dir.path(), &with_rewrite()).expect("after");
    assert!(after.findings.is_empty(), "second run reports nothing");
}

#[test]
fn a_changed_side_input_misses_the_cache() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "a.txt", "plain\n");
    SIDE_INPUT.store(1, Ordering::SeqCst);
    let first = run(dir.path(), &with_rewrite()).expect("first");
    assert!(first.stats.file_misses > 0);
    let again = run(dir.path(), &with_rewrite()).expect("again");
    assert_eq!(again.stats.file_misses, 0);
    SIDE_INPUT.store(2, Ordering::SeqCst);
    let changed = run(dir.path(), &with_rewrite()).expect("changed");
    assert!(changed.stats.file_misses > 0, "new side input must miss");
    SIDE_INPUT.store(1, Ordering::SeqCst);
}

#[test]
fn fix_is_refused_without_a_ticket_when_the_knob_requires_scope() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "frob.toml",
        "[check]\nfix_requires_scope = true\n",
    );
    let err = run(
        dir.path(),
        &CheckOptions {
            fix: true,
            ..quiet()
        },
    )
    .expect_err("refused");
    assert!(err.to_string().contains("E-CHECK-FIX-SCOPE"));
}

#[test]
fn a_failing_tool_stage_yields_tool001_outside_the_budget() {
    let dir = fixture();
    write(
        dir.path(),
        "frob.toml",
        "[[check.tool]]\nname = \"always-fails\"\ncommand = \"false\"\n\n[[check.tool]]\nname = \"advisory\"\ncommand = \"false\"\nfail_on_nonzero = false\n",
    );
    let report = run(
        dir.path(),
        &CheckOptions {
            skip_tools: false,
            only: vec!["TOOL".to_owned()],
            ..quiet()
        },
    )
    .expect("run");
    assert_eq!(rules_of(&report.findings), ["TOOL001"]);
    assert!(report.findings[0].message.contains("always-fails"));
    let tool_stages: Vec<_> = report
        .timing
        .stages
        .iter()
        .filter(|s| !s.budgeted)
        .collect();
    assert_eq!(
        tool_stages.len(),
        2,
        "both stages are timed, apart from the budget"
    );
    assert!(tool_stages.iter().all(|s| s.name.starts_with("tool:")));
}

#[test]
fn telemetry_line_is_appended_when_enabled() {
    let dir = fixture();
    run(
        dir.path(),
        &CheckOptions {
            skip_telemetry: false,
            ..quiet()
        },
    )
    .expect("run");
    let text =
        std::fs::read_to_string(dir.path().join(".frob/telemetry.jsonl")).expect("telemetry");
    let line: serde_json::Value =
        serde_json::from_str(text.lines().next().expect("a line")).expect("json");
    assert!(line["duration_ms"].is_array());
    assert!(line["files"].as_u64().expect("files") >= 2);
    assert!(line["findings"]["error"].as_u64().expect("errors") >= 1);
    assert!(line.get("args").is_none());
}

#[test]
fn perf001_fires_only_when_enforced_and_over_budget() {
    let dir = fixture();
    write(
        dir.path(),
        "frob.toml",
        "[perf]\nenforce = true\nbudget_ms = 0\n",
    );
    // A zero budget is exceeded by any run that takes at least a millisecond.
    let mut fired = false;
    for _ in 0..5 {
        let r = run(dir.path(), &quiet()).expect("run");
        fired |= rules_of(&r.findings).contains(&"PERF001".to_owned());
    }
    assert!(fired, "PERF001 fires with a zero budget");
    write(
        dir.path(),
        "frob.toml",
        "[perf]\nenforce = false\nbudget_ms = 0\n",
    );
    let r = run(dir.path(), &quiet()).expect("run");
    assert!(!rules_of(&r.findings).contains(&"PERF001".to_owned()));
}

/// A repository with a ledger on `main` holding one ticket scoped to `src/a/**`.
fn ticket_fixture() -> (tempfile::TempDir, String) {
    ticket_fixture_scoped(&["src/a/**"])
}

/// [`ticket_fixture`] with the ticket scoped to `scope`.
fn ticket_fixture_scoped(scope: &[&str]) -> (tempfile::TempDir, String) {
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
            RelPath::new(".gitignore").expect("path"),
            Some(b".frob/\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut new = NewTicket::new("Scoped work", TicketType::Task);
    new.scope = scope.iter().map(|g| (*g).to_owned()).collect();
    let id = ledger.new_ticket(new).expect("ticket").ticket.front.id;
    (dir, id.to_string())
}

#[test]
fn ticket_restricts_per_file_rules_to_its_scope() {
    let (dir, id) = ticket_fixture();
    let bare = format!("// {}: later\n", marker());
    write(dir.path(), "src/a/lib.rs", &bare);
    write(dir.path(), "src/b/lib.rs", &bare);

    let unscoped = run(dir.path(), &quiet()).expect("unscoped");
    let todo_files = |r: &frob_check::CheckReport| -> Vec<String> {
        r.findings
            .iter()
            .filter(|f| f.rule.as_str() == "TODO001")
            .filter_map(|f| f.span.and_then(|s| r.files.path(s.file)).map(str::to_owned))
            .collect()
    };
    assert_eq!(todo_files(&unscoped), ["src/a/lib.rs", "src/b/lib.rs"]);

    let scoped = run(
        dir.path(),
        &CheckOptions {
            ticket: Some(id),
            ..quiet()
        },
    )
    .expect("scoped");
    assert_eq!(
        todo_files(&scoped),
        ["src/a/lib.rs"],
        "src/b is outside the scope"
    );
    assert_eq!(scoped.stats.files_checked, 1);
    // SCOPE001: the new file under src/b lies outside the ticket scope.
    let scope: Vec<_> = scoped
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "SCOPE001")
        .collect();
    assert!(
        scope.iter().any(|f| f.message.contains("src/b/lib.rs")),
        "SCOPE001 names src/b/lib.rs: {scope:?}"
    );
    assert!(scoped.scope.is_some());
}

#[test]
fn ticket_without_a_ledger_is_an_error() {
    let dir = fixture();
    let err = run(
        dir.path(),
        &CheckOptions {
            ticket: Some("~nothing".to_owned()),
            ..quiet()
        },
    )
    .expect_err("no ledger");
    assert!(err.to_string().contains("E-CHECK-NO-LEDGER"));
}

/// Emits one Unresolved `FIXT001` per `*.txt` file; the message is the file text.
struct Opaque;

impl FileCheck<Frob> for Opaque {
    fn rules(&self) -> Vec<&'static RuleMeta> {
        vec![Fixt001.meta()]
    }

    fn applies(&self, _ctx: &SharedCtx<'_>, path: &str) -> bool {
        Path::new(path).extension().is_some_and(|e| e == "txt")
    }

    fn check(&self, _ctx: &CheckCtx<'_>, _file: FileId, path: &str, text: &str) -> Vec<Finding> {
        let id = Fixt001.meta().rule_id().expect("valid id");
        let f = Finding::new(id, gob_rules::Severity::Unresolved, None, text.trim(), path);
        // The reason is typed by the producer, never read back from the message.
        vec![if text.starts_with("annotation-required") {
            f.with_reason(gob_rules::UnresolvedReason::AnnotationSignature)
        } else {
            f
        }]
    }
}

fn opaque_options() -> CheckOptions {
    CheckOptions {
        extra_checks: vec![Arc::new(Opaque)],
        only: vec!["FIXT".to_owned()],
        ..quiet()
    }
}

fn tool_options() -> CheckOptions {
    CheckOptions {
        skip_tools: false,
        only: vec!["TOOL".to_owned()],
        ..quiet()
    }
}

const MISSING_TOOL: &str = "[[check.tool]]\nname = \"ghost\"\ncommand = \"frob-no-such-binary\"\n";

const FAILING_ACTIONLINT: &str = "[[check.tool]]\nname = \"lint\"\ncommand = \"sh\"\nargs = [\"-c\", \"echo unsatisfiable pin >&2; exit 2\"]\nparser = \"actionlint-json\"\nversion_args = [\"-c\", \"echo 1.7.12\"]\n";

// frob:tests crates/gob-check/src/tools.rs::start_tools
#[test]
fn a_failed_parsed_tool_fails_the_default_gate_with_its_stderr() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "frob.toml", FAILING_ACTIONLINT);
    let report = run(dir.path(), &tool_options()).expect("default policy");
    assert_eq!(rules_of(&report.findings), ["TOOL001"]);
    assert_eq!(
        report.findings[0].required,
        Some(RequiredReason::ToolFailed {
            stage: "lint".to_owned()
        })
    );
    assert!(
        report.findings[0].message.contains("unsatisfiable pin"),
        "{}",
        report.findings[0].message
    );
    assert_eq!(report.exit_code(), ExitCode::Negative);
}

#[test]
fn a_missing_tool_binary_fails_under_required_and_passes_under_never() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "frob.toml", MISSING_TOOL);
    let report = run(dir.path(), &tool_options()).expect("required");
    assert_eq!(rules_of(&report.findings), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, gob_rules::Severity::Unresolved);
    assert_eq!(
        report.findings[0].required.as_ref(),
        Some(&RequiredReason::ToolFailed {
            stage: "ghost".to_owned()
        })
    );
    assert_eq!(report.required_unresolved(), 1);
    assert_eq!(report.exit_code(), ExitCode::Negative);

    write(
        dir.path(),
        "frob.toml",
        &format!("[check]\nfail_on_unresolved = \"never\"\n\n{MISSING_TOOL}"),
    );
    let never = run(dir.path(), &tool_options()).expect("never");
    assert_eq!(never.findings.len(), 1, "still reported");
    assert_eq!(never.exit_code(), ExitCode::Ok);

    write(
        dir.path(),
        "frob.toml",
        &format!("[check]\nfail_on_unresolved = \"all\"\n\n{MISSING_TOOL}"),
    );
    assert_eq!(
        run(dir.path(), &tool_options()).expect("all").exit_code(),
        ExitCode::Negative
    );
}

#[test]
fn a_non_required_unresolved_finding_passes_under_required_and_fails_under_all() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "notes.txt", "sample too small\n");
    let report = run(dir.path(), &opaque_options()).expect("required");
    assert_eq!(report.findings.len(), 1);
    assert!(report.findings[0].required.is_none());
    assert_eq!(report.exit_code(), ExitCode::Ok);

    write(
        dir.path(),
        "frob.toml",
        "[check]\nfail_on_unresolved = \"all\"\n",
    );
    let all = run(dir.path(), &opaque_options()).expect("all");
    assert_eq!(all.exit_code(), ExitCode::Negative);
}

#[test]
fn an_annotation_required_unresolved_finding_is_marked_required() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "notes.txt",
        "annotation-required: opaque-fn on a public item\n",
    );
    let report = run(dir.path(), &opaque_options()).expect("run");
    assert_eq!(
        report.findings[0].required.as_ref(),
        Some(&RequiredReason::AnnotationRequired {
            code: "signature".to_owned(),
            public_surface: true
        })
    );
    assert_eq!(report.exit_code(), ExitCode::Negative);
}

fn scope001_paths(r: &frob_check::CheckReport) -> Vec<String> {
    r.findings
        .iter()
        .filter(|f| f.rule.as_str() == "SCOPE001")
        .map(|f| f.message.clone())
        .collect()
}

fn ticket_opts(id: &str) -> CheckOptions {
    CheckOptions {
        ticket: Some(id.to_owned()),
        base: Some("main".to_owned()),
        ..quiet()
    }
}

/// Branch `work` off `main` in `ticket_fixture`, then commit `files` onto `main` behind it.
fn branched(files: &[(&str, &str)], on_main: &[(&str, &str)]) -> (tempfile::TempDir, String) {
    branched_in(ticket_fixture(), files, on_main)
}

/// [`branched`] over an existing fixture.
fn branched_in(
    (dir, id): (tempfile::TempDir, String),
    files: &[(&str, &str)],
    on_main: &[(&str, &str)],
) -> (tempfile::TempDir, String) {
    let repo = Repo::discover(dir.path()).expect("discover");
    let opts = CommitOptions::default();
    let put = |r: &str, set: &[(&str, &str)], msg: &str| {
        let changes: Vec<_> = set
            .iter()
            .map(|(p, c)| (RelPath::new(*p).expect("path"), Some(c.as_bytes().to_vec())))
            .collect();
        repo.commit_paths(r, &changes, msg, &opts).expect("commit");
    };
    let tip = repo.rev_parse("main").expect("main");
    std::fs::write(repo.git_dir().join("refs/heads/work"), format!("{tip}\n")).expect("branch");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/work\n").expect("head");
    put("refs/heads/work", files, "work");
    put("refs/heads/main", on_main, "tickets(land): ~X unrelated");
    (dir, id)
}

// frob:tests crates/frob-check/src/scope.rs::branch_changes
#[test]
fn lock_files_written_by_ack_are_not_scope001_but_other_edits_are() {
    let (dir, id) = branched(
        &[
            ("frob.lock", "version = 2\ndigest_scheme = 2\n"),
            ("grimble.lock", "# written by grimble\n"),
            ("src/a/lib.rs", "pub fn a() {}\n"),
            ("docs/hand-edit.md", "# edited by hand\n"),
        ],
        &[],
    );
    let report = run(dir.path(), &ticket_opts(&id)).expect("run");
    let flagged = scope001_paths(&report);
    assert!(
        flagged.iter().any(|m| m.contains("docs/hand-edit.md")),
        "a hand edit outside the lease still fires: {flagged:?}"
    );
    assert!(
        !flagged.iter().any(|m| m.contains(".lock")),
        "lock bookkeeping is exempt: {flagged:?}"
    );
}

#[test]
fn base_advancing_does_not_leak_into_scope001() {
    let (dir, id) = branched(
        &[("src/a/lib.rs", "pub fn a() {}\n")],
        &[
            ("src/b/lib.rs", "pub fn b() {}\n"),
            ("tickets/OTHER/ticket.md", "x\n"),
        ],
    );
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    assert!(scope001_paths(&r).is_empty(), "{:?}", scope001_paths(&r));
}

#[test]
fn a_branch_touching_an_out_of_scope_file_still_fires_scope001() {
    let (dir, id) = branched(
        &[
            ("src/a/lib.rs", "pub fn a() {}\n"),
            ("src/c/lib.rs", "pub fn c() {}\n"),
        ],
        &[("src/b/lib.rs", "pub fn b() {}\n")],
    );
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    let hits = scope001_paths(&r);
    assert_eq!(hits.len(), 1, "{hits:?}");
    assert!(hits[0].contains("src/c/lib.rs"), "{hits:?}");
}

#[test]
fn the_ledger_directory_is_exempt_from_scope001() {
    let (dir, id) = branched(
        &[
            ("src/a/lib.rs", "pub fn a() {}\n"),
            ("tickets/MINE/events/1.md", "e\n"),
        ],
        &[("src/b/lib.rs", "pub fn b() {}\n")],
    );
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    assert!(scope001_paths(&r).is_empty(), "{:?}", scope001_paths(&r));
}

#[test]
fn uncommitted_out_of_scope_edits_still_fire_scope001() {
    let (dir, id) = branched(
        &[("src/a/lib.rs", "pub fn a() {}\n")],
        &[("src/b/lib.rs", "pub fn b() {}\n")],
    );
    write(dir.path(), "src/d/lib.rs", "pub fn d() {}\n");
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    let hits = scope001_paths(&r);
    assert_eq!(hits.len(), 1, "{hits:?}");
    assert!(hits[0].contains("src/d/lib.rs"), "{hits:?}");
}

// frob:tests crates/frob-check/src/scope.rs::branch_changes
#[cfg(unix)]
#[test]
fn untouched_symlinks_never_fire_scope001_and_a_retarget_does() {
    let (dir, id) = ticket_fixture();
    let root = dir.path();
    let git = |args: &[&str]| {
        let out = std::process::Command::new("git")
            .current_dir(root)
            .args(["-c", "user.name=T", "-c", "user.email=t@example.com"])
            .args(args)
            .output()
            .expect("git runs");
        assert!(out.status.success(), "git {args:?}: {out:?}");
    };
    git(&["config", "core.autocrlf", "true"]);
    write(root, "280/L/hello_1.c", "int main(void) { return 0; }\n");
    std::os::unix::fs::symlink("../../280/L/hello_1.c", root.join("link_file.c")).expect("link");
    std::os::unix::fs::symlink("280/L", root.join("link_dir")).expect("link");
    git(&["add", "-A"]);
    git(&["commit", "-q", "-m", "tickets(land): ~X links on main"]);
    git(&["checkout", "-q", "-b", "work"]);
    write(root, "src/a/lib.rs", "pub fn a() {}\n");
    git(&["add", "-A"]);
    git(&["commit", "-q", "-m", "work"]);

    let r = run(root, &ticket_opts(&id)).expect("run");
    assert!(scope001_paths(&r).is_empty(), "{:?}", scope001_paths(&r));

    std::fs::remove_file(root.join("link_file.c")).expect("rm");
    std::os::unix::fs::symlink("src/a/lib.rs", root.join("link_file.c")).expect("relink");
    let r = run(root, &ticket_opts(&id)).expect("run");
    let hits = scope001_paths(&r);
    assert_eq!(hits.len(), 1, "{hits:?}");
    assert!(hits[0].contains("link_file.c"), "{hits:?}");
}

/// Unresolved findings of `report` as (rule, reason) pairs.
fn zero_subject_rules(report: &frob_check::CheckReport) -> Vec<String> {
    report
        .findings
        .iter()
        .filter(|f| f.required.is_some())
        .map(|f| f.rule.to_string())
        .collect()
}

// frob:tests crates/frob-check/src/product.rs::applicable
#[test]
fn a_configured_ledger_that_is_absent_fails_the_gate_but_an_unconfigured_one_does_not() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "README.md", "# Plain\n");
    let silent = run(dir.path(), &quiet()).expect("unconfigured");
    assert!(
        zero_subject_rules(&silent).is_empty(),
        "no ledger expected, none missed"
    );
    assert_eq!(silent.exit_code(), ExitCode::Ok);

    write(dir.path(), "frob.toml", "[tickets]\n");
    // Nothing references a ticket or a todo owner: not applicable, not a required silence.
    let nothing = run(dir.path(), &quiet()).expect("configured, no references");
    assert!(
        zero_subject_rules(&nothing).is_empty(),
        "nothing to resolve"
    );
    assert_eq!(nothing.exit_code(), ExitCode::Ok);

    // Wiring-bug pattern: the facts exist (a reference and a todo owner) but the missing ledger gives
    // the rules no subject; they must still be flagged, not silently not-applicable.
    write(
        dir.path(),
        "src/lib.rs",
        "// frob:ticket 01M4069Z0HH5RV8TNPFVA936C5\n// frob:todo 01M4069Z0HH5RV8TNPFVA936C5\npub const X: u8 = 1;\n",
    );
    let configured = run(dir.path(), &quiet()).expect("configured");
    let mut rules = zero_subject_rules(&configured);
    rules.sort();
    assert_eq!(rules, ["REF001", "TODO002"]);
    assert_eq!(configured.exit_code(), ExitCode::Negative);
    let required = configured
        .findings
        .iter()
        .find(|f| f.required.is_some())
        .expect("a required finding");
    assert_eq!(
        required.required.as_ref(),
        Some(&RequiredReason::ZeroSubjects {
            rule: required.rule.to_string()
        })
    );
}

// frob:tests crates/frob-check/src/product.rs::applicable
#[test]
fn cov001_counts_rust_files_and_is_not_required_without_a_test_capable_language() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/lib.rs",
        "//! Only data.\npub const X: u8 = 1;\n",
    );
    let rust = run(dir.path(), &quiet()).expect("rust without functions");
    assert!(
        zero_subject_rules(&rust).is_empty(),
        "the Rust file is a subject"
    );
    assert_eq!(rust.subjects_examined.get("COV001"), Some(&1));

    let docs = tempfile::tempdir().expect("tempdir");
    write(docs.path(), "README.md", "# Docs only\n");
    let md = run(docs.path(), &quiet()).expect("markdown only");
    assert!(
        zero_subject_rules(&md).is_empty(),
        "no test capability, no required silence"
    );
    assert_eq!(md.subjects_examined.get("COV001"), Some(&0));
}

// frob:ticket 01M4069Z0HH5RV8TNPFVA936C5
// frob:tests crates/frob-check/src/product.rs::ledger_rule_applicable
#[test]
fn ref001_and_todo002_apply_only_when_they_have_a_reference_to_judge() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "frob.toml", "[tickets]\n");
    write(
        dir.path(),
        "src/lib.rs",
        "// frob:todo 01M4069Z0HH5RV8TNPFVA936C5\npub const X: u8 = 1;\n",
    );
    let todo_only = run(dir.path(), &quiet()).expect("todo only");
    assert_eq!(
        zero_subject_rules(&todo_only),
        ["TODO002"],
        "a todo directive makes TODO002 apply, not REF001"
    );

    write(
        dir.path(),
        "src/lib.rs",
        "// frob:ticket 01M4069Z0HH5RV8TNPFVA936C5\npub const X: u8 = 1;\n",
    );
    let ref_only = run(dir.path(), &quiet()).expect("ref only");
    assert_eq!(
        zero_subject_rules(&ref_only),
        ["REF001"],
        "a ticket reference makes REF001 apply, not TODO002"
    );

    let bare = tempfile::tempdir().expect("tempdir");
    write(
        bare.path(),
        "src/lib.rs",
        "// TODO: later\npub const X: u8 = 1;\n",
    );
    write(bare.path(), "frob.toml", "[tickets]\n");
    let markers = run(bare.path(), &quiet()).expect("bare marker");
    assert!(
        zero_subject_rules(&markers).is_empty(),
        "a bare marker is TODO001's subject, not TODO002's"
    );
}

/// A ULID no fixture ticket owns.
const OTHER_ULID: &str = "01ARZ3NDEKTSV4RRFFQ69G5FAV";

// frob:tests crates/frob-check/src/scope.rs::branch_changes
#[test]
fn a_tickets_own_fragment_is_never_scope001() {
    let (dir, id) = ticket_fixture();
    let own = format!("changelog.d/{id}.added.md");
    let (dir, id) = branched_in(
        (dir, id),
        &[
            ("src/a/lib.rs", "pub fn a() {}\n"),
            (&own, "Added a thing.\n"),
        ],
        &[],
    );
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    assert!(scope001_paths(&r).is_empty(), "{:?}", scope001_paths(&r));
}

// frob:tests crates/frob-check/src/scope.rs::branch_changes
#[test]
fn another_tickets_or_a_malformed_fragment_is_still_scope001() {
    let (dir, id) = ticket_fixture();
    let other = format!("changelog.d/{OTHER_ULID}.added.md");
    let malformed = format!("changelog.d/{id}.bogus.md");
    let (dir, id) = branched_in(
        (dir, id),
        &[
            ("src/a/lib.rs", "pub fn a() {}\n"),
            (&other, "x\n"),
            (&malformed, "x\n"),
        ],
        &[],
    );
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    let hits = scope001_paths(&r);
    assert_eq!(hits.len(), 2, "{hits:?}");
    assert!(hits.iter().any(|m| m.contains(OTHER_ULID)), "{hits:?}");
    assert!(hits.iter().any(|m| m.contains(".bogus.md")), "{hits:?}");
}

// frob:tests crates/frob-check/src/scope.rs::resolve
#[test]
fn a_recorded_changelog_d_glob_still_checks_but_covers_only_the_own_fragment() {
    let fixture = ticket_fixture_scoped(&["src/a/**", "changelog.d/**"]);
    let own = format!("changelog.d/{}.fixed.md", fixture.1);
    let other = format!("changelog.d/{OTHER_ULID}.fixed.md");
    let (dir, id) = branched_in(
        fixture,
        &[
            ("src/a/lib.rs", "pub fn a() {}\n"),
            (&own, "Fixed.\n"),
            (&other, "x\n"),
        ],
        &[],
    );
    let r = run(dir.path(), &ticket_opts(&id)).expect("run");
    let hits = scope001_paths(&r);
    assert_eq!(
        hits.len(),
        1,
        "the glob no longer licenses foreign fragments: {hits:?}"
    );
    assert!(hits[0].contains(OTHER_ULID), "{hits:?}");
}

/// `check --ticket` findings of rule `rule` for the ticket of `ticket_fixture`.
fn ticket_rule_messages(dir: &Path, id: &str, rule: &str) -> Vec<String> {
    let r = run(
        dir,
        &CheckOptions {
            ticket: Some(id.to_owned()),
            ..quiet()
        },
    )
    .expect("scoped run");
    r.findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .map(|f| f.message.clone())
        .collect()
}

#[test]
fn rel003_ticket_without_a_fragment_reports_with_the_remedy() {
    // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
    // frob:tests crates/frob-release/src/rel003.rs::missing
    let (dir, id) = ticket_fixture();
    let msgs = ticket_rule_messages(dir.path(), &id, "REL003");
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    assert!(msgs[0].contains("frob ticket fragment"), "{}", msgs[0]);
    assert!(msgs[0].contains(&id), "{}", msgs[0]);
}

#[test]
fn rel003_is_clean_for_an_exempted_ticket_by_event_or_by_option() {
    // frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
    // frob:tests crates/frob-release/src/rel003.rs::missing
    let (dir, id) = ticket_fixture();
    assert_eq!(ticket_rule_messages(dir.path(), &id, "REL003").len(), 1);
    let by_option = run(
        dir.path(),
        &CheckOptions {
            ticket: Some(id.clone()),
            changelog_exempt: true,
            ..quiet()
        },
    )
    .expect("exempt run");
    assert!(
        by_option
            .findings
            .iter()
            .all(|f| f.rule.as_str() != "REL003")
    );
    let repo = Repo::discover(dir.path()).expect("discover");
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let ticket: frob_ledger::TicketId = id.parse().expect("id");
    ledger
        .append(
            ticket,
            frob_ledger::event::EventBody::ChangelogExempt(
                frob_ledger::event::ChangelogExemptData {
                    reason: "design only".to_owned(),
                },
            ),
        )
        .expect("append");
    assert!(ticket_rule_messages(dir.path(), &id, "REL003").is_empty());
}

#[test]
fn rel003_invalid_fragment_reports_the_validation_message_and_valid_is_clean() {
    // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
    // frob:tests crates/frob-release/src/rel003.rs::evaluate
    let (dir, id) = ticket_fixture();
    write(
        dir.path(),
        &format!("changelog.d/{id}.improved.md"),
        "frob: x.\n",
    );
    let msgs = ticket_rule_messages(dir.path(), &id, "REL003");
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    assert!(msgs[0].contains("unknown type `improved`"), "{}", msgs[0]);
    std::fs::remove_file(dir.path().join(format!("changelog.d/{id}.improved.md"))).unwrap();
    write(dir.path(), &format!("changelog.d/{id}.fixed.md"), "\n");
    let msgs = ticket_rule_messages(dir.path(), &id, "REL003");
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    std::fs::remove_file(dir.path().join(format!("changelog.d/{id}.fixed.md"))).unwrap();
    write(
        dir.path(),
        &format!("changelog.d/{id}.changed.md"),
        "frob: Changed.\n",
    );
    assert!(ticket_rule_messages(dir.path(), &id, "REL003").is_empty());
}

/// `--ticket` fixture: two untouched files on `main` with findings, one touched file on the branch.
fn lead_fixture() -> (tempfile::TempDir, String, gob_cli::Cli) {
    let (dir, id) = ticket_fixture();
    let bare = "pub fn f() {}\n".to_owned();
    write(dir.path(), "src/b/lib.rs", &bare);
    write(dir.path(), "src/c/lib.rs", &bare);
    let repo = Repo::discover(dir.path()).expect("discover");
    let changes: Vec<_> = ["src/b/lib.rs", "src/c/lib.rs"]
        .iter()
        .map(|p| {
            (
                RelPath::new(*p).expect("path"),
                Some(bare.clone().into_bytes()),
            )
        })
        .collect();
    repo.commit_paths(
        "refs/heads/main",
        &changes,
        "base",
        &CommitOptions::default(),
    )
    .expect("commit");
    drop(repo);
    let (dir, id) = branched_in((dir, id), &[("src/a/lib.rs", bare.as_str())], &[]);
    write(dir.path(), "src/a/lib.rs", &bare);
    (
        dir,
        id,
        frob_check::register(gob_cli::Cli::new("frob", "0.0.0")),
    )
}

// frob:ticket 01M413V8CDKKBSBV8JDV92VDGB
// frob:tests crates/frob-check/src/verb.rs::lead_lines
#[test]
fn ticket_text_leads_with_diff_findings_and_counts_the_rest() {
    let (dir, id, cli) = lead_fixture();
    let args = [
        "check",
        "--ticket",
        id.as_str(),
        "--base",
        "main",
        "--text",
        "--fail-on",
        "none",
    ];
    let (code, out, err) = gob_cli::run_for_test(&cli, &args, dir.path());
    assert_eq!(code, 0, "{err}");
    assert!(
        out.contains("src/a/lib.rs"),
        "diff finding listed in full: {out}"
    );
    assert!(
        !out.contains("src/b/lib.rs"),
        "untouched file summarised: {out}"
    );
    assert!(
        !out.contains("src/c/lib.rs"),
        "untouched file summarised: {out}"
    );
    assert!(
        out.contains("outside this ticket's diff") && out.contains("COV001"),
        "per-rule count line: {out}"
    );
    assert!(out.contains("x2"), "two findings counted: {out}");

    let verbose = [
        "-v",
        "check",
        "--ticket",
        id.as_str(),
        "--base",
        "main",
        "--text",
        "--fail-on",
        "none",
    ];
    let (_, out, _) = gob_cli::run_for_test(&cli, &verbose, dir.path());
    assert!(out.contains("src/b/lib.rs"), "-v lists everything: {out}");
    assert!(!out.contains("outside this ticket's diff"), "{out}");
}

// frob:ticket 01M413V8CDKKBSBV8JDV92VDGB
// frob:tests crates/frob-check/src/verb.rs::lead_lines
#[test]
fn ticket_json_keeps_every_finding_and_errors_outside_the_diff_print_in_full() {
    let (dir, id, cli) = lead_fixture();
    let args = [
        "check",
        "--ticket",
        id.as_str(),
        "--base",
        "main",
        "--json",
        "--fail-on",
        "none",
    ];
    let (code, out, err) = gob_cli::run_for_test(&cli, &args, dir.path());
    assert_eq!(code, 0, "{err}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json");
    let files: Vec<&str> = v["data"]["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter_map(|f| f["file"].as_str())
        .collect();
    for want in ["src/a/lib.rs", "src/b/lib.rs", "src/c/lib.rs"] {
        assert!(files.contains(&want), "{want} present in JSON: {files:?}");
    }
    assert_eq!(v["data"]["elsewhere"].as_array().map(Vec::len), Some(0));

    // Failing on warnings makes the outside findings blocking: they print in full.
    let strict = [
        "check",
        "--ticket",
        id.as_str(),
        "--base",
        "main",
        "--text",
        "--fail-on",
        "warn",
    ];
    let (code, _, err) = gob_cli::run_for_test(&cli, &strict, dir.path());
    assert_eq!(code, 1);
    assert!(
        err.contains("src/b/lib.rs"),
        "blocking finding outside the diff is shown: {err}"
    );
}

// frob:ticket 01M42M1KK02KFZG39CXKAD47SZ
// frob:tests crates/frob-check/src/verb.rs::lead_lines
#[test]
fn ticket_text_never_folds_a_required_unreadable_finding_into_a_count() {
    let (dir, id, cli) = lead_fixture();
    std::fs::write(
        dir.path().join("docs-bad.md"),
        [b'#', b' ', 0xff, 0xfe, b'\n'],
    )
    .unwrap();
    let args = [
        "check",
        "--ticket",
        id.as_str(),
        "--base",
        "main",
        "--text",
        "--fail-on",
        "none",
    ];
    let (code, out, err) = gob_cli::run_for_test(&cli, &args, dir.path());
    assert_eq!(code, 1, "required Unresolved fails the gate: {out}{err}");
    assert!(
        err.contains("READ001") && err.contains("docs-bad.md"),
        "named in full although outside the diff: {err}"
    );
}

// frob:ticket 01M42MGNE7XHTT1MR5CA6C2R1C
// frob:tests crates/frob-check/src/product.rs::settle
#[test]
fn a_corrupt_ledger_index_is_required_unresolved_findings_and_fails_the_gate() {
    let (dir, _id) = ticket_fixture();
    let index = dir.path().join(".frob/tickets.sqlite");
    assert!(index.exists(), "the fixture builds the index");
    // No prior check run: a cached clean result would be replayed for the unchanged ledger tip.
    std::fs::write(
        &index,
        b"this is not a sqlite database at all, just bytes\n",
    )
    .expect("corrupt");
    for ext in ["-wal", "-shm"] {
        let _ = std::fs::remove_file(dir.path().join(format!(".frob/tickets.sqlite{ext}")));
    }
    let report = run(dir.path(), &quiet()).expect("corrupt run");
    let failed: Vec<&Finding> = report
        .findings
        .iter()
        .filter(|f| f.required.is_some() && f.message.contains("evaluation-failed"))
        .collect();
    assert!(!failed.is_empty(), "{:?}", report.findings);
    for f in &failed {
        assert_eq!(f.severity, gob_rules::Severity::Unresolved);
    }
    assert_eq!(report.exit_code(), ExitCode::Negative, "the gate fails");
    assert!(
        failed
            .iter()
            .all(|f| matches!(f.required, Some(RequiredReason::EvaluationFailed { .. })))
    );
    // Repair the index: the failure was never cached, so the next run evaluates fresh and is clean.
    std::fs::remove_file(&index).expect("remove corrupt index");
    let repaired = run(dir.path(), &quiet()).expect("repaired run");
    assert!(
        repaired
            .findings
            .iter()
            .all(|f| !matches!(f.required, Some(RequiredReason::EvaluationFailed { .. }))),
        "{:?}",
        repaired.findings
    );
}

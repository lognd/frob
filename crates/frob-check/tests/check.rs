//! End-to-end behaviour of the pipeline over temp repositories.

use std::path::Path;
use std::sync::Arc;
use std::sync::atomic::{AtomicU32, Ordering};

use frob_check::{CheckCtx, CheckOptions, FailOn, FileCheck, SharedCtx, run};
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

impl FileCheck for Rewrite {
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
    let ledger = Ledger::open(repo, LedgerConfig::default());
    let mut new = NewTicket::new("Scoped work", TicketType::Task);
    new.scope = vec!["src/a/**".to_owned()];
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
    assert!(scoped.ticket.is_some());
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

impl FileCheck for Opaque {
    fn rules(&self) -> Vec<&'static RuleMeta> {
        vec![Fixt001.meta()]
    }

    fn applies(&self, _ctx: &SharedCtx<'_>, path: &str) -> bool {
        Path::new(path).extension().is_some_and(|e| e == "txt")
    }

    fn check(&self, _ctx: &CheckCtx<'_>, _file: FileId, path: &str, text: &str) -> Vec<Finding> {
        let id = Fixt001.meta().rule_id().expect("valid id");
        vec![Finding::new(
            id,
            gob_rules::Severity::Unresolved,
            None,
            text.trim(),
            path,
        )]
    }
}

fn opaque_options() -> CheckOptions {
    CheckOptions {
        extra_checks: vec![Arc::new(Opaque)],
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

#[test]
fn a_missing_tool_binary_fails_under_required_and_passes_under_never() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "frob.toml", MISSING_TOOL);
    let report = run(dir.path(), &tool_options()).expect("required");
    assert_eq!(rules_of(&report.findings), ["TOOL001"]);
    assert_eq!(report.findings[0].severity, gob_rules::Severity::Unresolved);
    assert_eq!(
        report.required.get(&report.findings[0]),
        Some(&RequiredReason::SiblingMissing {
            product: "frob-no-such-binary".to_owned()
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
    assert!(report.required.is_empty());
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
        report.required.get(&report.findings[0]),
        Some(&RequiredReason::AnnotationRequired {
            code: "opaque-fn".to_owned(),
            public_surface: true
        })
    );
    assert_eq!(report.exit_code(), ExitCode::Negative);
}

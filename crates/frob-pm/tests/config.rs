//! The `[pm]` config tables: defaults, loading and refusal of unknown names.
// frob:ticket 01M4069R19D2KZENDGEH83JZSW

use frob_pm::{DoneRequirement, PmConfig, Pull, ReadyRequirement};

fn load(toml: &str) -> Result<PmConfig, gob_config::ConfigError> {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("frob.toml"), toml).expect("write");
    PmConfig::load(dir.path())
}

#[test]
fn missing_file_loads_the_documented_defaults() {
    let dir = tempfile::tempdir().expect("tempdir");
    let cfg = PmConfig::load(dir.path()).expect("defaults");
    assert_eq!(cfg.pm.pull, Pull::Rank);
    assert_eq!(cfg.pm.ready_min, 4);
    assert_eq!(cfg.pm.cycle_days, 7);
    assert_eq!(cfg.pm.min_history, 3);
    assert!((cfg.pm.capacity_k - 0.5).abs() < f64::EPSILON);
    assert_eq!(cfg.pm.ready_requires, ReadyRequirement::ALL);
    assert_eq!(cfg.pm.done_requires, DoneRequirement::DEFAULT);
    assert_eq!(cfg.wip.in_progress_per_identity, 1);
    assert_eq!(cfg.wip.in_progress, 2);
    assert_eq!(cfg.classes.expedite_max, 1);
    assert!((cfg.classes.intangible_share - 0.2).abs() < f64::EPSILON);
}

#[test]
fn file_values_override_defaults_across_the_nested_tables() {
    let cfg = load(
        "[pm]\nready_min = 6\nready_requires = [\"points\", \"scope\"]\n[pm.wip]\nin_progress = 3\n[pm.classes]\nintangible_share = 0.1\n",
    )
    .expect("load");
    assert_eq!(cfg.pm.ready_min, 6);
    assert_eq!(
        cfg.pm.ready_requires,
        [ReadyRequirement::Points, ReadyRequirement::Scope]
    );
    assert_eq!(cfg.wip.in_progress, 3);
    assert_eq!(cfg.wip.in_progress_per_identity, 1);
    assert!((cfg.classes.intangible_share - 0.1).abs() < f64::EPSILON);
}

#[test]
fn unknown_requirement_name_is_refused_with_did_you_mean() {
    let err = load("[pm]\nready_requires = [\"criterai\"]\n").expect_err("refused");
    let text = err.to_string();
    assert!(
        text.contains("unknown ready requirement `criterai`"),
        "{text}"
    );
    assert!(text.contains("did you mean `criteria`?"), "{text}");

    let err = load("[pm]\ndone_requires = [\"no_open_child\"]\n").expect_err("refused");
    assert!(
        err.to_string().contains("did you mean `no_open_children`?"),
        "{err}"
    );
}

#[test]
fn a_done_name_is_not_a_ready_name() {
    let err = load("[pm]\nready_requires = [\"criteria_evidenced\"]\n").expect_err("refused");
    assert!(
        err.to_string().contains("unknown ready requirement"),
        "{err}"
    );
}

#[test]
fn unknown_pm_key_is_reported_with_did_you_mean() {
    let err = load("[pm]\nready_mn = 4\n").expect_err("refused");
    assert!(
        err.to_string().contains("did you mean `ready_min`?"),
        "{err}"
    );
    let err = load("[pm.wip]\nin_progres = 1\n").expect_err("refused");
    assert!(
        err.to_string().contains("did you mean `in_progress`?"),
        "{err}"
    );
}

#[test]
fn unknown_pull_policy_is_refused() {
    let err = load("[pm]\npull = \"rnak\"\n").expect_err("refused");
    assert!(err.to_string().contains("did you mean `rank`?"), "{err}");
}

// frob:ticket 01M4GWKEMB266C6GTFEP4R3G7W
#[test]
fn repo_wide_tables_come_from_the_base_ref_over_a_stale_worktree_copy() {
    use gob_git::{CommitOptions, RelPath, Repo};
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = Repo::init(dir.path()).expect("init");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = T\n\temail = t@example.com\n"),
    )
    .expect("identity");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("frob.toml").expect("path"),
            Some(b"[pm.wip]\nin_progress = 16\n".to_vec()),
        )],
        "base config",
        &CommitOptions::default(),
    )
    .expect("commit");
    std::fs::write(dir.path().join("frob.toml"), "[pm.wip]\nin_progress = 10\n").expect("stale");
    let cfg = PmConfig::load_repo_wide(dir.path(), "refs/heads/main").expect("load");
    assert_eq!(cfg.wip.in_progress, 16);
    let fallback = PmConfig::load_repo_wide(dir.path(), "refs/heads/nope").expect("fallback");
    assert_eq!(fallback.wip.in_progress, 10);
}

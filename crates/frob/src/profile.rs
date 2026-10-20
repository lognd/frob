//! Reader-profile behaviours (`navigation.md` section 4.1): what the newcomer and experienced profiles
//! change in presentation. A profile never changes what a check decides and never a gate.

// frob:ticket 01M3ZX87VKDKC0N65NH77EBEJP

use std::path::Path;

use gob_cli::{Context, Presenter};
use gob_diagnostics::{SeenStore, TeachMode};
use serde_json::Value;

/// Rule occurrences taught in full under the newcomer profile before dropping to `first`.
pub const NEWCOMER_TEACH_OCCURRENCES: usize = 5;

/// The guide page named when a newcomer's command fails.
pub const GUIDE_PAGE: &str = "docs/guides/quickstart.md";

/// The reader profile in force.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Profile {
    /// Teach more, point at the next step, good-first tickets first.
    Newcomer,
    /// Terse: no hints, priority order.
    Experienced,
}

/// How much of a rule's explain text to print inline (the `[ui] teach` values).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Teach {
    /// Every occurrence.
    Always,
    /// The first occurrence only.
    First,
}

impl Profile {
    /// The profile recorded for the repository at `root`; the newcomer default when none is chosen.
    pub fn at(root: &Path) -> Self {
        let chosen = crate::profile_cmd::chosen_profile(root);
        let profile = match chosen.as_deref() {
            Some("experienced") => Self::Experienced,
            _ => Self::Newcomer,
        };
        tracing::debug!(?profile, "reader profile resolved");
        profile
    }

    /// The profile for the repository containing `cwd`; the newcomer default outside a repository.
    pub fn for_cwd(cwd: &Path) -> Self {
        match crate::workspace::Located::discover(cwd).into_repo() {
            Ok((_, root)) => Self::at(&root),
            Err(_) => Self::Newcomer,
        }
    }

    /// The teach mode for a rule already shown `seen` times: newcomers get `Always` for the first
    /// [`NEWCOMER_TEACH_OCCURRENCES`], then `First`; experienced is always `First`.
    pub fn teach_for(self, seen: usize) -> Teach {
        match self {
            Self::Newcomer if seen < NEWCOMER_TEACH_OCCURRENCES => Teach::Always,
            _ => Teach::First,
        }
    }
}

/// Where the local teaching state lives, relative to the repository root.
const SEEN_FILE: &str = ".frob/seen.toml";

/// The teach mode for `rule` at `root`: the `[ui] teach` knob, with the profile deciding how long
/// `first` keeps teaching in full from the rule's count in `.frob/seen.toml`. Unreadable config or
/// seen state is logged and treated as the defaults (`first`, count 0), never a failure.
pub fn teach_mode_at(root: &Path, profile: Profile, rule: &str) -> TeachMode {
    let knob = match gob_config::load::<gob_config::UiTable>(root, "frob") {
        Ok(loaded) => loaded.value.teach,
        Err(e) => {
            tracing::warn!(error = %e, "[ui] teach unreadable, using first");
            "first".to_owned()
        }
    };
    let mode = knob.parse::<TeachMode>().unwrap_or_else(|e| {
        tracing::warn!(error = %e, "[ui] teach invalid, using first");
        TeachMode::First
    });
    if mode != TeachMode::First {
        return mode;
    }
    let seen = SeenStore::load(&root.join(SEEN_FILE)).unwrap_or_else(|e| {
        tracing::warn!(error = %e, "seen state unreadable, counting from zero");
        SeenStore::default()
    });
    let count = usize::try_from(seen.count(rule)).unwrap_or(usize::MAX);
    match profile.teach_for(count) {
        Teach::Always => TeachMode::Always,
        Teach::First => TeachMode::First,
    }
}

/// The one-line next step after a successful verb, newcomers only; `None` when there is nothing to suggest.
pub fn next_step(verb: &str, data: &Value, ctx: &Context) -> Option<String> {
    if Profile::for_cwd(&ctx.cwd) != Profile::Newcomer {
        return None;
    }
    next_step_line(verb, data)
}

/// The profile-independent table behind [`next_step`].
fn next_step_line(verb: &str, data: &Value) -> Option<String> {
    let handle = |v: &Value| v.get("handle").and_then(Value::as_str).map(str::to_owned);
    match verb {
        "work" | "start" => handle(data).map(|h| format!("next: frob check --ticket {h}")),
        "ticket.doable" => data
            .get("tickets")
            .and_then(|t| t.get(0))
            .and_then(handle)
            .map(|h| format!("next: frob work {h}")),
        "ticket.close" => Some("next: frob ticket doable".to_owned()),
        _ => None,
    }
}

/// Help after a failed command, newcomers only: the three likely commands and the guide page.
pub fn failure_help(cwd: &Path) -> Option<String> {
    (Profile::for_cwd(cwd) == Profile::Newcomer).then(|| {
        format!(
            "help: likely next commands: frob ticket doable, frob work ~ID, frob check\nhelp: guide: {GUIDE_PAGE}"
        )
    })
}

/// The presenter the frob root registers.
pub const PRESENTER: Presenter = Presenter {
    next_step,
    failure_help,
};

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/profile.rs::Profile.teach_for
    #[test]
    fn newcomer_is_taught_five_times_then_first() {
        for n in 0..NEWCOMER_TEACH_OCCURRENCES {
            assert_eq!(Profile::Newcomer.teach_for(n), Teach::Always);
        }
        assert_eq!(
            Profile::Newcomer.teach_for(NEWCOMER_TEACH_OCCURRENCES),
            Teach::First
        );
        assert_eq!(Profile::Experienced.teach_for(0), Teach::First);
    }

    // frob:tests crates/frob/src/profile.rs::teach_mode_at
    #[test]
    fn teach_mode_comes_from_seen_toml_and_ui_teach() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let at = |p| teach_mode_at(root, p, "SYS003");
        assert_eq!(at(Profile::Newcomer), TeachMode::Always);
        assert_eq!(at(Profile::Experienced), TeachMode::First);
        let mut seen = SeenStore::default();
        for _ in 0..NEWCOMER_TEACH_OCCURRENCES {
            seen.disclose(TeachMode::First, "SYS003");
        }
        seen.save(&root.join(SEEN_FILE)).unwrap();
        assert_eq!(at(Profile::Newcomer), TeachMode::First);
        std::fs::write(root.join("frob.toml"), "[ui]\nteach = \"never\"\n").unwrap();
        assert_eq!(at(Profile::Newcomer), TeachMode::Never);
        std::fs::write(root.join("frob.toml"), "[ui]\nteach = \"always\"\n").unwrap();
        assert_eq!(at(Profile::Experienced), TeachMode::Always);
    }

    // frob:tests crates/frob/src/profile.rs::next_step
    #[test]
    fn work_and_doable_name_a_next_command() {
        let work = serde_json::json!({"handle": "~ABC"});
        assert_eq!(
            next_step_line("work", &work).as_deref(),
            Some("next: frob check --ticket ~ABC")
        );
        let doable = serde_json::json!({"tickets": [{"handle": "~XYZ"}]});
        assert_eq!(
            next_step_line("ticket.doable", &doable).as_deref(),
            Some("next: frob work ~XYZ")
        );
        assert_eq!(next_step_line("check", &work), None);
    }

    // frob:tests crates/frob/src/profile.rs::failure_help
    #[test]
    fn failure_help_is_newcomer_only() {
        let dir = tempfile::tempdir().unwrap();
        // Outside a repository the default profile is newcomer.
        let help = failure_help(dir.path()).unwrap();
        assert!(help.contains(GUIDE_PAGE));
        assert_eq!(help.matches("frob ").count(), 3);
    }

    /// Run `git` in `dir` through the runner and assert it exited 0.
    fn git(dir: &Path, args: &[&str]) {
        let spec = gob_exec::Spec {
            program: gob_exec::Program::Git,
            args: args.iter().map(|a| (*a).to_owned()).collect(),
            cwd: Some(dir.to_owned()),
            env: Vec::new(),
            timeout: std::time::Duration::from_secs(30),
            capture: true,
        };
        let out = gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
            .run(&spec)
            .expect("run git");
        assert!(
            matches!(out.status, gob_exec::Outcome::Exited(0)),
            "git {args:?}: {}",
            out.stderr
        );
    }

    fn repo() -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        for args in [
            vec!["init", "-q"],
            vec!["symbolic-ref", "HEAD", "refs/heads/main"],
            vec!["config", "user.name", "Test User"],
            vec!["config", "user.email", "test@example.com"],
        ] {
            git(dir.path(), &args);
        }
        let cli = crate::cli();
        let (code, out, err) = gob_cli::run_for_test(&cli, &["init"], dir.path());
        assert_eq!(code, 0, "{out} {err}");
        git(dir.path(), &["add", "-A"]);
        git(dir.path(), &["commit", "-q", "-m", "base"]);
        let (code, out, err) = gob_cli::run_for_test(
            &cli,
            &["ticket", "new", "--title", "One", "--type", "chore"],
            dir.path(),
        );
        assert_eq!(code, 0, "{out} {err}");
        dir
    }

    // frob:tests crates/frob/src/profile.rs::next_step
    // frob:tests crates/frob/src/profile.rs::failure_help
    #[test]
    fn newcomer_text_output_ends_with_next_and_experienced_does_not() {
        let dir = repo();
        let cli = crate::cli();
        let run = |args: &[&str]| gob_cli::run_for_test(&cli, args, dir.path());
        let (code, out, _) = run(&["ticket", "doable", "--text"]);
        assert_eq!(code, 0, "{out}");
        assert!(
            out.trim_end()
                .lines()
                .last()
                .unwrap()
                .starts_with("next: frob work "),
            "{out}"
        );
        let (_, out_json, _) = run(&["ticket", "doable", "--json"]);
        assert!(!out_json.contains("next:"));
        let (code, _, err) = run(&["bogus", "--text"]);
        assert_ne!(code, 0);
        assert!(err.contains(GUIDE_PAGE), "{err}");

        let (code, _, _) = run(&["profile", "experienced", "--json"]);
        assert_eq!(code, 0);
        let (_, out, _) = run(&["ticket", "doable", "--text"]);
        assert!(!out.contains("next:"), "{out}");
        let (_, _, err) = run(&["bogus", "--text"]);
        assert!(!err.contains(GUIDE_PAGE), "{err}");
    }

    // frob:tests crates/frob/src/profile.rs::next_step
    #[test]
    fn check_findings_and_exit_code_do_not_depend_on_the_profile() {
        let dir = repo();
        let cli = crate::cli();
        let run = |args: &[&str]| gob_cli::run_for_test(&cli, args, dir.path());
        let (c1, out1, _) = run(&["check", "--json"]);
        let (code, _, _) = run(&["profile", "experienced", "--json"]);
        assert_eq!(code, 0);
        let (c2, out2, _) = run(&["check", "--json"]);
        assert_eq!(c1, c2);
        let findings = |out: &str| serde_json::from_str::<Value>(out).unwrap()["findings"].clone();
        assert_eq!(findings(&out1), findings(&out2));
    }
}

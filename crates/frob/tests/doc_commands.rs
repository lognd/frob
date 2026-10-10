//! Doc tests for the README and the guides: every `sh` block runs in a fresh repository, every link resolves.
// frob:ticket 01M4CTTQFF84AWJZKH89X572Y1
#![cfg(unix)]

use std::path::{Path, PathBuf};
use std::process::Command;

/// The repository root (two levels above this crate).
fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The `sh` fenced blocks of a markdown file, joined; a block tagged `sh no-run` (or any other tag) is skipped.
fn sh_blocks(markdown: &str) -> String {
    let mut out = String::new();
    let mut inside = false;
    for line in markdown.lines() {
        if inside {
            if line.trim() == "```" {
                inside = false;
            } else {
                out.push_str(line);
                out.push('\n');
            }
        } else if line.trim() == "```sh" {
            inside = true;
        }
    }
    out
}

/// The UTC day `days` from now as `YYYY-MM-DD`, the zone `frob cycle` derives states from.
fn rel(days: i64) -> String {
    gob_time::Clock::today(&gob_time::SystemClock)
        .plus_days(days)
        .expect("in range")
        .to_string()
}

/// Rewrite a guide script for execution: current dates for the cycle, the ticket handle captured from `ticket new`.
fn prepare(script: &str) -> String {
    let joined = script
        .replace("\\\n", "")
        .replace("2026-10-08", &rel(0))
        .replace("2026-10-15", &rel(7));
    let capture = r#" --json | sed -n 's/.*"handle":"\(~[0-9A-Z]*\)".*/\1/p' | head -1)"#;
    let lines: Vec<String> = joined
        .lines()
        .map(|l| {
            if l.starts_with("frob ticket new") {
                format!("H=$({l}{capture}")
            } else {
                l.to_owned()
            }
        })
        .collect();
    lines
        .join("\n")
        .replace("~Q5FEE2P", "\"$H\"")
        .replace("Q5FEE2P", "${H#\\~}")
}

/// Directory holding the product binaries under test.
fn bin_dir() -> PathBuf {
    let frob = assert_cmd::Command::cargo_bin("frob").expect("frob binary");
    Path::new(frob.get_program())
        .parent()
        .expect("bin dir")
        .to_path_buf()
}

/// Run `script` with `sh -ex` in `cwd`, products first on `PATH` and a fixed git identity; panics with the transcript on failure.
fn run_script(script: &str, cwd: &Path, git_config: &Path) {
    let mut path = vec![bin_dir()];
    path.extend(std::env::split_paths(
        &std::env::var_os("PATH").unwrap_or_default(),
    ));
    let mut cmd = Command::new("sh");
    cmd.args(["-ex", "-c", script])
        .current_dir(cwd)
        .env("PATH", std::env::join_paths(path).expect("PATH"))
        .env("GIT_CONFIG_GLOBAL", git_config)
        .env_remove("FROB_LOG");
    for (k, _) in std::env::vars() {
        if k.starts_with("NEXTEST") || k == "CARGO_TARGET_DIR" {
            cmd.env_remove(k);
        }
    }
    let out = cmd.output().expect("run sh");
    assert!(
        out.status.success(),
        "doc script failed ({:?})\n--- script\n{script}\n--- stderr\n{}\n--- stdout\n{}",
        out.status,
        String::from_utf8_lossy(&out.stderr),
        String::from_utf8_lossy(&out.stdout)
    );
}

/// A temp directory holding a git identity file and an empty work area.
fn sandbox() -> (tempfile::TempDir, PathBuf, PathBuf) {
    let tmp = tempfile::tempdir().expect("tempdir");
    let config = tmp.path().join("gitconfig");
    std::fs::write(
        &config,
        "[user]\n\tname = Doc Test\n\temail = doc@example.com\n[init]\n\tdefaultBranch = main\n",
    )
    .expect("write gitconfig");
    let work = tmp.path().join("work");
    std::fs::create_dir(&work).expect("mkdir");
    (tmp, config, work)
}

/// Every command in the README runs successfully in a fresh git repository with one commit.
#[test]
fn readme_commands_succeed_in_a_fresh_repository() {
    let readme = std::fs::read_to_string(repo_root().join("README.md")).expect("README");
    let mut script = prepare(&sh_blocks(&readme));
    assert!(script.contains("frob init"), "README shows frob init");
    for sibling in ["grimble", "crunk"] {
        if !bin_dir().join(sibling).exists() {
            assert!(
                std::env::var_os("CI").is_none(),
                "{sibling} must be built in CI"
            );
            // A local `-p frob-cli` run does not build the siblings.
            script = script
                .lines()
                .filter(|l| !l.starts_with(sibling))
                .collect::<Vec<_>>()
                .join("\n");
        }
    }
    let (_tmp, config, work) = sandbox();
    let setup = "git init -q -b main && mkdir src && echo '// seed' > src/lib.rs && git add -A && git commit -q -m seed\n";
    run_script(&format!("{setup}{script}"), &work, &config);
}

/// The quickstart runs end to end, init to land, in a fresh temp repository.
#[test]
fn quickstart_runs_from_init_to_land() {
    let text =
        std::fs::read_to_string(repo_root().join("docs/guides/quickstart.md")).expect("quickstart");
    let script = prepare(&sh_blocks(&text));
    assert!(script.contains("frob land"), "quickstart reaches land");
    let (_tmp, config, work) = sandbox();
    run_script(&script, &work, &config);
}

/// The ticket-branch guide runs end to end: the ledger lands on `frob-tickets` and the worktree comes from the code branch.
// frob:ticket 01M4CTTSAZC93K94KNXH3WVSYM
#[test]
fn ticket_branch_guide_runs_in_a_fresh_repository() {
    let text = std::fs::read_to_string(repo_root().join("docs/guides/ticket-branch.md"))
        .expect("ticket-branch guide");
    let script = prepare(&sh_blocks(&text));
    assert!(
        script.contains("ticket branch init"),
        "guide creates the branch"
    );
    let (_tmp, config, work) = sandbox();
    run_script(&script, &work, &config);
}

/// GitHub-style slug of a heading.
fn slug(heading: &str) -> String {
    heading
        .trim()
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == ' ' || *c == '-')
        .map(|c| if c == ' ' { '-' } else { c })
        .collect()
}

/// Markdown link targets `](target)` in `text`.
fn link_targets(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    for line in text.lines() {
        let mut rest = line;
        while let Some(i) = rest.find("](") {
            rest = &rest[i + 2..];
            if let Some(j) = rest.find(')') {
                out.push(rest[..j].to_owned());
                rest = &rest[j..];
            }
        }
    }
    out
}

/// Every relative link (and `#anchor`) in the README and the guides points at something that exists.
#[test]
fn every_readme_and_guide_link_resolves() {
    let root = repo_root();
    let mut files = vec![root.join("README.md")];
    for entry in std::fs::read_dir(root.join("docs/guides")).expect("guides") {
        let path = entry.expect("entry").path();
        if path.extension().is_some_and(|e| e == "md") {
            files.push(path);
        }
    }
    let mut broken = Vec::new();
    for file in &files {
        let text = std::fs::read_to_string(file).expect("read");
        for target in link_targets(&text) {
            if target.contains("://") || target.starts_with("mailto:") {
                continue;
            }
            let (path_part, anchor) = match target.split_once('#') {
                Some((p, a)) => (p, Some(a)),
                None => (target.as_str(), None),
            };
            let dest = if path_part.is_empty() {
                file.clone()
            } else {
                file.parent().expect("parent").join(path_part)
            };
            if !dest.exists() {
                broken.push(format!("{}: {target}", file.display()));
                continue;
            }
            if let (Some(anchor), true) = (anchor, dest.is_file()) {
                let body = std::fs::read_to_string(&dest).expect("read target");
                let found = body
                    .lines()
                    .filter_map(|l| l.strip_prefix('#'))
                    .any(|h| slug(h.trim_start_matches('#')) == anchor);
                if !found {
                    broken.push(format!("{}: {target} (no such heading)", file.display()));
                }
            }
        }
    }
    assert!(broken.is_empty(), "broken links:\n{}", broken.join("\n"));
}

//! Leaf-command discovery: walk the clap tree of each built binary through its own `--help`.
//!
//! The binaries are the thing being profiled, so their help output is the one source that cannot
//! drift from them, and reading it needs no dependency on the product crates (linking them into
//! gob-dev would add their verbs to the generated CLI reference).

use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Runner, Spec};

use super::ProfileError;

/// Wall-clock limit for one `--help` call.
const HELP_TIMEOUT: Duration = Duration::from_secs(30);

/// Subcommand names listed under the `Commands:` heading of clap help text, without `help`.
pub fn parse_commands(help: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut in_commands = false;
    for line in help.lines() {
        if line.trim_end() == "Commands:" {
            in_commands = true;
            continue;
        }
        if !in_commands {
            continue;
        }
        if line.trim().is_empty() || !line.starts_with(' ') {
            break;
        }
        // Continuation lines of a wrapped description are indented deeper than the names.
        let indent = line.len() - line.trim_start().len();
        if indent > 2 {
            continue;
        }
        if let Some(name) = line.split_whitespace().next()
            && name != "help"
        {
            out.push(name.to_owned());
        }
    }
    out
}

/// Every leaf verb path of `exe` (words joined by one space), found by walking `--help`.
///
/// # Errors
/// [`ProfileError::Spawn`] when a help call cannot run or exits non-zero.
pub fn leaves(runner: &Runner, product: &str, exe: &Path) -> Result<Vec<String>, ProfileError> {
    let mut leaves = Vec::new();
    let mut pending: Vec<Vec<String>> = vec![Vec::new()];
    while let Some(path) = pending.pop() {
        let mut args = path.clone();
        args.push("--help".to_owned());
        let out = runner
            .run(&Spec {
                program: Program::Hook {
                    path: exe.to_path_buf(),
                },
                args,
                cwd: None,
                env: Vec::new(),
                timeout: HELP_TIMEOUT,
                capture: true,
            })
            .map_err(|e| ProfileError::Spawn(format!("{product} {path:?} --help: {e}")))?;
        if out.status != Outcome::Exited(0) {
            return Err(ProfileError::Spawn(format!(
                "{product} {} --help ended {:?}",
                path.join(" "),
                out.status
            )));
        }
        let subs = parse_commands(&out.stdout);
        if subs.is_empty() {
            if !path.is_empty() {
                leaves.push(path.join(" "));
            }
            continue;
        }
        for sub in subs {
            let mut next = path.clone();
            next.push(sub);
            pending.push(next);
        }
    }
    leaves.sort();
    tracing::info!(product, leaves = leaves.len(), "leaf commands discovered");
    Ok(leaves)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/profile/discover.rs::parse_commands
    #[test]
    fn reads_the_commands_section_only() {
        let help = "Usage: frob [OPTIONS] <COMMAND>\n\nCommands:\n  ack      Acknowledge a drift\n  ticket   Ticket verbs that\n           wrap over two lines\n  help     Print this message\n\nOptions:\n  -h, --help  Print help\n";
        assert_eq!(parse_commands(help), vec!["ack", "ticket"]);
        assert!(parse_commands("Usage: frob check\n\nOptions:\n  --json\n").is_empty());
    }

    // frob:tests crates/gob-dev/src/profile/discover.rs::leaves
    #[cfg(unix)]
    #[test]
    fn walks_the_help_tree_down_to_its_leaves() {
        use std::os::unix::fs::PermissionsExt as _;
        let tmp = tempfile::tempdir().unwrap();
        let exe = tmp.path().join("fake");
        let script = "#!/bin/sh\ncase \"$*\" in\n\
            '--help') printf 'Commands:\\n  ticket  Tickets\\n  check   Check\\n  help    Help\\n';;\n\
            'ticket --help') printf 'Commands:\\n  show  Show\\n  new   New\\n';;\n\
            *) printf 'Usage: leaf\\n';;\nesac\n";
        std::fs::write(&exe, script).unwrap();
        std::fs::set_permissions(&exe, std::fs::Permissions::from_mode(0o755)).unwrap();
        let runner = Runner::new(gob_exec::Limits { jobs: 1 });
        let found = leaves(&runner, "fake", &exe).unwrap();
        assert_eq!(found, ["check", "ticket new", "ticket show"]);
    }
}

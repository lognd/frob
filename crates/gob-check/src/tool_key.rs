//! The identity of a `TOOL001` stage failure: stage plus exit class, never the tool's output text.
//!
//! A failing tool prints timings, orderings and counts that differ run to run, so a fingerprint
//! over the raw message makes a stage already red on the base look NEW on every land. The key
//! keeps only what says *how* the stage failed (`exited 1`, `timed out`, `was terminated by a
//! signal`, ...) and drops the command line, the output excerpt and any parenthesised detail.

use std::fmt::Write as _;

/// The stable key of a `TOOL001` stage-failure `message`; `None` when it is not a stage failure message.
pub(crate) fn tool_failure_key(message: &str) -> Option<String> {
    let rest = message.strip_prefix("tool stage `")?;
    let (stage, rest) = rest.split_once('`')?;
    let rest = rest.trim_start();
    let rest = match rest.strip_prefix('(') {
        Some(after) => skip_parens(after)?.trim_start(),
        None => rest,
    };
    let head = rest.split_once(':').map_or(rest, |(h, _)| h);
    let class = class_of(head);
    tracing::debug!(stage, %class, "tool failure keyed by stage and exit class");
    Some(format!("tool-stage:{stage}:{class}"))
}

/// `after` is the text following an opening paren; return what follows its matching close.
fn skip_parens(after: &str) -> Option<&str> {
    let mut depth = 1usize;
    for (i, c) in after.char_indices() {
        match c {
            '(' => depth += 1,
            ')' => {
                depth -= 1;
                if depth == 0 {
                    return Some(&after[i + 1..]);
                }
            }
            _ => {}
        }
    }
    None
}

/// The failure class: `head` with parenthesised detail and trailing digits of durations dropped.
fn class_of(head: &str) -> String {
    let mut out = String::new();
    let mut depth = 0usize;
    for c in head.chars() {
        match c {
            '(' => depth += 1,
            ')' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(c),
            _ => {}
        }
    }
    // "timed out after 60s": the configured timeout is not part of the class.
    if let Some(i) = out.find("timed out") {
        out.truncate(i);
        let _ = write!(out, "timed out");
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-check/src/tool_key.rs::tool_failure_key
    #[test]
    fn differently_worded_output_keys_alike() {
        let a = "tool stage `vitest` (npx vitest run) exited 1: 3 failed in 12.1s";
        let b = "tool stage `vitest` (npx vitest run) exited 1: 4 failed in 9.8s, other order";
        assert_eq!(tool_failure_key(a), tool_failure_key(b));
        assert_eq!(
            tool_failure_key(a).as_deref(),
            Some("tool-stage:vitest:exited 1")
        );
    }

    // frob:tests crates/gob-check/src/tool_key.rs::tool_failure_key
    #[test]
    fn exit_class_and_stage_distinguish() {
        let one = tool_failure_key("tool stage `a` (c) exited 1: x");
        assert_ne!(one, tool_failure_key("tool stage `a` (c) exited 2: x"));
        assert_ne!(one, tool_failure_key("tool stage `b` (c) exited 1: x"));
        assert_eq!(
            tool_failure_key("tool stage `a` (c) timed out after 60s").as_deref(),
            Some("tool-stage:a:timed out")
        );
    }

    // frob:tests crates/gob-check/src/tool_key.rs::tool_failure_key
    #[test]
    fn failure_message_drops_error_detail_and_command() {
        let m = "tool stage `l` printed output its parser cannot read (bad json at 3): command `x --y`; status: 0; stderr: z";
        assert_eq!(
            tool_failure_key(m).as_deref(),
            Some("tool-stage:l:printed output its parser cannot read")
        );
        assert_eq!(tool_failure_key("something else"), None);
    }
}

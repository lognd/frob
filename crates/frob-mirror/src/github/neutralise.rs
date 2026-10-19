//! Neutralise GitHub side effects in mirrored text (mirror.md 3.6, MIR-AUD-21, 23).
//!
//! Mentions (`@user`, `@org/team`), issue and pull request references (`#12`), cross-repository
//! references (`owner/repo#5`) and closing-keyword phrases (`fixes #12`) are wrapped in code spans,
//! where GitHub neither notifies, links nor closes. Task-list lines (`- [ ] x`) become plain list
//! text. Text already inside code spans or fenced blocks is left untouched. The function is pure
//! and idempotent.

// frob:ticket 01M4052TZJMWSQJGXQN6ZR4N2C

use tracing::debug;

/// Keywords GitHub treats as issue-closing when followed by a reference.
const CLOSING_KEYWORDS: [&str; 9] = [
    "close", "closes", "closed", "fix", "fixes", "fixed", "resolve", "resolves", "resolved",
];

/// True for characters allowed in a user, organisation or repository name.
fn is_name(c: char) -> bool {
    c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.')
}

/// True when position `i` is not glued to a preceding word character.
fn at_boundary(chars: &[char], i: usize) -> bool {
    i == 0 || !(chars[i - 1].is_ascii_alphanumeric() || matches!(chars[i - 1], '_' | '/'))
}

/// End of the run of name characters starting at `i`.
fn name_end(chars: &[char], mut i: usize) -> usize {
    while i < chars.len() && is_name(chars[i]) {
        i += 1;
    }
    i
}

/// Length of an issue reference (`#12` or `owner/repo#12`) at `i`, if one starts there.
fn reference_len(chars: &[char], i: usize) -> Option<usize> {
    let hash = if chars.get(i) == Some(&'#') {
        i
    } else {
        let slash = name_end(chars, i);
        if slash == i || chars.get(slash) != Some(&'/') {
            return None;
        }
        let hash = name_end(chars, slash + 1);
        if hash == slash + 1 || chars.get(hash) != Some(&'#') {
            return None;
        }
        hash
    };
    let mut end = hash + 1;
    while end < chars.len() && chars[end].is_ascii_digit() {
        end += 1;
    }
    (end > hash + 1).then_some(end - i)
}

/// Length of a closing-keyword phrase (`fixes #12`, `Closes: o/r#3`) at `i`, if one starts there.
fn closing_len(chars: &[char], i: usize) -> Option<usize> {
    let word_end = (i..chars.len())
        .find(|&k| !chars[k].is_ascii_alphabetic())
        .unwrap_or(chars.len());
    let word: String = chars[i..word_end]
        .iter()
        .collect::<String>()
        .to_ascii_lowercase();
    if !CLOSING_KEYWORDS.contains(&word.as_str()) {
        return None;
    }
    let mut k = word_end;
    if chars.get(k) == Some(&':') {
        k += 1;
    }
    let spaces = k;
    while chars.get(k) == Some(&' ') {
        k += 1;
    }
    if k == spaces {
        return None;
    }
    reference_len(chars, k).map(|n| k + n - i)
}

/// Length of a mention (`@user` or `@org/team`) at `i`, if one starts there.
fn mention_len(chars: &[char], i: usize) -> Option<usize> {
    if chars.get(i) != Some(&'@') {
        return None;
    }
    let first = name_end(chars, i + 1);
    if first == i + 1 {
        return None;
    }
    if chars.get(first) == Some(&'/') {
        let second = name_end(chars, first + 1);
        if second > first + 1 {
            return Some(second - i);
        }
    }
    Some(first - i)
}

/// Wrap every side-effect token of a code-span-free segment in a code span.
fn wrap_tokens(seg: &str, out: &mut String) {
    let chars: Vec<char> = seg.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        let hit = if at_boundary(&chars, i) {
            closing_len(&chars, i)
                .or_else(|| reference_len(&chars, i))
                .or_else(|| mention_len(&chars, i))
        } else {
            None
        };
        if let Some(n) = hit {
            out.push('`');
            out.extend(&chars[i..i + n]);
            out.push('`');
            i += n;
        } else {
            out.push(chars[i]);
            i += 1;
        }
    }
}

/// Length of the backtick run starting at byte `i` of `s`.
fn tick_run(s: &str, i: usize) -> usize {
    s[i..].bytes().take_while(|&b| b == b'`').count()
}

/// Neutralise one prose line, leaving existing code spans verbatim.
fn neutralise_line(line: &str, out: &mut String) {
    let mut plain_from = 0;
    let mut i = 0;
    while i < line.len() {
        if line.as_bytes()[i] != b'`' {
            i += 1;
            continue;
        }
        let n = tick_run(line, i);
        // Find a closing run of exactly the same length.
        let mut j = i + n;
        let mut close = None;
        while j < line.len() {
            if line.as_bytes()[j] == b'`' {
                let m = tick_run(line, j);
                if m == n {
                    close = Some(j + m);
                    break;
                }
                j += m;
            } else {
                j += 1;
            }
        }
        match close {
            Some(end) => {
                wrap_tokens(&line[plain_from..i], out);
                out.push_str(&line[i..end]);
                plain_from = end;
                i = end;
            }
            None => i += n,
        }
    }
    wrap_tokens(&line[plain_from..], out);
}

/// Split a leading checkbox off `rest`, returning its plain-text label and the remaining text.
fn checkbox(rest: &str) -> Option<(&'static str, &str)> {
    if let Some(t) = rest.strip_prefix("[ ]") {
        return Some(("Unbound", t));
    }
    let t = rest
        .strip_prefix("[x]")
        .or_else(|| rest.strip_prefix("[X]"))?;
    Some(("Bound", t))
}

/// Rewrite a task-list line (`- [ ] x`, `1. [x] y`) as plain list text, or return it unchanged.
fn defang_task(line: &str) -> Option<String> {
    let body = line.trim_start();
    let indent = &line[..line.len() - body.len()];
    let after_marker = if let Some(r) = body.strip_prefix(['-', '*', '+']) {
        (&body[..1], r)
    } else {
        let digits = body.bytes().take_while(u8::is_ascii_digit).count();
        match body[digits..].chars().next() {
            Some('.' | ')') if digits > 0 => body.split_at(digits + 1),
            _ => return None,
        }
    };
    let (marker, rest) = after_marker;
    let rest = rest.trim_start_matches(' ');
    let (label, text) = checkbox(rest)?;
    if !(text.is_empty() || text.starts_with(' ')) {
        return None;
    }
    Some(format!("{indent}{marker} {label}:{text}"))
}

/// Neutralise `text` so it cannot mention, close, link or tick anything on GitHub.
pub fn neutralise(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 16);
    let mut fence: Option<char> = None;
    for line in text.split_inclusive('\n') {
        let (content, eol) = match line.strip_suffix('\n') {
            Some(c) => (c, "\n"),
            None => (line, ""),
        };
        let trimmed = content.trim_start();
        let opener = ['`', '~']
            .into_iter()
            .find(|&c| trimmed.starts_with(&c.to_string().repeat(3)));
        match (fence, opener) {
            (Some(f), Some(o)) if f == o => fence = None,
            (None, Some(o)) => fence = Some(o),
            _ => {}
        }
        if fence.is_some() || opener.is_some() {
            out.push_str(content);
        } else if let Some(t) = defang_task(content) {
            neutralise_line(&t, &mut out);
        } else {
            neutralise_line(content, &mut out);
        }
        out.push_str(eol);
    }
    debug!(
        before = text.len(),
        after = out.len(),
        "github: neutralised text"
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests neutralise
    #[test]
    fn mentions_and_team_mentions_are_code_spans() {
        let r = neutralise("ping @alice and @org/team-x now");
        assert_eq!(r, "ping `@alice` and `@org/team-x` now");
        assert!(
            !r.replace("`@alice`", "")
                .replace("`@org/team-x`", "")
                .contains('@')
        );
    }

    // frob:tests neutralise
    #[test]
    fn email_addresses_are_not_mentions() {
        assert_eq!(neutralise("mail a@b.example"), "mail a@b.example");
    }

    // frob:tests neutralise
    #[test]
    fn closing_keywords_and_cross_repo_refs_are_plain_text() {
        assert_eq!(neutralise("fixes #12"), "`fixes #12`");
        assert_eq!(neutralise("Closes: o/r#3 done"), "`Closes: o/r#3` done");
        assert_eq!(neutralise("see owner/repo#5."), "see `owner/repo#5`.");
        assert_eq!(neutralise("also #7"), "also `#7`");
        assert_eq!(neutralise("fix the bug"), "fix the bug");
    }

    // frob:tests neutralise
    #[test]
    fn task_list_lines_lose_their_checkbox() {
        let r = neutralise("- [ ] item\n  * [x] done\n1. [X] num\n- [ ]\n- [a] keep\n");
        assert_eq!(
            r,
            "- Unbound: item\n  * Bound: done\n1. Bound: num\n- Unbound:\n- [a] keep\n"
        );
        assert!(!r.contains("[ ]") && !r.contains("[x]"));
    }

    // frob:tests neutralise
    #[test]
    fn code_spans_and_fences_are_left_alone_and_output_is_idempotent() {
        let src = "a `@x #1` b @y\n```\n@z fixes #2\n- [ ] k\n```\nend #3";
        let once = neutralise(src);
        assert_eq!(
            once,
            "a `@x #1` b `@y`\n```\n@z fixes #2\n- [ ] k\n```\nend `#3`"
        );
        assert_eq!(neutralise(&once), once);
    }
}

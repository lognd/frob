//! CI012 verb join: the `frob` verbs a workflow's `run:` scripts invoke against the verbs frob has.
//!
//! The inventory is a static table here rather than a read of the CLI definition: the verb tree
//! lives in `frob-cli` (layer 17) and `grimble-ci` (layer 11) may not depend upward, so the table
//! is copied and a drift test belongs next to the CLI. The scan is lexical, not a shell parser:
//! it finds simple commands (split on `|`, `&`, `;`, parentheses and backquotes), skips comments,
//! heredoc bodies, `NAME=value` prefixes and wrappers, and reads the verb path of every command
//! whose word is `frob`. Anything it cannot know (an expression or variable in the verb) is not
//! judged.

// frob:ticket 01M5F010Y998BXB67KPZ4T040N

/// Top-level `frob` verbs and their subcommands (empty for a leaf verb), deprecated aliases included.
pub const VERBS: &[(&str, &[&str])] = &[
    ("schema", &[]),
    ("serve", &[]),
    ("check", &[]),
    ("doctor", &[]),
    ("init", &[]),
    ("config", &["show", "sync"]),
    ("agent", &["sync", "status", "uninstall"]),
    ("lease", &["widen", "release", "rekind", "list"]),
    ("claim", &["touch", "restore", "evict", "hold", "resume"]),
    ("board", &[]),
    (
        "ticket",
        &[
            "new",
            "update",
            "link",
            "unlink",
            "comment",
            "close",
            "closeout",
            "drop",
            "reopen",
            "show",
            "list",
            "doable",
            "triage",
            "proposals",
            "fragment",
            "branch",
            "migrate",
            "reindex",
            "url",
            "doctor",
            "evidence",
            "brief",
            "contention",
        ],
    ),
    (
        "milestone",
        &["criterion", "evidence", "new", "add", "show", "list"],
    ),
    (
        "cycle",
        &[
            "new", "show", "list", "close", "assign", "unassign", "plan", "velocity",
        ],
    ),
    ("stats", &[]),
    ("refresh", &[]),
    ("mirror", &["render", "recreate"]),
    ("profile", &[]),
    ("tour", &[]),
    ("trust", &[]),
    ("teach", &[]),
    (
        "release",
        &["changelog", "notes", "status", "bump", "cut", "adopt"],
    ),
    ("rule", &["test", "check", "catalog", "fmt", "new"]),
    ("explain", &[]),
    ("work", &[]),
    ("requeue", &[]),
    ("test", &[]),
    ("ack", &[]),
    ("graph", &["why", "affects"]),
    ("land", &[]),
    ("train", &["status", "run", "drain", "drop"]),
    ("start", &[]),
    ("merge-driver", &[]),
    ("help", &[]),
];

/// Global options that take the next word as their value.
const VALUE_FLAGS: [&str; 3] = ["--format", "--cwd", "--color"];

/// Words that prefix a command without being it (shell keywords and transparent wrappers).
const PREFIXES: [&str; 14] = [
    "if", "then", "elif", "else", "do", "while", "until", "!", "{", "time", "exec", "sudo", "env",
    "command",
];

/// Prefix words whose own flags (`sudo -E`, `command -p`) are skipped too.
const WRAPPERS: [&str; 5] = ["time", "exec", "sudo", "env", "command"];

/// A `frob` invocation whose verb path is not in the inventory.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct UnknownVerb {
    /// The verb path as written (`ticket foo`, `frobnicate`).
    pub path: String,
    /// The word that is wrong (`foo`, `frobnicate`).
    pub word: String,
    /// What would have been valid at that position, comma-joined and backquoted.
    pub valid: String,
}

/// Every `frob` verb path in `script` that frob does not have.
pub(crate) fn unknown_verbs(script: &str) -> Vec<UnknownVerb> {
    let mut out = Vec::new();
    for words in commands(script) {
        if let Some(bad) = judge(&words)
            && !out.contains(&bad)
        {
            tracing::debug!(path = bad.path, "CI012 unknown frob verb");
            out.push(bad);
        }
    }
    out
}

/// The verdict on one simple command, `None` when it is not `frob`, is fine or cannot be judged.
fn judge(words: &[String]) -> Option<UnknownVerb> {
    let mut it = words.iter().map(String::as_str).peekable();
    while let Some(w) = it.peek().copied() {
        if is_assignment(w) {
            it.next();
        } else if PREFIXES.contains(&w) {
            it.next();
            if WRAPPERS.contains(&w) {
                while it.next_if(|n| n.starts_with('-')).is_some() {}
            }
        } else {
            break;
        }
    }
    let program = it.next()?;
    if program != "frob" && !program.ends_with("/frob") {
        return None;
    }
    let mut positionals: Vec<&str> = Vec::new();
    let mut flag_between = false;
    while let Some(w) = it.next() {
        if matches!(w, "--help" | "-h" | "--version" | "-V") {
            return None;
        }
        if VALUE_FLAGS.contains(&w) {
            it.next();
            flag_between |= !positionals.is_empty();
        } else if w.starts_with('-') {
            flag_between |= !positionals.is_empty();
        } else if positionals.len() < 2 && !flag_between {
            positionals.push(w);
        }
        if positionals.len() == 2 {
            break;
        }
    }
    let verb = *positionals.first()?;
    if verb.contains('$') {
        return None;
    }
    let Some((_, subs)) = VERBS.iter().find(|(v, _)| *v == verb) else {
        let valid = VERBS.iter().map(|(v, _)| *v).collect::<Vec<_>>();
        return Some(UnknownVerb {
            path: verb.to_owned(),
            word: verb.to_owned(),
            valid: names(&valid),
        });
    };
    let sub = *positionals.get(1)?;
    if subs.is_empty() || sub.contains('$') || sub == "help" || subs.contains(&sub) {
        return None;
    }
    Some(UnknownVerb {
        path: format!("{verb} {sub}"),
        word: sub.to_owned(),
        valid: names(subs),
    })
}

/// Comma-joined, backquoted names.
fn names(list: &[&str]) -> String {
    list.iter()
        .map(|n| format!("`{n}`"))
        .collect::<Vec<_>>()
        .join(", ")
}

/// True for a `NAME=value` word (a leading environment assignment).
fn is_assignment(w: &str) -> bool {
    let Some((name, _)) = w.split_once('=') else {
        return false;
    };
    name.starts_with(|c: char| c.is_ascii_alphabetic() || c == '_')
        && name.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
}

/// The shell line-continuation marker.
const CONTINUATION: char = 0x5c_u8 as char;

/// The simple commands of a script as word lists: continuations joined, heredoc bodies and
/// comments dropped, quotes removed.
fn commands(script: &str) -> Vec<Vec<String>> {
    let joined = script
        .replace(&format!("{CONTINUATION}\r\n"), "")
        .replace(&format!("{CONTINUATION}\n"), "");
    let mut out = Vec::new();
    let mut heredoc: Option<String> = None;
    for line in joined.lines() {
        if let Some(delim) = &heredoc {
            if line.trim() == delim {
                heredoc = None;
            }
            continue;
        }
        out.extend(split_line(line));
        heredoc = heredoc_delimiter(line);
    }
    out
}

/// The delimiter of a `<<EOF` / `<<-'EOF'` heredoc opened on `line`.
fn heredoc_delimiter(line: &str) -> Option<String> {
    let bytes = line.as_bytes();
    for (at, _) in line.match_indices("<<") {
        if at > 0 && bytes[at - 1] == b'<' || bytes.get(at + 2) == Some(&b'<') {
            continue;
        }
        let rest = line[at + 2..].trim_start_matches('-').trim_start();
        let rest = rest.trim_start_matches(['\'', '"']);
        let delim: String = rest
            .chars()
            .take_while(|c| c.is_ascii_alphanumeric() || *c == '_')
            .collect();
        if !delim.is_empty() {
            return Some(delim);
        }
    }
    None
}

/// Split one logical line into simple commands.
fn split_line(line: &str) -> Vec<Vec<String>> {
    let chars: Vec<char> = line.chars().collect();
    let mut out: Vec<Vec<String>> = Vec::new();
    let mut words: Vec<String> = Vec::new();
    let mut cur: Option<String> = None;
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        let peek = |n: usize| chars.get(i + n).copied();
        match c {
            '\'' => {
                let end = chars[i + 1..].iter().position(|x| *x == '\'');
                let stop = end.map_or(chars.len(), |e| i + 1 + e);
                cur.get_or_insert_with(String::new)
                    .extend(&chars[i + 1..stop]);
                i = stop;
            }
            '"' => {
                let w = cur.get_or_insert_with(String::new);
                i += 1;
                while i < chars.len() && chars[i] != '"' {
                    if chars[i] == '\\' && i + 1 < chars.len() {
                        i += 1;
                    }
                    w.push(chars[i]);
                    i += 1;
                }
            }
            '\\' => {
                if let Some(n) = peek(1) {
                    cur.get_or_insert_with(String::new).push(n);
                    i += 1;
                }
            }
            '$' if peek(1) == Some('{') => {
                let close = if peek(2) == Some('{') { "}}" } else { "}" };
                let tail: String = chars[i..].iter().collect();
                let len = tail.find(close).map_or(tail.len(), |p| p + close.len());
                let take = tail[..len].chars().count();
                cur.get_or_insert_with(String::new).push_str(&tail[..len]);
                i += take - 1;
            }
            '#' if cur.is_none() => break,
            c if c.is_whitespace() => flush(&mut cur, &mut words),
            '|' | '&' | ';' | '(' | ')' | '`' => {
                flush(&mut cur, &mut words);
                if !words.is_empty() {
                    out.push(std::mem::take(&mut words));
                }
            }
            c => cur.get_or_insert_with(String::new).push(c),
        }
        i += 1;
    }
    flush(&mut cur, &mut words);
    if !words.is_empty() {
        out.push(words);
    }
    out
}

/// Move the word in progress, if any, onto `words`.
fn flush(cur: &mut Option<String>, words: &mut Vec<String>) {
    if let Some(w) = cur.take() {
        words.push(w);
    }
}

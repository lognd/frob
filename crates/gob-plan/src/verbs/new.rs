//! `rule new`: scaffold a rule file from the code at `FILE:LINE` (grl-spec.md sections 2 and 11).

// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W

/// Why a rule could not be scaffolded.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum NewError {
    /// The id is not letters followed by three digits, such as `NOPE001`.
    #[error("rule id `{0}` must be uppercase letters then three digits, such as NOPE001")]
    BadId(String),
    /// The location is not `FILE:LINE` with a positive line.
    #[error("`{0}` is not FILE:LINE")]
    BadLocation(String),
    /// The file extension names no language the scaffolder knows.
    #[error("cannot tell the language of `{0}`; supported extensions are rs, py, ts, tsx and cs")]
    UnknownLanguage(String),
    /// The line is past the end of the file.
    #[error("line {line} is past the end of the file ({lines} lines)")]
    NoSuchLine {
        /// The requested line.
        line: usize,
        /// Lines in the file.
        lines: usize,
    },
    /// The line is blank, a lone brace, or holds a triple quote the example block cannot carry.
    #[error("line {0} holds no code to build a rule from")]
    NoCode(usize),
}

/// A scaffolded rule file.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct NewRule {
    /// Where to write it, relative to the project: `rules/ID.grl`.
    pub path: String,
    /// The file text.
    pub text: String,
    /// The code the rule was built from, trimmed.
    pub from: String,
    /// The snippet the rule looks for.
    pub snippet: String,
}

/// Split `FILE:LINE` at the last colon.
///
/// # Errors
///
/// [`NewError::BadLocation`] when there is no colon, the file is empty or the line is not a
/// positive number.
pub fn parse_location(loc: &str) -> Result<(&str, usize), NewError> {
    let bad = || NewError::BadLocation(loc.to_owned());
    let (file, line) = loc.rsplit_once(':').ok_or_else(bad)?;
    match line.parse::<usize>() {
        Ok(n) if n > 0 && !file.is_empty() => Ok((file, n)),
        _ => Err(bad()),
    }
}

/// The GRL language id and example-marker introducer for a file name.
fn language(file: &str) -> Result<(&'static str, &'static str), NewError> {
    match file.rsplit_once('.').map(|(_, e)| e) {
        Some("rs") => Ok(("rust", "//~")),
        Some("py") => Ok(("python", "#~")),
        Some("ts" | "tsx") => Ok(("typescript", "//~")),
        Some("cs") => Ok(("csharp", "//~")),
        _ => Err(NewError::UnknownLanguage(file.to_owned())),
    }
}

/// The first call on the line as `(name, text of the whole call)`; the name may end in `!`.
fn first_call(line: &str) -> Option<(&str, &str)> {
    let bytes = line.as_bytes();
    let open = line.find('(')?;
    let name_start = line[..open]
        .rfind(|c: char| !(c.is_alphanumeric() || matches!(c, '_' | '!' | ':' | '.')))
        .map_or(0, |i| i + 1);
    let name = &line[name_start..open];
    if name.is_empty() {
        return None;
    }
    let mut depth = 0usize;
    for (i, &b) in bytes.iter().enumerate().skip(open) {
        match b {
            b'(' => depth += 1,
            b')' => {
                depth -= 1;
                if depth == 0 {
                    return Some((name, &line[name_start..=i]));
                }
            }
            _ => {}
        }
    }
    None
}

/// Scaffold rule `id` from line `line` (1-based) of `source`, which came from file `file`.
///
/// The snippet is the first call on the line with its arguments turned into `$$$ARGS`, or the
/// whole line when it holds no call. The result has a `fire` example from that line and no
/// `clean` example, so `rule check` reports exactly GRL011 until the author adds one.
///
/// # Errors
///
/// [`NewError`] for a malformed id, an unknown language, a missing line or a line without code.
pub fn scaffold(id: &str, file: &str, line: usize, source: &str) -> Result<NewRule, NewError> {
    let letters = id.trim_end_matches(|c: char| c.is_ascii_digit());
    let digits = id.len() - letters.len();
    if letters.is_empty() || digits != 3 || !letters.bytes().all(|b| b.is_ascii_uppercase()) {
        return Err(NewError::BadId(id.to_owned()));
    }
    let (lang, intro) = language(file)?;
    let lines = source.lines().count();
    let text = source
        .lines()
        .nth(line - 1)
        .ok_or(NewError::NoSuchLine { line, lines })?;
    let code = text.trim();
    if code.is_empty() || code.chars().all(|c| "{}();,".contains(c)) || code.contains("\"\"\"") {
        return Err(NewError::NoCode(line));
    }
    let (snippet, shown, head) = match first_call(code) {
        Some((name, call)) => (format!("{name}($$$ARGS)"), call.to_owned(), name.to_owned()),
        None => (
            code.trim_end_matches(';').replace('$', "$$"),
            code.to_owned(),
            code.to_owned(),
        ),
    };
    let bare = head
        .trim_end_matches('!')
        .rsplit(['.', ':'])
        .next()
        .unwrap_or("")
        .to_owned();
    let slug = format!("no-{}", bare.to_lowercase().replace('_', "-"));
    let var = bare.chars().next().map_or('x', |c| c.to_ascii_lowercase());
    let ticks = if snippet.contains('`') { "``" } else { "`" };
    let message = head.replace('"', "");
    let text = format!(
        "rule {id} \"{slug}\" {{\n  lang {lang}\n\n  find {var}: {ticks}{snippet}{ticks}\n  \
         report {var} \"avoid {message}\"\n\n  example fire \"\"\"\n    {code}        {intro} error\n  \"\"\"\n  \
         # add an `example clean` here: code the rule must leave alone\n\n  explain \"\"\"\n    \
         Say why `{message}` should not be used.\n\n    ## Remedy\n    Say what to do instead.\n  \"\"\"\n}}\n"
    );
    Ok(NewRule {
        path: format!("rules/{id}.grl"),
        text,
        from: shown,
        snippet,
    })
}

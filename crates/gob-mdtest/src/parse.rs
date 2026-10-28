//! Parsing of markdown suites into cases and marker expectations.

use std::collections::BTreeMap;

use gob_rules::{RuleId, Severity};

use crate::section::Tree;

/// The outcome class a block expects (testing.md section 1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Expect {
    /// The rule found what it looks for.
    Fire,
    /// The rule examined at least one subject and found nothing.
    Clean,
    /// The rule could not decide: an Unresolved finding.
    Unresolved,
    /// The rule cannot apply to this artifact by construction.
    NotApplicable,
}

/// A constraint on the number of subjects the rule examined.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Subjects {
    /// `subjects=N`: exactly N.
    Exactly(usize),
    /// `subjects>=N`: at least N.
    AtLeast(usize),
}

impl Subjects {
    /// True when `examined` satisfies the constraint.
    #[must_use]
    pub fn admits(self, examined: usize) -> bool {
        match self {
            Self::Exactly(n) => examined == n,
            Self::AtLeast(n) => examined >= n,
        }
    }
}

impl std::fmt::Display for Subjects {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Exactly(n) => write!(f, "subjects={n}"),
            Self::AtLeast(n) => write!(f, "subjects>={n}"),
        }
    }
}

impl std::fmt::Display for Expect {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Fire => "fire",
            Self::Clean => "clean",
            Self::Unresolved => "unresolved",
            Self::NotApplicable => "notapplicable",
        })
    }
}

/// A finding asserted by an inline marker comment.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Marker {
    /// Position in the case's files of the file the marker sits in (0 = the case block).
    pub file: usize,
    /// 1-based line within that file.
    pub line: u32,
    /// Rule named by the marker.
    pub rule: RuleId,
    /// Severity the marker word asserts (`error`, `unresolved`).
    pub severity: Severity,
    /// 1-based byte column the finding must start at, when asserted.
    pub col: Option<u32>,
    /// Substring the finding message must contain, when asserted.
    pub message: Option<String>,
    /// Unresolved reason code the finding must carry, when asserted.
    pub reason: Option<String>,
    /// True when the finding must be a required Unresolved.
    pub required: bool,
}

/// An extra file of a case: a fence with `file=` and no `expect=` in the case's section.
#[derive(Debug, Clone)]
pub struct BlockFile {
    /// Virtual file name (`file=`).
    pub file_name: String,
    /// Fence language (first info token).
    pub language: String,
    /// File body text.
    pub text: String,
    /// `fidelity=F0..F4` for this file's language.
    pub fidelity: Option<String>,
    /// `parse=ok|partial|failed` for this file.
    pub parse: Option<String>,
}

/// One parsed case, before it is handed to the runner.
#[derive(Debug, Clone)]
pub struct Block {
    /// Heading path plus ordinal, for reports.
    pub name: String,
    /// Heading path of the section the case lives in (titles joined by ` / `).
    pub section: String,
    /// Extra files of the case, in document order (the block itself is not listed).
    pub files: Vec<BlockFile>,
    /// `[mdtest] languages` from the section config: extra matrix cells the case fills.
    pub languages: Vec<String>,
    /// 1-based line of the opening fence in the markdown file.
    pub fence_line: usize,
    /// Block language (first info token).
    pub language: String,
    /// Virtual file name.
    pub file_name: String,
    /// Block body text.
    pub text: String,
    /// Rule under test.
    pub rule: RuleId,
    /// Expected outcome class.
    pub expect: Expect,
    /// `reason=CODE`: the Unresolved reason code (expect=unresolved) or the not-applicable reason text (expect=notapplicable).
    pub reason: Option<String>,
    /// `subjects=N` / `subjects>=N`; a clean block with none defaults to at least one.
    pub subjects: Option<Subjects>,
    /// `fidelity=F0..F4`: the adapter fidelity class the case is written for (recorded; checked by the language matrix).
    pub fidelity: Option<String>,
    /// `parse=ok|partial|failed`: the parse status the case is written for (recorded; checked by the language matrix).
    pub parse: Option<String>,
    /// `cell=NAME`: the language-matrix cell the case fills (see [`crate::matrix::CELLS`]).
    pub cell: Option<String>,
    /// `parity=NAME`: the case is one language's version of the named cross-language case.
    pub parity: Option<String>,
    /// `known-gap=~TICKET`: an Unresolved the project accepts, tracked by the ticket.
    pub known_gap: Option<String>,
    /// `fixed`: the case is the text after applying the rule's fix.
    pub fixed: bool,
    /// `rules=A,B`: extra rules the case selects beyond the block rule and marker rules.
    pub rules: Vec<RuleId>,
    /// Effective TOML config: inherited section config merged with any inline `config=`.
    pub config: Option<String>,
    /// Marker expectations of every file of the case.
    pub markers: Vec<Marker>,
    /// True when the `snapshot-diagnostics` suite header was in force.
    pub snapshot: bool,
    /// `<!-- expect-panic: SUBSTRING -->` before the block: the runner must panic with a message containing the substring (empty matches any panic).
    pub expect_panic: Option<String>,
}

/// Why a suite could not be parsed into cases.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("line {line}: {message}")]
pub struct ParseError {
    /// 1-based markdown line of the offending fence.
    pub line: usize,
    /// What is wrong.
    pub message: String,
}

/// Split an info string into tokens, honouring double quotes after `key=`.
fn tokenize(info: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut quoted = false;
    for c in info.chars() {
        match c {
            '"' => quoted = !quoted,
            c if c.is_whitespace() && !quoted => {
                if !cur.is_empty() {
                    out.push(std::mem::take(&mut cur));
                }
            }
            c => cur.push(c),
        }
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

/// Default file extension for a language tag.
fn extension(lang: &str) -> &str {
    match lang {
        "rust" | "rs" => "rs",
        "python" | "py" => "py",
        "javascript" | "js" => "js",
        "typescript" | "ts" => "ts",
        "markdown" | "md" => "md",
        "yaml" | "yml" => "yaml",
        "shell" | "bash" | "sh" => "sh",
        "" => "txt",
        other => other,
    }
}

/// Marker words in matching order, with the severity each asserts.
const WORDS: [(&str, Severity); 2] = [
    ("error", Severity::Error),
    ("unresolved", Severity::Unresolved),
];

/// A marker word found in a comment: where the tail starts and the bracket options.
struct Hit {
    /// Byte offset of the word in the comment.
    at: usize,
    /// Severity the word asserts.
    severity: Severity,
    /// Text after the colon.
    tail_at: usize,
    /// `unresolved[REASON]` reason code, if given.
    reason: Option<String>,
    /// `unresolved[..., required]` flag.
    required: bool,
}

/// Find the earliest marker word (`error:`, `unresolved[R]:`) in `comment`.
fn find_hit(comment: &str) -> Option<Hit> {
    let mut best: Option<Hit> = None;
    for (word, severity) in WORDS {
        for (at, _) in comment.match_indices(word) {
            if comment[..at].ends_with(|c: char| c.is_ascii_alphanumeric()) {
                continue;
            }
            let mut rest = &comment[at + word.len()..];
            let (mut reason, mut required) = (None, false);
            if severity == Severity::Unresolved
                && let Some(inner) = rest.strip_prefix('[').and_then(|r| r.split_once(']'))
            {
                for item in inner.0.split(',').map(str::trim) {
                    if item == "required" {
                        required = true;
                    } else if !item.is_empty() {
                        reason = Some(item.to_owned());
                    }
                }
                rest = inner.1;
            }
            let Some(after) = rest.strip_prefix(':') else {
                continue;
            };
            let tail_at = comment.len() - after.len();
            if best.as_ref().is_none_or(|b| at < b.at) {
                best = Some(Hit {
                    at,
                    severity,
                    tail_at,
                    reason,
                    required,
                });
            }
            break;
        }
    }
    best
}

/// Parse the part of a marker after the colon: `[COL] RULE "substring"`, all optional.
fn parse_tail(tail: &str, default_rule: &RuleId, hit: Hit) -> Result<Marker, String> {
    let mut rest = tail.trim_start();
    let mut col = None;
    if let Some((inner, after)) = rest.strip_prefix('[').and_then(|r| r.split_once(']')) {
        let n: u32 = inner
            .trim()
            .parse()
            .map_err(|_| format!("bad column `[{inner}]`"))?;
        if n == 0 {
            return Err("column is 1-based, got `[0]`".into());
        }
        col = Some(n);
        rest = after.trim_start();
    }
    let id: String = rest
        .chars()
        .take_while(char::is_ascii_alphanumeric)
        .collect();
    rest = rest[id.len()..].trim_start();
    let rule = if id.is_empty() {
        default_rule.clone()
    } else {
        id.parse::<RuleId>().map_err(|e| e.to_string())?
    };
    let message = match rest.strip_prefix('"') {
        Some(q) => Some(
            q.split_once('"')
                .ok_or("unterminated message string")?
                .0
                .to_owned(),
        ),
        None => None,
    };
    Ok(Marker {
        file: 0,
        line: 0,
        rule,
        severity: hit.severity,
        col,
        message,
        reason: hit.reason,
        required: hit.required,
    })
}

/// Extract markers from a block body; an own-line marker applies to the next non-marker line.
fn markers(text: &str, line_err: usize, default_rule: &RuleId) -> Result<Vec<Marker>, ParseError> {
    let mut out: Vec<Marker> = Vec::new();
    let mut pending: Vec<(usize, Marker)> = Vec::new();
    for (i, l) in text.lines().enumerate() {
        let line = u32::try_from(i + 1).unwrap_or(u32::MAX);
        let parsed = ["//", "#", "<!--"]
            .iter()
            .filter_map(|t| l.find(t))
            .min()
            .and_then(|c| find_hit(&l[c..]).map(|h| (c, h)));
        let Some((c, hit)) = parsed else {
            for (_, mut m) in pending.drain(..) {
                m.line = line;
                out.push(m);
            }
            continue;
        };
        let start = ["//", "#", "<!--"]
            .iter()
            .filter_map(|t| l[..c + hit.at].rfind(t))
            .max()
            .unwrap_or(c);
        let tail = &l[c..][hit.tail_at..];
        let mut m = parse_tail(tail, default_rule, hit).map_err(|e| ParseError {
            line: line_err,
            message: format!("bad marker on block line {line}: {e}"),
        })?;
        if l[..start].trim().is_empty() {
            pending.push((i + 1, m));
        } else {
            m.line = line;
            for (_, mut p) in pending.drain(..) {
                p.line = line;
                out.push(p);
            }
            out.push(m);
        }
    }
    if let Some((n, _)) = pending.first() {
        return Err(ParseError {
            line: line_err,
            message: format!("marker on block line {n} has no following line"),
        });
    }
    tracing::debug!(count = out.len(), "markers parsed");
    Ok(out)
}

impl Block {
    /// Every matrix cell the case fills: `cell=` plus the section's `[mdtest] languages`.
    #[must_use]
    pub fn matrix_cells(&self) -> Vec<&str> {
        let mut out: Vec<&str> = self.cell.as_deref().into_iter().collect();
        for l in &self.languages {
            if !out.contains(&l.as_str()) {
                out.push(l.as_str());
            }
        }
        out
    }
}

/// A fence without `expect=` that is part of a case: an extra file or a same-language continuation.
struct Extra {
    /// Section the fence sits in.
    section: usize,
    /// 1-based fence line.
    line: usize,
    /// Fence language.
    language: String,
    /// `file=` name; `None` for a continuation that merges into the case block.
    file: Option<String>,
    /// `fidelity=` value.
    fidelity: Option<String>,
    /// `parse=` value.
    parse: Option<String>,
    /// Fence body.
    body: String,
}

/// Option keys an extra file may carry.
const EXTRA_KEYS: [&str; 3] = ["file", "fidelity", "parse"];

// frob:ticket 01M48PC09SX0KFAM4B3V88AAXW
/// Parse a markdown suite into blocks.
///
/// Headings of any level form a tree; a section is a test (it holds case blocks) or a group
/// (only its descendants do), never both. A fence with `expect=` is a case block. A fence with
/// `file=` and no `expect=` is an extra file of the single case in its section; a same-language
/// fence with neither merges into that case's text in document order. A `toml` fence with no
/// `expect=` configures its section and descendants, a child overriding its parent.
///
/// # Errors
///
/// Returns [`ParseError`] for a malformed info string, missing `rule` or
/// `expect`, an unterminated fence, markers inside a clean or notapplicable block, a section
/// that is both test and group, a duplicate `file=` name, an extra file without exactly one
/// case in its section, or invalid toml config.
#[allow(clippy::too_many_lines)] // one linear pass over the fences; splitting hides the state machine
pub fn parse_suite(md: &str) -> Result<Vec<Block>, ParseError> {
    let mut blocks: Vec<Block> = Vec::new();
    let mut sections: Vec<usize> = Vec::new();
    let mut inline: Vec<Option<String>> = Vec::new();
    let mut extras: Vec<Extra> = Vec::new();
    let mut tree = Tree::new();
    let mut default_rule: Option<RuleId> = None;
    let mut snapshot = false;
    let mut pending_panic: Option<(usize, String)> = None;
    let mut lines = md.lines().enumerate();
    while let Some((i, line)) = lines.next() {
        let t = line.trim_start();
        let fence = ["```", "~~~"].into_iter().find(|f| t.starts_with(f));
        let Some(fence) = fence else {
            if let Some((level, title)) = heading(line) {
                tree.open(level, title);
            } else {
                parse_outside(
                    line,
                    &mut default_rule,
                    &mut snapshot,
                    &mut pending_panic,
                    i + 1,
                )?;
            }
            continue;
        };
        let ticks = t.chars().take_while(|c| fence.starts_with(*c)).count();
        let info = t[ticks..].trim();
        let (body, closed) = fence_body(&mut lines, fence, ticks);
        let fence_line = i + 1;
        if !closed {
            return Err(ParseError {
                line: fence_line,
                message: "unterminated fence".into(),
            });
        }
        let toks = tokenize(info);
        let language = toks.first().cloned().unwrap_or_default();
        let opts: BTreeMap<&str, &str> = toks
            .iter()
            .skip(1)
            .filter_map(|t| t.split_once('='))
            .collect();
        let err = |m: String| ParseError {
            line: fence_line,
            message: m,
        };
        let section = tree.current();
        // Blocks without `expect` are config, extra files or plain documentation, not cases.
        let Some(expect) = opts.get("expect") else {
            if language == "toml" && !opts.contains_key("file") {
                let table: toml::Table = body
                    .parse()
                    .map_err(|e| err(format!("toml config fence is not valid toml: {e}")))?;
                tree.add_toml(section, fence_line, table)?;
            } else {
                if let Some(bad) = opts
                    .keys()
                    .find(|k| opts.contains_key("file") && !EXTRA_KEYS.contains(k))
                {
                    return Err(err(format!(
                        "extra file blocks accept only file=, fidelity= and parse=, got `{bad}=`"
                    )));
                }
                extras.push(Extra {
                    section,
                    line: fence_line,
                    language,
                    file: opts.get("file").map(|f| (*f).to_owned()),
                    fidelity: opts.get("fidelity").map(|t| (*t).to_owned()),
                    parse: opts.get("parse").map(|t| (*t).to_owned()),
                    body,
                });
            }
            continue;
        };
        let expect = match *expect {
            "fire" => Expect::Fire,
            "clean" => Expect::Clean,
            "unresolved" => Expect::Unresolved,
            "notapplicable" => Expect::NotApplicable,
            o => {
                return Err(err(format!(
                    "expect must be fire, clean, unresolved or notapplicable, got `{o}`"
                )));
            }
        };
        let subjects = subjects_of(&opts).map_err(&err)?;
        let (known_gap, fixed, reason) = modifiers(&opts, &toks, expect).map_err(&err)?;
        let rule = match opts.get("rule") {
            Some(r) => r.parse::<RuleId>().map_err(|e| err(e.to_string()))?,
            None => default_rule
                .clone()
                .ok_or_else(|| err("no rule=ID and no suite default".into()))?,
        };
        let file_name = opts.get("file").map_or_else(
            || format!("case.{}", extension(&language)),
            |f| (*f).to_owned(),
        );
        let name = format!(
            "{} #{} (line {fence_line})",
            tree.path(section),
            blocks.len() + 1
        );
        tree.add_head(section, fence_line);
        sections.push(section);
        inline.push(opts.get("config").map(|c| (*c).to_owned()));
        blocks.push(Block {
            name,
            section: tree.path(section),
            files: Vec::new(),
            languages: Vec::new(),
            fence_line,
            fidelity: opts.get("fidelity").map(|t| (*t).to_owned()),
            parse: opts.get("parse").map(|t| (*t).to_owned()),
            language,
            file_name,
            text: body,
            rule,
            expect,
            reason,
            subjects,
            cell: cell_of(&opts).map_err(&err)?,
            parity: opts.get("parity").map(|t| (*t).to_owned()),
            known_gap,
            fixed,
            rules: selected_rules(opts.get("rules").copied()).map_err(&err)?,
            config: None,
            markers: Vec::new(),
            snapshot,
            expect_panic: pending_panic.take().map(|(_, sub)| sub),
        });
    }
    if let Some((line, _)) = pending_panic {
        return Err(ParseError {
            line,
            message: "expect-panic directive is not followed by a case block".into(),
        });
    }
    tree.check_groups()?;
    attach_extras(&mut blocks, &sections, extras)?;
    for (b, (section, raw)) in blocks.iter_mut().zip(sections.iter().zip(&inline)) {
        let err = |message: String| ParseError {
            line: b.fence_line,
            message,
        };
        let settings = tree.settings(*section, raw.as_deref()).map_err(&err)?;
        b.config = settings.config;
        b.languages = settings.languages;
        finish_markers(b)?;
    }
    tracing::debug!(cases = blocks.len(), "suite parsed");
    Ok(blocks)
}

/// A markdown heading line: its level (1..=6) and title.
fn heading(line: &str) -> Option<(usize, &str)> {
    let hashes = line.chars().take_while(|c| *c == '#').count();
    if !(1..=6).contains(&hashes) {
        return None;
    }
    line[hashes..].strip_prefix(' ').map(|t| (hashes, t.trim()))
}

/// Hand each section's extra files and continuations to its single case block.
fn attach_extras(
    blocks: &mut [Block],
    sections: &[usize],
    extras: Vec<Extra>,
) -> Result<(), ParseError> {
    for ex in extras {
        let heads: Vec<usize> = (0..blocks.len())
            .filter(|&i| sections[i] == ex.section)
            .collect();
        let err = |m: String| ParseError {
            line: ex.line,
            message: m,
        };
        let [head] = heads[..] else {
            if ex.file.is_none() {
                continue; // documentation fence
            }
            return Err(err(if heads.is_empty() {
                "file= block has no case block (expect=) in its section".into()
            } else {
                "file= block is ambiguous: its section holds several case blocks".into()
            }));
        };
        let b = &mut blocks[head];
        let Some(file_name) = ex.file else {
            if ex.language == b.language {
                if ex.line < b.fence_line {
                    b.text.insert_str(0, &ex.body);
                } else {
                    b.text.push_str(&ex.body);
                }
            }
            continue;
        };
        if file_name == b.file_name || b.files.iter().any(|f| f.file_name == file_name) {
            return Err(err(format!(
                "duplicate file= name `{file_name}` in one case"
            )));
        }
        b.files.push(BlockFile {
            file_name,
            language: ex.language,
            text: ex.body,
            fidelity: ex.fidelity,
            parse: ex.parse,
        });
    }
    Ok(())
}

/// Parse the markers of every file of `b` and apply the clean/notapplicable restriction.
fn finish_markers(b: &mut Block) -> Result<(), ParseError> {
    let mut marks = markers(&b.text, b.fence_line, &b.rule)?;
    for (n, f) in b.files.iter().enumerate() {
        for mut m in markers(&f.text, b.fence_line, &b.rule)? {
            m.file = n + 1;
            marks.push(m);
        }
    }
    if matches!(b.expect, Expect::Clean | Expect::NotApplicable) && !marks.is_empty() {
        return Err(ParseError {
            line: b.fence_line,
            message: format!("expect={} block must not carry markers", b.expect),
        });
    }
    b.markers = marks;
    Ok(())
}

/// The `cell=` key, checked against the closed matrix cell list.
fn cell_of(opts: &BTreeMap<&str, &str>) -> Result<Option<String>, String> {
    match opts.get("cell") {
        None => Ok(None),
        Some(c) if crate::matrix::CELLS.contains(c) => Ok(Some((*c).to_owned())),
        Some(c) => Err(format!(
            "cell must be one of {}, got `{c}`",
            crate::matrix::CELLS.join(", ")
        )),
    }
}

/// Parse the comma-separated `rules=` list into rule ids.
fn selected_rules(list: Option<&str>) -> Result<Vec<RuleId>, String> {
    list.map_or_else(
        || Ok(Vec::new()),
        |l| {
            l.split(',')
                .map(|r| r.trim().parse::<RuleId>().map_err(|e| e.to_string()))
                .collect()
        },
    )
}

/// Read lines up to the closing fence of `ticks` or more `fence` chars; the body and whether it closed.
fn fence_body<'a>(
    lines: &mut impl Iterator<Item = (usize, &'a str)>,
    fence: &str,
    ticks: usize,
) -> (String, bool) {
    let mut body = String::new();
    for (_, l) in lines {
        let lt = l.trim_start();
        if lt.chars().take_while(|c| fence.starts_with(*c)).count() >= ticks
            && lt
                .trim_start_matches(fence.chars().next().unwrap_or('`'))
                .trim()
                .is_empty()
        {
            return (body, true);
        }
        body.push_str(l);
        body.push('\n');
    }
    (body, false)
}

/// The `known-gap`, `fixed` and `reason` modifiers, each checked against the block's `expect` class.
fn modifiers(
    opts: &BTreeMap<&str, &str>,
    toks: &[String],
    expect: Expect,
) -> Result<(Option<String>, bool, Option<String>), String> {
    let known_gap = opts.get("known-gap").map(|t| (*t).to_owned());
    if let Some(t) = &known_gap
        && !t.starts_with('~')
    {
        return Err(format!(
            "known-gap needs a ticket handle `~XXXXXXX`, got `{t}`"
        ));
    }
    if known_gap.is_some() && expect != Expect::Unresolved {
        return Err("known-gap applies only to expect=unresolved".into());
    }
    let fixed = toks.iter().skip(1).any(|t| t == "fixed");
    if fixed && !matches!(expect, Expect::Clean) {
        return Err("`fixed` applies only to expect=clean".into());
    }
    let reason = opts.get("reason").map(|r| (*r).to_owned());
    if reason.is_some() && !matches!(expect, Expect::Unresolved | Expect::NotApplicable) {
        return Err("reason= applies only to expect=unresolved or notapplicable".into());
    }
    Ok((known_gap, fixed, reason))
}

/// Read `subjects=N` or `subjects>=N` from the info-string options.
fn subjects_of(opts: &BTreeMap<&str, &str>) -> Result<Option<Subjects>, String> {
    let num = |v: &str| {
        v.parse::<usize>()
            .map_err(|_| format!("subjects needs a number, got `{v}`"))
    };
    match (opts.get("subjects"), opts.get("subjects>")) {
        (Some(_), Some(_)) => Err("both subjects= and subjects>= given".into()),
        (Some(v), None) => Ok(Some(Subjects::Exactly(num(v)?))),
        (None, Some(v)) => Ok(Some(Subjects::AtLeast(num(v)?))),
        (None, None) => Ok(None),
    }
}

/// The substring of an `<!-- expect-panic: SUBSTRING -->` line (empty for the bare form), if `line` is one.
fn expect_panic_of(line: &str) -> Option<&str> {
    let inner = line
        .trim()
        .strip_prefix("<!--")?
        .strip_suffix("-->")?
        .trim();
    let rest = inner.strip_prefix("expect-panic")?;
    if rest.is_empty() {
        return Some("");
    }
    rest.strip_prefix(':').map(str::trim)
}

/// Handle a non-fence, non-heading line: the suite header comment and the expect-panic directive.
fn parse_outside(
    line: &str,
    default_rule: &mut Option<RuleId>,
    snapshot: &mut bool,
    pending_panic: &mut Option<(usize, String)>,
    n: usize,
) -> Result<(), ParseError> {
    if let Some(sub) = expect_panic_of(line) {
        if let Some((first, _)) = pending_panic {
            return Err(ParseError {
                line: n,
                message: format!(
                    "second expect-panic directive before a case (first on line {first})"
                ),
            });
        }
        tracing::debug!(line = n, substring = sub, "expect-panic directive");
        *pending_panic = Some((n, sub.to_owned()));
    } else if line.trim() == "<!-- snapshot-diagnostics -->" {
        tracing::debug!(line = n, "snapshot-diagnostics header");
        *snapshot = true;
    } else if let Some(rest) = line
        .trim()
        .strip_prefix("<!-- mdtest:")
        .and_then(|r| r.strip_suffix("-->"))
    {
        for tok in rest.split_whitespace() {
            if tok == "snapshot-diagnostics" {
                tracing::debug!(line = n, "snapshot-diagnostics header");
                *snapshot = true;
            }
            if let Some(r) = tok.strip_prefix("rule=") {
                *default_rule =
                    Some(
                        r.parse()
                            .map_err(|e: gob_rules::ParseRuleIdError| ParseError {
                                line: n,
                                message: e.to_string(),
                            })?,
                    );
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rule() -> RuleId {
        "MDT001".parse().unwrap()
    }

    // frob:tests crates/gob-mdtest/src/parse.rs::markers
    #[test]
    fn trailing_marker_with_column_rule_and_message() {
        let m = markers("a // error: [3] MDT002 \"boo\"\n", 1, &rule()).unwrap();
        assert_eq!(m.len(), 1);
        assert_eq!(m[0].line, 1);
        assert_eq!(m[0].col, Some(3));
        assert_eq!(m[0].rule.as_str(), "MDT002");
        assert_eq!(m[0].message.as_deref(), Some("boo"));
        assert_eq!(m[0].severity, Severity::Error);
    }

    // frob:tests crates/gob-mdtest/src/parse.rs::markers
    #[test]
    fn bare_marker_takes_the_default_rule() {
        let m = markers("a # error:\nb <!-- error: [2] -->\n", 1, &rule()).unwrap();
        assert_eq!(m[0].rule, rule());
        assert_eq!(m[0].severity, Severity::Error);
        assert_eq!(m[1].rule, rule());
        assert_eq!(m[1].col, Some(2));
    }

    // frob:tests crates/gob-mdtest/src/parse.rs::markers
    #[test]
    fn own_line_and_stacked_markers_target_the_next_non_marker_line() {
        let m = markers("// error: [1]\n// unresolved: \"x\"\n\ncode\n", 1, &rule()).unwrap();
        assert_eq!(m.len(), 2);
        assert!(m.iter().all(|m| m.line == 3));
        assert_eq!(m[1].severity, Severity::Unresolved);
    }

    // frob:tests crates/gob-mdtest/src/parse.rs::markers
    #[test]
    fn unresolved_takes_reason_and_required() {
        let m = markers("x // unresolved[hole, required]: [4] \"m\"\n", 1, &rule()).unwrap();
        assert_eq!(m[0].severity, Severity::Unresolved);
        assert_eq!(m[0].reason.as_deref(), Some("hole"));
        assert!(m[0].required);
        let m = markers("x # unresolved:\n", 1, &rule()).unwrap();
        assert_eq!(m[0].reason, None);
        assert!(!m[0].required);
    }

    // frob:tests crates/gob-mdtest/src/parse.rs::markers
    #[test]
    fn malformed_markers_are_parse_errors() {
        for bad in [
            "x // error: [0]\n",
            "x // error: [z]\n",
            "x // error: \"open\n",
            "// error:\n",
            "x // error: not-a-rule\n",
        ] {
            assert!(markers(bad, 7, &rule()).is_err(), "{bad}");
        }
    }

    // frob:tests crates/gob-mdtest/src/parse.rs::markers
    #[test]
    fn plain_comments_and_words_are_not_markers() {
        let m = markers(
            "a // no error here\nb # unresolved thing\nc // myerror: X\n",
            1,
            &rule(),
        );
        assert!(m.unwrap().is_empty());
    }
}

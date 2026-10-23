//! Prose citations of a markdown file (`tickets.md section 6`, `tickets.md#lifecycle`) and the
//! headings they point at.
//!
//! Pure text in, plain values out: this module only finds citations and the sections and anchors
//! a markdown file offers; deciding what a missing target means belongs to the caller.

// frob:ticket 01M4H0RE1Q9A1M47ZT7Q1ZG43K

use std::collections::{HashMap, HashSet};

/// Characters that may appear in the file part of a citation.
const PATH_CHARS: &[u8] = b"_./-~";
/// Characters that may close a quoted or bracketed file name before the locator.
const CLOSERS: &[char] = &['`', '\'', '"', ')', '*', '_'];
/// Characters that may appear inside an anchor.
const ANCHOR_CHARS: &[u8] = b"_-.:";
/// The section sign, an alternative to the word `section` (kept as an escape: sources are ASCII).
const SECTION_SIGN: char = '\u{a7}';

/// Where in the cited file a citation points.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Locator {
    /// `section 6` or `section 6.2`: a numbered heading, number as written (no trailing dot).
    Section(String),
    /// `#anchor`: a heading slug or explicit anchor, as written.
    Anchor(String),
}

/// One `x.md section N` or `x.md#anchor` citation found in a text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Citation {
    /// The cited file as written (`tickets.md`, `docs/design/tickets.md`).
    pub file: String,
    /// The section or anchor cited.
    pub locator: Locator,
    /// Byte offset of the citation's first character in the scanned text.
    pub start: usize,
    /// Byte length of the whole citation.
    pub len: usize,
}

impl Citation {
    /// The citation as a reader would quote it (`tickets.md section 6`, `tickets.md#lifecycle`).
    #[must_use]
    pub fn quoted(&self) -> String {
        match &self.locator {
            Locator::Section(n) => format!("{} section {n}", self.file),
            Locator::Anchor(a) => format!("{}#{a}", self.file),
        }
    }
}

/// True for a byte that continues a word.
fn is_word(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

/// The file token that ends at byte `end` (just after `.md`) of `line`, with its start offset.
fn file_token(line: &str, end: usize) -> Option<(usize, &str)> {
    let bytes = line.as_bytes();
    let mut start = end - 3;
    while start > 0
        && (bytes[start - 1].is_ascii_alphanumeric() || PATH_CHARS.contains(&bytes[start - 1]))
    {
        start -= 1;
    }
    // A leading ellipsis or dot run is not part of the name; `./` and `../` are.
    while line[start..].starts_with('.')
        && !line[start..].starts_with("./")
        && !line[start..].starts_with("../")
    {
        start += 1;
    }
    let token = &line[start..end];
    let stem = token.strip_suffix(".md")?;
    let named = stem.chars().any(|c| c.is_ascii_alphanumeric());
    let rooted = token.starts_with(['/', '~']);
    let glob = start > 0 && matches!(bytes[start - 1], b'*' | b'}' | b'{' | b'$' | b'%');
    let url = line[..start]
        .rsplit(char::is_whitespace)
        .next()
        .is_some_and(|run| run.contains("://") || run.ends_with("//"));
    let linked = line[..start].ends_with("](");
    (named && !rooted && !glob && !url && !linked).then_some((start, token))
}

/// The anchor right after a `#` at the start of `rest`, with its byte length (the `#` included).
fn anchor_after(rest: &str) -> Option<(String, usize)> {
    let body = rest.strip_prefix('#')?;
    let raw = body
        .bytes()
        .take_while(|b| b.is_ascii_alphanumeric() || ANCHOR_CHARS.contains(b))
        .count();
    let anchor = body[..raw].trim_end_matches(['.', ':', '-']);
    (!anchor.is_empty()).then(|| (anchor.to_owned(), 1 + anchor.len()))
}

/// The section number after `section` (or the section sign) in `rest`, the text following the
/// file name, with the byte length consumed from the start of `rest`.
fn section_after(rest: &str) -> Option<(String, usize)> {
    let closed = rest.trim_start_matches(CLOSERS);
    let closed = closed.strip_prefix(',').unwrap_or(closed);
    let after_ws = closed.trim_start();
    let had_ws = after_ws.len() != closed.len();
    let tail = if let Some(t) = after_ws.strip_prefix(SECTION_SIGN) {
        t
    } else {
        if !had_ws {
            return None;
        }
        let word_len = after_ws.bytes().take_while(u8::is_ascii_alphabetic).count();
        let word = after_ws[..word_len].to_ascii_lowercase();
        if !matches!(word.as_str(), "section" | "sections" | "sec") {
            return None;
        }
        let t = &after_ws[word_len..];
        t.strip_prefix('.').unwrap_or(t)
    };
    let num = tail.trim_start();
    let digits = num
        .bytes()
        .take_while(|b| b.is_ascii_digit() || *b == b'.')
        .count();
    let number = num[..digits].trim_end_matches('.');
    if !number.starts_with(|c: char| c.is_ascii_digit()) || number.contains("..") {
        return None;
    }
    Some((number.to_owned(), rest.len() - num.len() + number.len()))
}

/// Append the citations of one line of prose to `out`; offsets are `base` plus the line offset.
pub fn scan_line(line: &str, base: usize, out: &mut Vec<Citation>) {
    for (i, _) in line.match_indices(".md") {
        let end = i + 3;
        if line.as_bytes().get(end).copied().is_some_and(is_word) {
            continue;
        }
        let Some((start, token)) = file_token(line, end) else {
            continue;
        };
        let rest = &line[end..];
        let found = anchor_after(rest)
            .map(|(a, n)| (Locator::Anchor(a), n))
            .or_else(|| section_after(rest).map(|(s, n)| (Locator::Section(s), n)));
        if let Some((locator, used)) = found {
            out.push(Citation {
                file: token.to_owned(),
                locator,
                start: base + start,
                len: end + used - start,
            });
        }
    }
}

/// The fence marker (`` ` `` or `~`), its length and the text after it, when `line` is a fence.
fn fence_of(line: &str) -> Option<(char, usize, &str)> {
    let t = line.trim_start();
    let c = t.chars().next().filter(|c| matches!(c, '`' | '~'))?;
    let n = t.chars().take_while(|x| *x == c).count();
    (n >= 3).then(|| (c, n, &t[n..]))
}

/// The lines of a markdown text outside fenced code blocks: `(offset, line)` pairs.
fn prose_lines(text: &str) -> Vec<(usize, &str)> {
    let mut out = Vec::new();
    let mut fence: Option<(char, usize)> = None;
    let mut pos = 0;
    for raw in text.split_inclusive('\n') {
        let line = raw.trim_end_matches(['\n', '\r']);
        match (fence, fence_of(line)) {
            (None, Some((c, n, _))) => fence = Some((c, n)),
            (Some((c, n)), Some((c2, n2, rest)))
                if c == c2 && n2 >= n && rest.trim().is_empty() =>
            {
                fence = None;
            }
            (None, None) => out.push((pos, line)),
            _ => {}
        }
        pos += raw.len();
    }
    out
}

/// Every citation in a markdown text, skipping fenced code blocks.
#[must_use]
pub fn scan_markdown(text: &str) -> Vec<Citation> {
    let mut out = Vec::new();
    for (offset, line) in prose_lines(text) {
        scan_line(line, offset, &mut out);
    }
    out
}

/// The numbered sections and anchors a markdown file offers.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Headings {
    /// Heading numbers as written, without a trailing dot (`6`, `6.2`).
    numbers: Vec<String>,
    /// Lower-cased anchors: heading slugs (duplicates suffixed `-1`, `-2`) and explicit ids.
    anchors: HashSet<String>,
}

/// The GitHub-style slug of heading text: lower case, letters digits `-` `_` kept, spaces to `-`.
fn slug(text: &str) -> String {
    let mut plain = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(i) = rest.find("](") {
        plain.push_str(&rest[..i]);
        if let Some(j) = rest[i..].find(')') {
            rest = &rest[i + j + 1..];
        } else {
            rest = "";
            break;
        }
    }
    plain.push_str(rest);
    plain
        .to_lowercase()
        .chars()
        .filter_map(|c| match c {
            ' ' => Some('-'),
            '-' | '_' => Some(c),
            c if c.is_alphanumeric() => Some(c),
            _ => None,
        })
        .collect()
}

/// The heading number that opens heading text (`6.`, `6.2`, `Section 6`, section sign 6), if any.
fn number_of(text: &str) -> Option<String> {
    let t = text.trim_start_matches(SECTION_SIGN).trim_start();
    let t = match t.get(..8) {
        Some(w) if w.eq_ignore_ascii_case("section ") => t[8..].trim_start(),
        _ => t,
    };
    let n = t
        .bytes()
        .take_while(|b| b.is_ascii_digit() || *b == b'.')
        .count();
    let next = t[n..].chars().next();
    let number = t[..n].trim_end_matches('.');
    (number.starts_with(|c: char| c.is_ascii_digit())
        && next.is_none_or(|c| c.is_whitespace() || matches!(c, ':' | ')')))
    .then(|| number.to_owned())
}

/// Explicit `<a id="x">` / `<a name="x">` anchors on a line, lower-cased.
fn html_anchors(line: &str) -> Vec<String> {
    let mut out = Vec::new();
    for (i, _) in line.match_indices("<a ") {
        let tag = line[i..].split('>').next().unwrap_or("");
        for key in ["id=\"", "name=\""] {
            if let Some(j) = tag.find(key) {
                let v = &tag[j + key.len()..];
                if let Some(k) = v.find('"') {
                    out.push(v[..k].to_lowercase());
                }
            }
        }
    }
    out
}

/// The text of an ATX heading line (`## Title ##`), without markers, or `None` for other lines.
fn heading_text(line: &str) -> Option<&str> {
    let t = line.trim_start();
    if line.len() - t.len() > 3 {
        return None;
    }
    let hashes = t.bytes().take_while(|b| *b == b'#').count();
    if !(1..=6).contains(&hashes) {
        return None;
    }
    let after = &t[hashes..];
    if !after.is_empty() && !after.starts_with(' ') {
        return None;
    }
    let body = after.trim();
    let cut = body.trim_end_matches('#');
    Some(if cut.is_empty() || cut.ends_with(' ') {
        cut.trim_end()
    } else {
        body
    })
}

impl Headings {
    /// Read the headings of a markdown text, skipping fenced code blocks.
    #[must_use]
    pub fn parse(text: &str) -> Self {
        let mut me = Self::default();
        let mut seen: HashMap<String, usize> = HashMap::new();
        for (_, line) in prose_lines(text) {
            me.anchors.extend(html_anchors(line));
            let Some(mut body) = heading_text(line) else {
                continue;
            };
            if let Some((head, id)) = body
                .rsplit_once("{#")
                .and_then(|(h, r)| Some((h, r.strip_suffix('}')?)))
            {
                me.anchors.insert(id.to_lowercase());
                body = head.trim_end();
            }
            if let Some(n) = number_of(body) {
                me.numbers.push(n);
            }
            let base = slug(body);
            let count = seen.entry(base.clone()).or_insert(0);
            let anchor = if *count == 0 {
                base
            } else {
                format!("{base}-{count}")
            };
            *count += 1;
            me.anchors.insert(anchor);
        }
        me
    }

    /// True when a heading is numbered `number` or sits below it (`6` is offered by `6.2`).
    #[must_use]
    pub fn has_section(&self, number: &str) -> bool {
        self.numbers
            .iter()
            .any(|h| h == number || h.strip_prefix(number).is_some_and(|r| r.starts_with('.')))
    }

    /// True when `anchor` (compared without regard to case) is a heading slug or explicit anchor.
    #[must_use]
    pub fn has_anchor(&self, anchor: &str) -> bool {
        self.anchors.contains(&anchor.to_lowercase())
    }

    /// True when the citation's locator resolves in these headings.
    #[must_use]
    pub fn offers(&self, locator: &Locator) -> bool {
        match locator {
            Locator::Section(n) => self.has_section(n),
            Locator::Anchor(a) => self.has_anchor(a),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cites(text: &str) -> Vec<String> {
        scan_markdown(text).iter().map(Citation::quoted).collect()
    }

    // frob:tests scan_markdown
    #[test]
    fn finds_section_and_anchor_forms() {
        let got = cites(
            "See tickets.md section 6.2, `a/b.md` Section 3. and x.md#life-cycle, y.md\u{a7}4 and z.md#a.\n",
        );
        assert_eq!(
            got,
            [
                "tickets.md section 6.2",
                "a/b.md section 3",
                "x.md#life-cycle",
                "y.md section 4",
                "z.md#a"
            ]
        );
    }

    // frob:tests scan_markdown
    #[test]
    fn skips_fences_urls_links_globs_and_bare_mentions() {
        let text = "```\nin.md section 1\n```\n~~~~\nin2.md#x\n~~~~\nhttps://h.io/a/b.md#frag\n[l](c.md#d)\ndocs/*.md section 1\nplain d.md here\ne.mdx#x\n/abs/f.md section 2\n";
        assert!(cites(text).is_empty(), "{:?}", cites(text));
    }

    // frob:tests scan_markdown
    #[test]
    fn offsets_cover_the_citation() {
        let text = "x\nsee t.md section 6 now";
        let c = &scan_markdown(text)[0];
        assert_eq!(&text[c.start..c.start + c.len], "t.md section 6");
    }

    // frob:tests Headings.parse
    #[test]
    fn headings_offer_numbers_and_slugs() {
        let h = Headings::parse(
            "# T\n## 6. The Life-cycle (v2)\n### 6.2 Sub\n## Same\n## Same\n```\n## 9 hidden\n```\n## Plain {#custom}\n<a id=\"Old\"></a>\n",
        );
        assert!(h.has_section("6") && h.has_section("6.2"));
        assert!(!h.has_section("7") && !h.has_section("9") && !h.has_section("6.3"));
        assert!(h.has_anchor("6-the-life-cycle-v2") && h.has_anchor("SAME-1"));
        assert!(h.has_anchor("custom") && h.has_anchor("old"));
        assert!(!h.has_anchor("hidden"));
    }
}

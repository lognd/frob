//! A parsed Dockerfile: logical instructions with byte ranges, and the build stages.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

/// One logical instruction (continuation lines joined, comments dropped).
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Instruction {
    /// Upper-cased keyword (`RUN`).
    pub keyword: String,
    /// The argument text after the keyword, on one line.
    pub args: String,
    /// Byte range of the instruction in the file (first line start to last line end).
    pub range: (usize, usize),
}

/// One build stage: its `FROM` and the instructions after it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Stage {
    /// The base image reference as written (`rust:1.80`, `builder`).
    pub image: String,
    /// The `AS` name, lower-cased.
    pub name: Option<String>,
    /// Byte range of the `FROM` line.
    pub from_range: (usize, usize),
    /// The instructions of the stage, `FROM` excluded.
    pub body: Vec<Instruction>,
}

/// Split `text` into logical instructions, honouring `\` (or the `# escape=` char) continuations.
pub(crate) fn instructions(text: &str) -> Vec<Instruction> {
    let escape = escape_char(text);
    let mut out = Vec::new();
    let mut current: Option<(String, (usize, usize))> = None;
    let mut offset = 0;
    for raw in text.split_inclusive('\n') {
        let line = raw.trim_end_matches(['\n', '\r']);
        let range = (offset, offset + line.len());
        offset += raw.len();
        let trimmed = line.trim();
        if trimmed.starts_with('#') || (trimmed.is_empty() && current.is_none()) {
            continue;
        }
        let (mut buf, start) = current
            .take()
            .map_or((String::new(), range.0), |(b, r)| (b, r.0));
        let continued = trimmed.ends_with(escape);
        let piece = if continued {
            trimmed.trim_end_matches(escape).trim_end()
        } else {
            trimmed
        };
        if !buf.is_empty() && !piece.is_empty() {
            buf.push(' ');
        }
        buf.push_str(piece);
        if continued {
            current = Some((buf, (start, range.1)));
        } else {
            push(&mut out, &buf, (start, range.1));
        }
    }
    if let Some((buf, range)) = current {
        push(&mut out, &buf, range);
    }
    out
}

/// Append the instruction spelled by `joined` when it is non-empty.
fn push(out: &mut Vec<Instruction>, joined: &str, range: (usize, usize)) {
    let joined = joined.trim();
    if joined.is_empty() {
        return;
    }
    let (kw, args) = joined
        .split_once(char::is_whitespace)
        .unwrap_or((joined, ""));
    out.push(Instruction {
        keyword: kw.to_ascii_uppercase(),
        args: args.trim().to_owned(),
        range,
    });
}

/// The escape character set by a leading `# escape=` parser directive (default backslash).
fn escape_char(text: &str) -> char {
    for line in text.lines() {
        let t = line.trim();
        let Some(rest) = t.strip_prefix('#') else {
            break;
        };
        let Some((k, v)) = rest.split_once('=') else {
            break;
        };
        if k.trim().eq_ignore_ascii_case("escape") {
            return v.trim().chars().next().unwrap_or('\\');
        }
    }
    '\\'
}

/// Split the instructions into build stages; instructions before the first `FROM` (ARG) are dropped.
pub(crate) fn stages(text: &str) -> Vec<Stage> {
    let mut out: Vec<Stage> = Vec::new();
    for ins in instructions(text) {
        if ins.keyword == "FROM" {
            let mut words = ins.args.split_whitespace().filter(|w| !w.starts_with("--"));
            let image = words.next().unwrap_or("").to_owned();
            let name = match (words.next(), words.next()) {
                (Some(a), Some(n)) if a.eq_ignore_ascii_case("as") => Some(n.to_ascii_lowercase()),
                _ => None,
            };
            out.push(Stage {
                image,
                name,
                from_range: ins.range,
                body: Vec::new(),
            });
        } else if let Some(stage) = out.last_mut() {
            stage.body.push(ins);
        }
    }
    out
}

/// True when `image` names an earlier stage of the file or is `scratch`.
pub(crate) fn is_internal(image: &str, earlier: &[Stage]) -> bool {
    image.eq_ignore_ascii_case("scratch")
        || earlier
            .iter()
            .any(|s| s.name.as_deref() == Some(&image.to_ascii_lowercase()))
}

/// Split an image reference into (name, tag, digest); the registry port colon is not a tag.
pub(crate) fn split_ref(image: &str) -> (&str, Option<&str>, Option<&str>) {
    let (rest, digest) = match image.split_once('@') {
        Some((r, d)) => (r, Some(d)),
        None => (image, None),
    };
    let last = rest.rsplit('/').next().unwrap_or(rest);
    match last.rsplit_once(':') {
        Some((_, tag)) => (&rest[..rest.len() - tag.len() - 1], Some(tag), digest),
        None => (rest, None, digest),
    }
}

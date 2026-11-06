//! Pure summarising behind `frob agent digest`: head, tail and error lines of a command's output, plus its content address.

// frob:ticket 01M4P2N1Q1F8PKS9FY2MRH4QCR

use schemars::JsonSchema;
use serde::Serialize;

/// Substrings (lowercase) that mark a line as an error line.
const ERROR_MARKS: [&str; 5] = ["error", "failed", "panicked", "fatal", "traceback"];

/// Longest a single digest line may be before it is cut.
const MAX_LINE: usize = 240;

/// The bounded view of one command's output.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Digest {
    /// Total lines in the full output.
    pub total_lines: usize,
    /// The first lines of the output.
    pub head: Vec<String>,
    /// The last lines of the output (disjoint from `head`).
    pub tail: Vec<String>,
    /// Lines that look like errors, capped; each is `N: text` with its 1-based line number.
    pub errors: Vec<String>,
}

/// The blake3 content address of `bytes`, as lowercase hex.
#[must_use]
pub fn address(bytes: &[u8]) -> String {
    blake3::hash(bytes).to_hex().to_string()
}

/// Cut `line` to [`MAX_LINE`] bytes on a char boundary, marking a cut with `...`.
fn clip(line: &str) -> String {
    if line.len() <= MAX_LINE {
        return line.to_owned();
    }
    let mut end = MAX_LINE;
    while !line.is_char_boundary(end) {
        end -= 1;
    }
    format!("{}...", &line[..end])
}

/// True when `line` contains an error marker, ignoring case.
fn is_error(line: &str) -> bool {
    let lower = line.to_lowercase();
    ERROR_MARKS.iter().any(|m| lower.contains(m))
}

/// Summarise `text`: the first `head` lines, the last `tail` lines and up to `max_errors` error lines.
#[must_use]
pub fn summarize(text: &str, head: usize, tail: usize, max_errors: usize) -> Digest {
    let lines: Vec<&str> = text.lines().collect();
    let total = lines.len();
    let head_n = head.min(total);
    let tail_n = tail.min(total - head_n);
    let errors = lines
        .iter()
        .enumerate()
        .filter(|(_, l)| is_error(l))
        .take(max_errors)
        .map(|(i, l)| format!("{}: {}", i + 1, clip(l)))
        .collect();
    Digest {
        total_lines: total,
        head: lines[..head_n].iter().map(|l| clip(l)).collect(),
        tail: lines[total - tail_n..].iter().map(|l| clip(l)).collect(),
        errors,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/agent/digest.rs::summarize
    #[test]
    fn head_and_tail_are_disjoint() {
        let text = "a\nb\nc\nd\ne\n";
        let d = summarize(text, 2, 2, 10);
        assert_eq!(d.total_lines, 5);
        assert_eq!(d.head, ["a", "b"]);
        assert_eq!(d.tail, ["d", "e"]);
    }

    // frob:tests crates/frob/src/agent/digest.rs::summarize
    #[test]
    fn short_output_is_not_duplicated() {
        let d = summarize("a\nb\n", 5, 5, 10);
        assert_eq!(d.head, ["a", "b"]);
        assert!(d.tail.is_empty());
    }

    // frob:tests crates/frob/src/agent/digest.rs::summarize
    #[test]
    fn error_lines_are_numbered_and_capped() {
        let d = summarize("ok\nError: x\nfine\nFAILED y\nerror z\n", 0, 0, 2);
        assert_eq!(d.errors, ["2: Error: x", "4: FAILED y"]);
    }

    // frob:tests crates/frob/src/agent/digest.rs::summarize
    #[test]
    fn long_lines_are_clipped_on_a_char_boundary() {
        let long = "\u{e9}".repeat(300);
        let d = summarize(&long, 1, 0, 0);
        assert!(d.head[0].ends_with("..."));
        assert!(d.head[0].len() <= MAX_LINE + 3);
    }

    // frob:tests crates/frob/src/agent/digest.rs::address
    #[test]
    fn address_is_stable_hex() {
        assert_eq!(address(b"x"), address(b"x"));
        assert_ne!(address(b"x"), address(b"y"));
        assert_eq!(address(b"x").len(), 64);
    }
}

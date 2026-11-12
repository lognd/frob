//! Instruction-count benchmarks (gungraun, Valgrind callgrind) of the tree-sitter parse entry
//! point for the main grammars, compared against the base by `cargo dev bench-ic` on pull requests.
// frob:ticket 01M5FA5EHT4NSJZP7JVFCZTVFB
#![allow(missing_docs, reason = "gungraun macros generate undocumented items")]

use std::hint::black_box;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gungraun::{library_benchmark, library_benchmark_group, main};

/// Number of repeated units in each synthetic source; small so a run stays fast.
const UNITS: usize = 60;

/// A deterministic source text of `UNITS` repeated units for `lang`.
fn source(lang: &str) -> String {
    (0..UNITS)
        .map(|i| match lang {
            "rust" => format!(
                "/// Doc {i}.\npub fn item_{i}(x: u32) -> u32 {{\n    // frob:ticket T-{i}\n    x + {i}\n}}\n"
            ),
            "python" => format!(
                "def item_{i}(x):\n    \"\"\"Doc {i}.\"\"\"\n    # frob:ticket T-{i}\n    return x + {i}\n\n"
            ),
            "markdown" => format!("## Heading {i}\n\nText {i} with `code` and a [link](a.md).\n\n"),
            _ => format!("[table_{i}]\nkey = {i}\nname = \"value {i}\"\n\n"),
        })
        .collect()
}

// frob:accept DEAD001 because="called by the gungraun main! macro, which the call graph cannot see"
/// Builds the source text outside the measured region.
fn ic_source(lang: &'static str) -> (Language, String) {
    let language = match lang {
        "rust" => Language::Rust,
        "python" => Language::Python,
        "markdown" => Language::Markdown,
        _ => Language::Toml,
    };
    (language, source(lang))
}

// frob:accept DEAD001 because="called by the gungraun main! macro, which the call graph cannot see"
#[library_benchmark]
#[bench::rust(args = ("rust"), setup = ic_source)]
#[bench::python(args = ("python"), setup = ic_source)]
#[bench::markdown(args = ("markdown"), setup = ic_source)]
#[bench::toml(args = ("toml"), setup = ic_source)]
fn parse_source((language, text): (Language, String)) -> bool {
    let result = parse(language, &text, &ParseLimits::default());
    black_box(matches!(result, ParseResult::Parsed(_)))
}

library_benchmark_group!(name = ic; benchmarks = parse_source);

main!(library_benchmark_groups = ic);

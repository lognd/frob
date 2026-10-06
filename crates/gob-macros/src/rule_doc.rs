//! SPIKE (~9R52NCF): structural validation of a rule's colocated `.md` page at macro expansion.
//!
//! Pure text in, human messages out, so the attribute can turn each one into a spanned
//! compile error. Running the examples is test time; this only checks the page has the
//! required shape (rule-authoring.md 2.7).

/// Level-2 sections every rule page must have, in the order the page template lists them.
const REQUIRED_SECTIONS: [&str; 4] = ["What it does", "Why it matters", "Remedy", "Examples"];

/// Check a rule page; each returned string is one problem (empty means the page is valid).
pub(crate) fn validate(md: &str, id: &str, slug: &str) -> Vec<String> {
    let mut problems = Vec::new();
    let mut in_fence = false;
    let mut header = false;
    let mut title: Option<&str> = None;
    let mut sections: Vec<&str> = Vec::new();
    let (mut fire, mut clean) = (false, false);
    for line in md.lines() {
        let t = line.trim_end();
        if t.trim_start().starts_with("```") {
            if !in_fence {
                fire |= t.contains("expect=fire");
                clean |= t.contains("expect=clean");
            }
            in_fence = !in_fence;
            continue;
        }
        if in_fence {
            continue;
        }
        if t.starts_with("<!--") && t.contains("mdtest:") && t.contains(&format!("rule={id}")) {
            header = true;
        } else if let Some(rest) = t.strip_prefix("## ") {
            sections.push(rest.trim());
        } else if let Some(rest) = t.strip_prefix("# ") {
            title.get_or_insert(rest.trim());
        }
    }
    if !header {
        problems.push(format!(
            "missing the header comment `<!-- mdtest: rule={id} -->`"
        ));
    }
    let want = format!("{id} {slug}");
    if title != Some(want.as_str()) {
        problems.push(format!("the title line must be `# {want}`"));
    }
    for s in REQUIRED_SECTIONS {
        if !sections.contains(&s) {
            problems.push(format!("missing the required section `## {s}`"));
        }
    }
    if !fire {
        problems.push("missing a fire example: a code fence marked `expect=fire`".to_owned());
    }
    if !clean {
        problems.push("missing a clean example: a code fence marked `expect=clean`".to_owned());
    }
    problems
}

#[cfg(test)]
mod tests {
    use super::validate;

    const GOOD: &str = "<!-- mdtest: rule=COV001 -->\n# COV001 slug-x\n\nSummary.\n\n## What it does\n## Why it matters\n## Remedy\n## Examples\n### a\n```rust expect=fire file=a.rs\nx\n```\n### b\n```rust expect=clean file=a.rs\ny\n```\n";

    #[test]
    fn good_page_has_no_problems() {
        assert!(validate(GOOD, "COV001", "slug-x").is_empty());
    }

    #[test]
    fn each_gap_is_reported() {
        let bad = GOOD
            .replace("## Remedy\n", "")
            .replace("expect=fire", "expect=nope");
        let p = validate(&bad, "COV001", "slug-x");
        assert_eq!(p.len(), 2, "{p:?}");
        assert!(p[0].contains("Remedy"));
        assert!(p[1].contains("fire"));
    }

    #[test]
    fn headings_inside_fences_do_not_count() {
        let md = GOOD.replace("x\n```\n### b", "## Remedy\n```\n### b");
        let md = md.replace("## Remedy\n## Examples", "## Examples");
        assert_eq!(validate(&md, "COV001", "slug-x").len(), 1);
    }
}

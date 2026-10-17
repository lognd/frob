//! `crunk fix` end to end over a project with no attached fixes.

// frob:ticket 01M43ATCQVX9A1TJ6A4AE48FDX

use gob_cli::run_for_test;

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]
"##;

#[test]
fn dry_run_and_real_run_agree_and_leave_unfixable_sites_alone() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), SPEC).expect("spec");
    std::fs::create_dir_all(dir.path().join("styles/base")).expect("mkdir");
    let css = dir.path().join("styles/base/a.css");
    let body = ".a { margin: 13px; }\n";
    std::fs::write(&css, body).expect("css");
    let cli = crunk::cli();
    let (c1, dry, e1) = run_for_test(&cli, &["fix", "--dry-run"], dir.path());
    assert_eq!(c1, 0, "{dry} {e1}");
    let (c2, real, e2) = run_for_test(&cli, &["fix"], dir.path());
    assert_eq!(c2, 0, "{real} {e2}");
    let strip = |s: &str| s.replace("\"dry_run\":true", "").replace("\"dry_run\":false", "");
    let field = |s: &str| -> Vec<String> {
        s.lines().filter(|l| l.contains("files")).map(str::to_owned).collect()
    };
    assert_eq!(field(&strip(&dry)), field(&strip(&real)));
    assert_eq!(std::fs::read_to_string(&css).expect("read"), body);
}

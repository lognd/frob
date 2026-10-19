use std::path::Path;

fn allowed(p: &Path) -> bool {
    let s = p.to_string_lossy();
    s.starts_with("src/")
}

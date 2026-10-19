use std::path::Path;

fn allowed(p: &Path) -> bool {
    p.starts_with("src")
}

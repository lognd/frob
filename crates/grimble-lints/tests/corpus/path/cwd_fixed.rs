use std::path::Path;

fn is_cwd(p: &Path) -> bool {
    p == Path::new(".")
}

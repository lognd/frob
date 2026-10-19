use std::path::Path;

fn is_cwd(p: &Path) -> bool {
    let s = p.to_str().unwrap();
    s == "./"
}

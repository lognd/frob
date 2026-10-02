//! Holes: syntax errors become hole nodes; the rest of the file still folds.

pub fn fine() {}

pub fn broken() {
    let = ;
    call(;
}

pub fn after() {}

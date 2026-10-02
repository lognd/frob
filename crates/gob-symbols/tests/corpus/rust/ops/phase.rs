//! Phases: macro invocations keep their tokens and their calls (capped at May).

pub fn shout(name: &str) {
    println!("{}", greet(name));
}

fn greet(name: &str) -> String {
    format!("hi {name}")
}

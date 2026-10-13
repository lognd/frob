struct S { v: i32 }
fn f(s: &mut S, a: i32, b: i32) -> i32 {
    let x = a + 1;
    let mut y = b;
    y = x;
    y += 1;
    s.v = x;
    let seen = s.v;
    let c = || x + y;
    if x > 1 {
        y = 2;
    }
    for i in 0..a {
        y = y + i;
    }
    y + seen + c()
}

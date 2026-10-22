fn f(a: i32, sink: Sink) -> i32 {
    let x = compute(a);
    if x > 3 {
        sink.send(x);
    }
    x
}

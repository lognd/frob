function f(a, sink) {
  const x = compute(a);
  if (x > 3) {
    sink.send(x);
  }
  return x;
}

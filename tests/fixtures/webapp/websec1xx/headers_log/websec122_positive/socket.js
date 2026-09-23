function connect() {
  const ws = new WebSocket("ws://example.com/socket");
  return ws;
}

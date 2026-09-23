function connect() {
  const ws = new WebSocket("wss://example.com/socket");
  ws.onopen = () => {
    if (ws.origin !== "https://example.com") {
      ws.close();
    }
  };
  return ws;
}

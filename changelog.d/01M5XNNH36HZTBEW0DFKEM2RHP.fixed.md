Net connect calls (TcpStream::connect, socket.create_connection, requests.get) are now detected as net.connect, and listener binds map only to net.listen.

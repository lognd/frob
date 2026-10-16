fn f(order: Order, sock: Sock) -> Invoice {
    let total = order.line_total + order.sales_tax;
    let invoice = order.invoice_total(total);
    let packet = sock.read_packet_buffer();
    sock.send_packet_header(packet);
    invoice
}

def f(order, sock):
    total = order.line_total + order.sales_tax
    invoice = order.invoice_total(total)
    packet = sock.read_packet_buffer()
    sock.send_packet_header(packet)
    return invoice

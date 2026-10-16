def f(order):
    total = order.line_total + order.sales_tax
    invoice = order.invoice_total(total)
    order.line_total = invoice
    return invoice

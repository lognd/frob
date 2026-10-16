fn f(order: Order) -> Invoice {
    let total = order.line_total + order.sales_tax;
    let invoice = order.invoice_total(total);
    order.line_total = invoice;
    invoice
}

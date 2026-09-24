"""Positive-for-negative control: a ForeignKey column with a matching
migration index -- no SQL104 finding.

frob:ticket T-5337
"""


class Order:
    """A model whose `customer_id` FK column is indexed in
    0001_index.sql.

    frob:ticket T-5337
    """

    customer_id = ForeignKey("Customer")

"""Positive control: SQL104 -- a ForeignKey column with no matching
migration index anywhere under this root.

frob:ticket T-5337
"""


class Order:
    """A model whose `customer_id` FK column has no migration index.

    frob:ticket T-5337
    """

    customer_id = ForeignKey("Customer")

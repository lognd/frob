"""FastAPI WEBSEC401 fixture: one owner-checked handler (clean), one that
skips the owner check (planted finding).

frob:ticket T-5356
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, current_user=Depends(get_current_user)):
    """Clean: correlates the lookup with current_user."""
    return (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.owner == current_user.id)
        .first()
    )


@app.get("/invoices/{invoice_id}/unsafe")
def get_invoice_unsafe(invoice_id: str):
    """Planted finding: no auth identifier referenced anywhere in the body."""
    return db.query(Invoice).filter(Invoice.id == invoice_id).first()

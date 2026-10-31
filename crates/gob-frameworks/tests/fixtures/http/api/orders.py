from fastapi import APIRouter

router = APIRouter(prefix='/api')


@router.post('/orders')
def create_order():
    return {}


@router.get('/orders/{order_id}')
def get_order(order_id: int):
    return {}

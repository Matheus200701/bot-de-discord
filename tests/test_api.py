from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}

def test_create_product_recalculates_from_server_data() -> None:
    response = client.post("/api/v1/products", json={"name": "VIP", "sku": "VIP-1", "price_minor": 2990, "currency": "BRL", "stock_quantity": 10})
    assert response.status_code == 201
    assert response.json()["price_minor"] == 2990

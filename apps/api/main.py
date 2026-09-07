from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from apps.api.webhooks import router as webhook_router

app = FastAPI(title="Discord Commerce API", version="0.1.0")
app.include_router(webhook_router)

class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0)

class Product(ProductIn):
    id: UUID

_products: dict[UUID, Product] = {}

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}

@app.get("/api/v1/products", response_model=list[Product])
async def products() -> list[Product]:
    return list(_products.values())

@app.post("/api/v1/products", response_model=Product, status_code=201)
async def create_product(data: ProductIn) -> Product:
    product = Product(id=uuid4(), **data.model_dump())
    _products[product.id] = product
    return product

@app.get("/api/v1/products/{product_id}", response_model=Product)
async def get_product(product_id: UUID) -> Product:
    product = _products.get(product_id)
    if product is None:
        raise HTTPException(404, "product_not_found")
    return product

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order

app = FastAPI(title="E-Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "E-Commerce backend is running"}


# Utility to convert ObjectId to str in responses

def serialize_doc(doc: dict):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# Products Endpoints

@app.post("/api/products", status_code=201)
def create_product(product: Product):
    try:
        inserted_id = create_document("product", product)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
def list_products(category: Optional[str] = None, limit: int = 50):
    try:
        filter_dict = {"category": category} if category else {}
        docs = get_documents("product", filter_dict=filter_dict, limit=limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    try:
        if db is None:
            raise Exception("Database not available")
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        return serialize_doc(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed-products")
def seed_products():
    try:
        if db is None:
            raise Exception("Database not available")
        products = [
            {
                "title": "Classic White T-Shirt",
                "description": "100% cotton, breathable, and perfect for everyday wear.",
                "price": 699.0,
                "category": "Apparel",
                "image": "https://images.unsplash.com/photo-1520975916090-3105956dac38?w=800",
                "in_stock": True,
            },
            {
                "title": "Wireless Headphones",
                "description": "Noise-cancelling over-ear headphones with 30h battery life.",
                "price": 4999.0,
                "category": "Electronics",
                "image": "https://images.unsplash.com/photo-1518449037270-557fef82de76?w=800",
                "in_stock": True,
            },
            {
                "title": "Ceramic Coffee Mug",
                "description": "Handmade mug with matte finish and 350ml capacity.",
                "price": 349.0,
                "category": "Home",
                "image": "https://images.unsplash.com/photo-1523942839745-7848d4a7aa89?w=800",
                "in_stock": True,
            },
            {
                "title": "Running Shoes",
                "description": "Lightweight shoes designed for comfort and performance.",
                "price": 2999.0,
                "category": "Footwear",
                "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800",
                "in_stock": True,
            },
        ]
        # Insert only if collection empty
        if db["product"].count_documents({}) == 0:
            db["product"].insert_many(products)
            return {"inserted": len(products), "status": "seeded"}
        return {"inserted": 0, "status": "already-seeded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Orders Endpoints

@app.post("/api/orders", status_code=201)
def create_order(order: Order):
    try:
        # Basic validation: ensure product IDs exist
        for item in order.items:
            prod = db["product"].find_one({"_id": ObjectId(item.product_id)})
            if not prod:
                raise HTTPException(status_code=400, detail=f"Invalid product ID: {item.product_id}")
        inserted_id = create_document("order", order)
        return {"id": inserted_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orders")
def list_orders(limit: int = 50):
    try:
        docs = get_documents("order", limit=limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

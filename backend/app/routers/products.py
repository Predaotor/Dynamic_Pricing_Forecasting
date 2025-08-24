from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.org import Organization
from app.models.product import Product

router = APIRouter()

@router.post("/orgs")
def create_org(name: str, db: Session = Depends(get_db)):
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"id": str(org.id), "name": org.name}

@router.post("/products")
def create_product(org_id: str, sku: str, name: str, currency: str, db: Session = Depends(get_db)):
    product = Product(org_id=org_id, sku=sku, name=name, currency=currency)
    db.add(product)
    db.commit()
    db.refresh(product)
    return {
        "id": str(product.id),
        "org_id": str(product.org_id),
        "sku": product.sku,
        "name": product.name,
        "currency": product.currency,
    }

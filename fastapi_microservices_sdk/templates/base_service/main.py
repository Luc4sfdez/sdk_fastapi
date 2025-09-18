# fastapi-microservices-sdk/fastapi_microservices_sdk/templates/base_service/main.py 
"""
Base service template for FastAPI Microservices SDK.

This template provides a basic microservice structure with:
- Health checks
- Service info endpoint
- Basic CRUD operations example
- Error handling
- Logging
"""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Depends
from pydantic import BaseModel

from fastapi_microservices_sdk import create_service


# Pydantic models for the example API
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


# Create the microservice
app = create_service(
    name="base-service",
    version="1.0.0",
    description="Base microservice template with CRUD operations"
)

# In-memory storage for demo purposes
items_db: Dict[int, Item] = {}
next_id = 1


# Custom health check
def database_health_check():
    """Example health check for database connectivity."""
    # In a real service, this would check actual database connectivity
    return {
        "healthy": True,
        "message": "Database connection OK",
        "items_count": len(items_db)
    }


# Add the health check to the service
app.add_health_check(database_health_check)


# API Routes
@app.get("/items", response_model=List[Item], tags=["Items"])
async def get_items(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> List[Item]:
    """Get all items with pagination and filtering."""
    items = list(items_db.values())
    
    if active_only:
        items = [item for item in items if item.is_active]
    
    return items[skip:skip + limit]


@app.get("/items/{item_id}", response_model=Item, tags=["Items"])
async def get_item(item_id: int) -> Item:
    """Get a specific item by ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return items_db[item_id]


@app.post("/items", response_model=Item, status_code=201, tags=["Items"])
async def create_item(item: ItemCreate) -> Item:
    """Create a new item."""
    global next_id
    
    new_item = Item(id=next_id, **item.dict())
    items_db[next_id] = new_item
    next_id += 1
    
    app.logger.info(f"Created item: {new_item.name} (ID: {new_item.id})")
    return new_item


@app.put("/items/{item_id}", response_model=Item, tags=["Items"])
async def update_item(item_id: int, item: ItemUpdate) -> Item:
    """Update an existing item."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    existing_item = items_db[item_id]
    update_data = item.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(existing_item, field, value)
    
    app.logger.info(f"Updated item: {existing_item.name} (ID: {item_id})")
    return existing_item


@app.delete("/items/{item_id}", tags=["Items"])
async def delete_item(item_id: int) -> Dict[str, str]:
    """Delete an item."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    deleted_item = items_db.pop(item_id)
    app.logger.info(f"Deleted item: {deleted_item.name} (ID: {item_id})")
    
    return {"message": f"Item {item_id} deleted successfully"}


@app.get("/stats", tags=["Stats"])
async def get_stats() -> Dict[str, Any]:
    """Get service statistics."""
    active_items = sum(1 for item in items_db.values() if item.is_active)
    inactive_items = len(items_db) - active_items
    
    return {
        "total_items": len(items_db),
        "active_items": active_items,
        "inactive_items": inactive_items,
        "service_info": app.get_service_info()
    }


# Startup event example
@app.add_startup_task
async def startup_task():
    """Example startup task."""
    app.logger.info("Base service startup completed")
    
    # Create some sample data
    sample_items = [
        ItemCreate(name="Sample Item 1", description="First sample item", price=10.99),
        ItemCreate(name="Sample Item 2", description="Second sample item", price=25.50),
        ItemCreate(name="Sample Item 3", description="Third sample item", price=5.00, is_active=False)
    ]
    
    global next_id
    for item_data in sample_items:
        new_item = Item(id=next_id, **item_data.dict())
        items_db[next_id] = new_item
        next_id += 1
    
    app.logger.info(f"Created {len(sample_items)} sample items")


# Shutdown event example
@app.add_shutdown_task
async def shutdown_task():
    """Example shutdown task."""
    app.logger.info("Base service shutting down")
    app.logger.info(f"Final item count: {len(items_db)}")


if __name__ == "__main__":
    # Run the service
    app.run(host="0.0.0.0", port=8000, reload=True)

"""
Data Service Template Example

This example demonstrates how to use the Data Service Template to generate
a comprehensive data service with advanced CRUD operations, caching, search,
and monitoring capabilities.
"""

import asyncio
from pathlib import Path
from fastapi_microservices_sdk.templates.builtin_templates.data_service import DataServiceTemplate


async def basic_data_service_example():
    """Generate a basic data service"""
    print("🚀 Generating Basic Data Service...")
    
    template = DataServiceTemplate()
    
    # Basic configuration
    variables = {
        "service_name": "blog_service",
        "service_description": "Blog management service with posts and comments",
        "service_version": "1.0.0",
        "service_port": 8000,
        "database_type": "postgresql",
        "models": [
            {
                "name": "Post",
                "fields": [
                    {
                        "name": "title",
                        "type": "string",
                        "nullable": False,
                        "max_length": 200,
                        "description": "Post title"
                    },
                    {
                        "name": "content",
                        "type": "text",
                        "nullable": False,
                        "description": "Post content"
                    },
                    {
                        "name": "slug",
                        "type": "string",
                        "nullable": False,
                        "unique": True,
                        "max_length": 100,
                        "description": "URL-friendly post identifier"
                    },
                    {
                        "name": "published",
                        "type": "boolean",
                        "nullable": False,
                        "default": False,
                        "description": "Whether the post is published"
                    },
                    {
                        "name": "view_count",
                        "type": "integer",
                        "nullable": False,
                        "default": 0,
                        "description": "Number of views"
                    },
                    {
                        "name": "published_at",
                        "type": "datetime",
                        "nullable": True,
                        "description": "Publication date"
                    }
                ],
                "relationships": [
                    {
                        "name": "comments",
                        "model": "Comment",
                        "type": "one_to_many"
                    }
                ],
                "indexes": [
                    {
                        "fields": ["slug"],
                        "unique": True
                    },
                    {
                        "fields": ["published", "published_at"]
                    }
                ]
            },
            {
                "name": "Comment",
                "fields": [
                    {
                        "name": "content",
                        "type": "text",
                        "nullable": False,
                        "description": "Comment content"
                    },
                    {
                        "name": "author_name",
                        "type": "string",
                        "nullable": False,
                        "max_length": 100,
                        "description": "Comment author name"
                    },
                    {
                        "name": "author_email",
                        "type": "string",
                        "nullable": False,
                        "max_length": 255,
                        "description": "Comment author email"
                    },
                    {
                        "name": "approved",
                        "type": "boolean",
                        "nullable": False,
                        "default": False,
                        "description": "Whether the comment is approved"
                    },
                    {
                        "name": "post_id",
                        "type": "integer",
                        "nullable": False,
                        "description": "ID of the related post"
                    }
                ],
                "relationships": [
                    {
                        "name": "post",
                        "model": "Post",
                        "type": "many_to_one"
                    }
                ]
            }
        ]
    }
    
    # Generate the service
    output_dir = Path("./generated/blog_service_basic")
    files = template.generate_files(variables, output_dir)
    
    print(f"✅ Generated {len(files)} files in {output_dir}")
    print("📁 Key files generated:")
    for file_path in sorted(files)[:10]:  # Show first 10 files
        print(f"   - {file_path.relative_to(output_dir)}")
    
    if len(files) > 10:
        print(f"   ... and {len(files) - 10} more files")
    
    return output_dir


async def advanced_data_service_example():
    """Generate an advanced data service with all features"""
    print("\n🚀 Generating Advanced Data Service with All Features...")
    
    template = DataServiceTemplate()
    
    # Advanced configuration with all features enabled
    variables = {
        "service_name": "ecommerce_service",
        "service_description": "E-commerce data service with products, orders, and customers",
        "service_version": "2.0.0",
        "service_port": 8080,
        "database_type": "postgresql",
        "database_config": {
            "host": "localhost",
            "port": 5432,
            "database": "ecommerce_db",
            "username": "ecommerce_user",
            "password": "secure_password"
        },
        "enable_cache": True,
        "cache_config": {
            "backend": "redis",
            "host": "localhost",
            "port": 6379,
            "default_ttl": 600
        },
        "enable_search": True,
        "search_config": {
            "backend": "elasticsearch",
            "host": "localhost",
            "port": 9200
        },
        "enable_monitoring": True,
        "enable_analytics": True,
        "enable_export": True,
        "enable_archiving": True,
        "pagination_default_size": 25,
        "pagination_max_size": 500,
        "enable_soft_delete": True,
        "enable_audit_log": True,
        "enable_versioning": True,
        "enable_encryption": False,
        "enable_compression": True,
        "models": [
            {
                "name": "Product",
                "fields": [
                    {
                        "name": "name",
                        "type": "string",
                        "nullable": False,
                        "max_length": 255,
                        "description": "Product name"
                    },
                    {
                        "name": "description",
                        "type": "text",
                        "nullable": True,
                        "description": "Product description"
                    },
                    {
                        "name": "sku",
                        "type": "string",
                        "nullable": False,
                        "unique": True,
                        "max_length": 50,
                        "description": "Stock Keeping Unit"
                    },
                    {
                        "name": "price",
                        "type": "float",
                        "nullable": False,
                        "description": "Product price"
                    },
                    {
                        "name": "stock_quantity",
                        "type": "integer",
                        "nullable": False,
                        "default": 0,
                        "description": "Available stock quantity"
                    },
                    {
                        "name": "category",
                        "type": "string",
                        "nullable": False,
                        "max_length": 100,
                        "description": "Product category"
                    },
                    {
                        "name": "is_active",
                        "type": "boolean",
                        "nullable": False,
                        "default": True,
                        "description": "Whether the product is active"
                    },
                    {
                        "name": "metadata",
                        "type": "json",
                        "nullable": True,
                        "description": "Additional product metadata"
                    }
                ],
                "relationships": [
                    {
                        "name": "order_items",
                        "model": "OrderItem",
                        "type": "one_to_many"
                    }
                ],
                "indexes": [
                    {
                        "fields": ["sku"],
                        "unique": True
                    },
                    {
                        "fields": ["category", "is_active"]
                    },
                    {
                        "fields": ["price"]
                    }
                ]
            },
            {
                "name": "Customer",
                "fields": [
                    {
                        "name": "email",
                        "type": "string",
                        "nullable": False,
                        "unique": True,
                        "max_length": 255,
                        "description": "Customer email address"
                    },
                    {
                        "name": "first_name",
                        "type": "string",
                        "nullable": False,
                        "max_length": 100,
                        "description": "Customer first name"
                    },
                    {
                        "name": "last_name",
                        "type": "string",
                        "nullable": False,
                        "max_length": 100,
                        "description": "Customer last name"
                    },
                    {
                        "name": "phone",
                        "type": "string",
                        "nullable": True,
                        "max_length": 20,
                        "description": "Customer phone number"
                    },
                    {
                        "name": "date_of_birth",
                        "type": "date",
                        "nullable": True,
                        "description": "Customer date of birth"
                    },
                    {
                        "name": "is_premium",
                        "type": "boolean",
                        "nullable": False,
                        "default": False,
                        "description": "Whether the customer has premium status"
                    },
                    {
                        "name": "total_orders",
                        "type": "integer",
                        "nullable": False,
                        "default": 0,
                        "description": "Total number of orders"
                    },
                    {
                        "name": "lifetime_value",
                        "type": "float",
                        "nullable": False,
                        "default": 0.0,
                        "description": "Customer lifetime value"
                    }
                ],
                "relationships": [
                    {
                        "name": "orders",
                        "model": "Order",
                        "type": "one_to_many"
                    }
                ],
                "indexes": [
                    {
                        "fields": ["email"],
                        "unique": True
                    },
                    {
                        "fields": ["is_premium"]
                    },
                    {
                        "fields": ["lifetime_value"]
                    }
                ]
            },
            {
                "name": "Order",
                "fields": [
                    {
                        "name": "order_number",
                        "type": "string",
                        "nullable": False,
                        "unique": True,
                        "max_length": 50,
                        "description": "Unique order number"
                    },
                    {
                        "name": "customer_id",
                        "type": "integer",
                        "nullable": False,
                        "description": "ID of the customer who placed the order"
                    },
                    {
                        "name": "status",
                        "type": "string",
                        "nullable": False,
                        "max_length": 50,
                        "default": "pending",
                        "description": "Order status"
                    },
                    {
                        "name": "total_amount",
                        "type": "float",
                        "nullable": False,
                        "description": "Total order amount"
                    },
                    {
                        "name": "shipping_address",
                        "type": "json",
                        "nullable": False,
                        "description": "Shipping address details"
                    },
                    {
                        "name": "billing_address",
                        "type": "json",
                        "nullable": False,
                        "description": "Billing address details"
                    },
                    {
                        "name": "order_date",
                        "type": "datetime",
                        "nullable": False,
                        "description": "Date when the order was placed"
                    },
                    {
                        "name": "shipped_date",
                        "type": "datetime",
                        "nullable": True,
                        "description": "Date when the order was shipped"
                    },
                    {
                        "name": "delivered_date",
                        "type": "datetime",
                        "nullable": True,
                        "description": "Date when the order was delivered"
                    }
                ],
                "relationships": [
                    {
                        "name": "customer",
                        "model": "Customer",
                        "type": "many_to_one"
                    },
                    {
                        "name": "order_items",
                        "model": "OrderItem",
                        "type": "one_to_many"
                    }
                ],
                "indexes": [
                    {
                        "fields": ["order_number"],
                        "unique": True
                    },
                    {
                        "fields": ["customer_id", "order_date"]
                    },
                    {
                        "fields": ["status"]
                    }
                ]
            },
            {
                "name": "OrderItem",
                "fields": [
                    {
                        "name": "order_id",
                        "type": "integer",
                        "nullable": False,
                        "description": "ID of the related order"
                    },
                    {
                        "name": "product_id",
                        "type": "integer",
                        "nullable": False,
                        "description": "ID of the related product"
                    },
                    {
                        "name": "quantity",
                        "type": "integer",
                        "nullable": False,
                        "description": "Quantity of the product ordered"
                    },
                    {
                        "name": "unit_price",
                        "type": "float",
                        "nullable": False,
                        "description": "Unit price at the time of order"
                    },
                    {
                        "name": "total_price",
                        "type": "float",
                        "nullable": False,
                        "description": "Total price for this line item"
                    }
                ],
                "relationships": [
                    {
                        "name": "order",
                        "model": "Order",
                        "type": "many_to_one"
                    },
                    {
                        "name": "product",
                        "model": "Product",
                        "type": "many_to_one"
                    }
                ],
                "indexes": [
                    {
                        "fields": ["order_id", "product_id"],
                        "unique": True
                    }
                ]
            }
        ]
    }
    
    # Generate the service
    output_dir = Path("./generated/ecommerce_service_advanced")
    files = template.generate_files(variables, output_dir)
    
    print(f"✅ Generated {len(files)} files in {output_dir}")
    print("📁 Key directories created:")
    
    # Show directory structure
    directories = set()
    for file_path in files:
        directories.add(file_path.parent.relative_to(output_dir))
    
    for directory in sorted(directories):
        if str(directory) != ".":
            print(f"   📂 {directory}/")
    
    return output_dir


async def mongodb_data_service_example():
    """Generate a data service using MongoDB"""
    print("\n🚀 Generating MongoDB Data Service...")
    
    template = DataServiceTemplate()
    
    # MongoDB configuration
    variables = {
        "service_name": "content_service",
        "service_description": "Content management service using MongoDB",
        "service_version": "1.0.0",
        "service_port": 8000,
        "database_type": "mongodb",
        "database_config": {
            "host": "localhost",
            "port": 27017,
            "database": "content_db",
            "username": "content_user",
            "password": "mongo_password"
        },
        "enable_cache": True,
        "enable_search": True,
        "enable_monitoring": True,
        "models": [
            {
                "name": "Article",
                "fields": [
                    {
                        "name": "title",
                        "type": "string",
                        "nullable": False,
                        "description": "Article title"
                    },
                    {
                        "name": "content",
                        "type": "text",
                        "nullable": False,
                        "description": "Article content"
                    },
                    {
                        "name": "tags",
                        "type": "list",
                        "nullable": True,
                        "description": "Article tags"
                    },
                    {
                        "name": "metadata",
                        "type": "json",
                        "nullable": True,
                        "description": "Additional metadata"
                    },
                    {
                        "name": "published",
                        "type": "boolean",
                        "nullable": False,
                        "default": False,
                        "description": "Publication status"
                    }
                ]
            }
        ]
    }
    
    # Generate the service
    output_dir = Path("./generated/content_service_mongodb")
    files = template.generate_files(variables, output_dir)
    
    print(f"✅ Generated {len(files)} files in {output_dir}")
    
    return output_dir


async def minimal_data_service_example():
    """Generate a minimal data service with basic features only"""
    print("\n🚀 Generating Minimal Data Service...")
    
    template = DataServiceTemplate()
    
    # Minimal configuration
    variables = {
        "service_name": "simple_service",
        "service_description": "Simple data service with minimal features",
        "database_type": "sqlite",
        "models": [
            {
                "name": "Task",
                "fields": [
                    {
                        "name": "title",
                        "type": "string",
                        "nullable": False,
                        "description": "Task title"
                    },
                    {
                        "name": "completed",
                        "type": "boolean",
                        "nullable": False,
                        "default": False,
                        "description": "Task completion status"
                    }
                ]
            }
        ],
        "enable_cache": False,
        "enable_search": False,
        "enable_monitoring": False,
        "enable_analytics": False,
        "enable_export": False
    }
    
    # Generate the service
    output_dir = Path("./generated/simple_service_minimal")
    files = template.generate_files(variables, output_dir)
    
    print(f"✅ Generated {len(files)} files in {output_dir}")
    
    return output_dir


async def demonstrate_template_validation():
    """Demonstrate template validation"""
    print("\n🔍 Demonstrating Template Validation...")
    
    template = DataServiceTemplate()
    
    # Test valid configuration
    valid_config = {
        "service_name": "valid_service",
        "service_description": "Valid service",
        "database_type": "postgresql",
        "models": [
            {
                "name": "User",
                "fields": [
                    {"name": "username", "type": "string"}
                ]
            }
        ]
    }
    
    errors = template.validate_variables(valid_config)
    print(f"✅ Valid configuration: {len(errors)} errors")
    
    # Test invalid configurations
    invalid_configs = [
        {
            "description": "Missing service name",
            "config": {
                "service_description": "Missing name",
                "database_type": "postgresql",
                "models": []
            }
        },
        {
            "description": "Invalid database type",
            "config": {
                "service_name": "test_service",
                "service_description": "Invalid DB",
                "database_type": "invalid_db",
                "models": []
            }
        },
        {
            "description": "Invalid service name",
            "config": {
                "service_name": "invalid@name!",
                "service_description": "Invalid name",
                "database_type": "postgresql",
                "models": []
            }
        },
        {
            "description": "Missing model fields",
            "config": {
                "service_name": "test_service",
                "service_description": "Missing fields",
                "database_type": "postgresql",
                "models": [{"name": "User"}]
            }
        }
    ]
    
    for test_case in invalid_configs:
        errors = template.validate_variables(test_case["config"])
        print(f"❌ {test_case['description']}: {len(errors)} errors")
        for error in errors[:2]:  # Show first 2 errors
            print(f"   - {error}")


async def show_generated_file_examples(output_dir: Path):
    """Show examples of generated files"""
    print(f"\n📄 Examples of Generated Files in {output_dir.name}:")
    
    # Show main.py content (first 20 lines)
    main_file = output_dir / "app" / "main.py"
    if main_file.exists():
        print("\n📝 app/main.py (first 20 lines):")
        lines = main_file.read_text().split('\n')[:20]
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line}")
        if len(main_file.read_text().split('\n')) > 20:
            print("    ... (truncated)")
    
    # Show model file content (first 15 lines)
    model_files = list((output_dir / "app" / "models").glob("*.py"))
    if model_files and model_files[0].name != "__init__.py":
        model_file = model_files[0]
        print(f"\n📝 {model_file.relative_to(output_dir)} (first 15 lines):")
        lines = model_file.read_text().split('\n')[:15]
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line}")
        if len(model_file.read_text().split('\n')) > 15:
            print("    ... (truncated)")
    
    # Show requirements.txt
    requirements_file = output_dir / "requirements.txt"
    if requirements_file.exists():
        print(f"\n📝 requirements.txt:")
        print(requirements_file.read_text())
    
    # Show directory structure
    print(f"\n📂 Directory Structure:")
    def show_tree(path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0):
        if current_depth >= max_depth:
            return
        
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir() and not item.name.startswith('.'):
                extension = "    " if is_last else "│   "
                show_tree(item, prefix + extension, max_depth, current_depth + 1)
    
    show_tree(output_dir)


async def main():
    """Run all examples"""
    print("🎯 Data Service Template Examples")
    print("=" * 50)
    
    try:
        # Run validation demonstration
        await demonstrate_template_validation()
        
        # Generate different types of services
        basic_dir = await basic_data_service_example()
        advanced_dir = await advanced_data_service_example()
        mongodb_dir = await mongodb_data_service_example()
        minimal_dir = await minimal_data_service_example()
        
        # Show examples of generated files
        await show_generated_file_examples(advanced_dir)
        
        print("\n🎉 All examples completed successfully!")
        print("\n📋 Summary of Generated Services:")
        print(f"   📁 Basic Blog Service: {basic_dir}")
        print(f"   📁 Advanced E-commerce Service: {advanced_dir}")
        print(f"   📁 MongoDB Content Service: {mongodb_dir}")
        print(f"   📁 Minimal Task Service: {minimal_dir}")
        
        print("\n🚀 Next Steps:")
        print("   1. Navigate to any generated service directory")
        print("   2. Copy .env.example to .env and configure")
        print("   3. Install dependencies: pip install -r requirements.txt")
        print("   4. Run the service: uvicorn app.main:app --reload")
        print("   5. Visit http://localhost:8000/docs for API documentation")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
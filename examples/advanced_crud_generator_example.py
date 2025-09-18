"""
Advanced CRUD Generator Example

Demonstrates the usage of the enhanced FastAPI Microservices SDK CRUD Generator.
"""

import asyncio
import tempfile
import json
from pathlib import Path

from fastapi_microservices_sdk.templates.generators import CRUDGenerator


async def main():
    """Main example function."""
    print("🚀 FastAPI Microservices SDK - Advanced CRUD Generator Example")
    print("=" * 70)
    
    # Create temporary directory for examples
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Example 1: Simple User Model
        print("\n👤 Example 1: Simple User Model")
        print("-" * 35)
        
        user_schema = {
            "name": "User",
            "fields": [
                {
                    "name": "email",
                    "type": "email",
                    "description": "User email address",
                    "required": True,
                    "constraints": {
                        "max_length": 255
                    }
                },
                {
                    "name": "full_name",
                    "type": "string",
                    "description": "User full name",
                    "required": True,
                    "constraints": {
                        "max_length": 100,
                        "min_length": 2
                    }
                },
                {
                    "name": "age",
                    "type": "integer",
                    "description": "User age",
                    "required": False,
                    "default": 18,
                    "constraints": {
                        "min_value": 13,
                        "max_value": 120
                    }
                },
                {
                    "name": "is_active",
                    "type": "boolean",
                    "description": "User active status",
                    "required": False,
                    "default": True
                },
                {
                    "name": "bio",
                    "type": "text",
                    "description": "User biography",
                    "required": False,
                    "constraints": {
                        "max_length": 1000
                    }
                },
                {
                    "name": "website",
                    "type": "url",
                    "description": "User website URL",
                    "required": False
                }
            ],
            "relationships": []
        }
        
        generator = CRUDGenerator()
        
        # Generate CRUD for PostgreSQL
        print("🔨 Generating User CRUD for PostgreSQL...")
        user_result = generator.generate(user_schema, {
            "database": "postgresql",
            "generate_tests": True,
            "generate_migrations": True,
            "generate_docs": True,
            "generate_performance_tests": False
        })
        
        print(f"✅ Generated {len(user_result.files)} files for User CRUD:")
        for file in user_result.files:
            print(f"   📄 {file.path}")
        
        # Write files
        user_output = temp_path / "user_crud_postgresql"
        user_result.write_to_directory(user_output)
        print(f"📁 Files written to: {user_output}")
        
        # Example 2: Complex Product Model with Relationships
        print("\n\n🛍️ Example 2: Complex Product Model")
        print("-" * 40)
        
        product_schema = {
            "name": "Product",
            "fields": [
                {
                    "name": "sku",
                    "type": "string",
                    "description": "Product SKU",
                    "required": True,
                    "constraints": {
                        "max_length": 50
                    }
                },
                {
                    "name": "name",
                    "type": "string",
                    "description": "Product name",
                    "required": True,
                    "constraints": {
                        "max_length": 200,
                        "min_length": 3
                    }
                },
                {
                    "name": "description",
                    "type": "text",
                    "description": "Product description",
                    "required": False,
                    "constraints": {
                        "max_length": 2000
                    }
                },
                {
                    "name": "price",
                    "type": "decimal",
                    "description": "Product price",
                    "required": True,
                    "constraints": {
                        "min_value": 0,
                        "max_value": 999999.99
                    }
                },
                {
                    "name": "stock_quantity",
                    "type": "integer",
                    "description": "Stock quantity",
                    "required": True,
                    "default": 0,
                    "constraints": {
                        "min_value": 0
                    }
                },
                {
                    "name": "is_available",
                    "type": "boolean",
                    "description": "Product availability",
                    "required": False,
                    "default": True
                },
                {
                    "name": "category_id",
                    "type": "integer",
                    "description": "Category ID",
                    "required": True
                },
                {
                    "name": "tags",
                    "type": "list",
                    "description": "Product tags",
                    "required": False,
                    "default": []
                },
                {
                    "name": "metadata",
                    "type": "json",
                    "description": "Additional product metadata",
                    "required": False,
                    "default": {}
                },
                {
                    "name": "launch_date",
                    "type": "date",
                    "description": "Product launch date",
                    "required": False
                }
            ],
            "relationships": [
                {
                    "name": "category",
                    "type": "foreign_key",
                    "target_model": "Category",
                    "foreign_key": "category_id",
                    "description": "Product category"
                },
                {
                    "name": "reviews",
                    "type": "one_to_many",
                    "target_model": "Review",
                    "foreign_key": "product_id",
                    "description": "Product reviews"
                },
                {
                    "name": "images",
                    "type": "one_to_many",
                    "target_model": "ProductImage",
                    "foreign_key": "product_id",
                    "description": "Product images"
                }
            ]
        }
        
        print("🔨 Generating Product CRUD with relationships...")
        product_result = generator.generate(product_schema, {
            "database": "postgresql",
            "generate_tests": True,
            "generate_migrations": True,
            "generate_docs": True,
            "generate_performance_tests": True
        })
        
        print(f"✅ Generated {len(product_result.files)} files for Product CRUD:")
        for file in product_result.files:
            print(f"   📄 {file.path}")
        
        # Write files
        product_output = temp_path / "product_crud_postgresql"
        product_result.write_to_directory(product_output)
        print(f"📁 Files written to: {product_output}")
        
        # Example 3: MongoDB Document Model
        print("\n\n🍃 Example 3: MongoDB Document Model")
        print("-" * 40)
        
        blog_post_schema = {
            "name": "BlogPost",
            "fields": [
                {
                    "name": "title",
                    "type": "string",
                    "description": "Blog post title",
                    "required": True,
                    "constraints": {
                        "max_length": 200,
                        "min_length": 5
                    }
                },
                {
                    "name": "slug",
                    "type": "string",
                    "description": "URL slug",
                    "required": True,
                    "constraints": {
                        "max_length": 200
                    }
                },
                {
                    "name": "content",
                    "type": "text",
                    "description": "Blog post content",
                    "required": True,
                    "constraints": {
                        "min_length": 100
                    }
                },
                {
                    "name": "author_id",
                    "type": "uuid",
                    "description": "Author ID",
                    "required": True
                },
                {
                    "name": "published",
                    "type": "boolean",
                    "description": "Publication status",
                    "required": False,
                    "default": False
                },
                {
                    "name": "published_at",
                    "type": "datetime",
                    "description": "Publication timestamp",
                    "required": False
                },
                {
                    "name": "tags",
                    "type": "list",
                    "description": "Post tags",
                    "required": False,
                    "default": []
                },
                {
                    "name": "view_count",
                    "type": "integer",
                    "description": "View count",
                    "required": False,
                    "default": 0,
                    "constraints": {
                        "min_value": 0
                    }
                },
                {
                    "name": "seo_metadata",
                    "type": "json",
                    "description": "SEO metadata",
                    "required": False,
                    "default": {}
                }
            ],
            "relationships": [
                {
                    "name": "author",
                    "type": "reference",
                    "target_model": "User",
                    "foreign_key": "author_id",
                    "description": "Blog post author"
                },
                {
                    "name": "comments",
                    "type": "embedded",
                    "target_model": "Comment",
                    "description": "Blog post comments"
                }
            ]
        }
        
        print("🔨 Generating BlogPost CRUD for MongoDB...")
        blog_result = generator.generate(blog_post_schema, {
            "database": "mongodb",
            "generate_tests": True,
            "generate_migrations": False,  # MongoDB doesn't need migrations
            "generate_docs": True,
            "generate_performance_tests": True
        })
        
        print(f"✅ Generated {len(blog_result.files)} files for BlogPost CRUD:")
        for file in blog_result.files:
            print(f"   📄 {file.path}")
        
        # Write files
        blog_output = temp_path / "blog_crud_mongodb"
        blog_result.write_to_directory(blog_output)
        print(f"📁 Files written to: {blog_output}")
        
        # Example 4: Show Generated Code Samples
        print("\n\n📄 Example 4: Generated Code Samples")
        print("-" * 40)
        
        # Show sample generated model
        user_model_file = user_output / "models" / "user.py"
        if user_model_file.exists():
            print("📋 Sample Generated User Model (first 30 lines):")
            lines = user_model_file.read_text().split('\n')[:30]
            for i, line in enumerate(lines, 1):
                print(f"   {i:2d}: {line}")
            if len(user_model_file.read_text().split('\n')) > 30:
                print("   ...")
        
        # Show sample generated repository
        user_repo_file = user_output / "repositories" / "user.py"
        if user_repo_file.exists():
            print(f"\n🏪 Sample Generated User Repository (first 25 lines):")
            lines = user_repo_file.read_text().split('\n')[:25]
            for i, line in enumerate(lines, 1):
                print(f"   {i:2d}: {line}")
            if len(user_repo_file.read_text().split('\n')) > 25:
                print("   ...")
        
        # Example 5: Validation and Error Handling
        print("\n\n✅ Example 5: Schema Validation")
        print("-" * 35)
        
        # Test with invalid schema
        invalid_schema = {
            "name": "InvalidModel",
            "fields": [
                {
                    "name": "123invalid",  # Invalid field name
                    "type": "unknown_type",  # Invalid type
                    "required": True
                },
                {
                    "name": "duplicate_field",
                    "type": "string",
                    "required": True
                },
                {
                    "name": "duplicate_field",  # Duplicate name
                    "type": "string",
                    "required": True
                }
            ]
        }
        
        print("🔍 Validating invalid schema...")
        validation_errors = generator.validate_schema(invalid_schema)
        
        if validation_errors:
            print("❌ Schema validation failed with errors:")
            for error in validation_errors:
                print(f"   • {error}")
        else:
            print("✅ Schema validation passed")
        
        # Example 6: Advanced Features Demo
        print("\n\n🚀 Example 6: Advanced Features")
        print("-" * 35)
        
        advanced_schema = {
            "name": "Order",
            "fields": [
                {
                    "name": "order_number",
                    "type": "string",
                    "description": "Unique order number",
                    "required": True,
                    "constraints": {
                        "max_length": 20
                    },
                    "validation": {
                        "custom_validator": "if not v.startswith('ORD-'): raise ValueError('Order number must start with ORD-')"
                    }
                },
                {
                    "name": "customer_email",
                    "type": "email",
                    "description": "Customer email",
                    "required": True
                },
                {
                    "name": "total_amount",
                    "type": "decimal",
                    "description": "Total order amount",
                    "required": True,
                    "constraints": {
                        "min_value": 0.01,
                        "max_value": 50000.00
                    }
                },
                {
                    "name": "status",
                    "type": "string",
                    "description": "Order status",
                    "required": True,
                    "default": "pending",
                    "constraints": {
                        "choices": ["pending", "confirmed", "shipped", "delivered", "cancelled"]
                    }
                },
                {
                    "name": "shipping_address",
                    "type": "json",
                    "description": "Shipping address details",
                    "required": True
                },
                {
                    "name": "order_date",
                    "type": "datetime",
                    "description": "Order creation date",
                    "required": True,
                    "auto_generated": True
                },
                {
                    "name": "estimated_delivery",
                    "type": "date",
                    "description": "Estimated delivery date",
                    "required": False
                }
            ],
            "relationships": [
                {
                    "name": "customer",
                    "type": "foreign_key",
                    "target_model": "Customer",
                    "foreign_key": "customer_id",
                    "description": "Order customer"
                },
                {
                    "name": "items",
                    "type": "one_to_many",
                    "target_model": "OrderItem",
                    "foreign_key": "order_id",
                    "description": "Order items"
                }
            ]
        }
        
        print("🔨 Generating advanced Order CRUD with custom validation...")
        order_result = generator.generate(advanced_schema, {
            "database": "postgresql",
            "generate_tests": True,
            "generate_migrations": True,
            "generate_docs": True,
            "generate_performance_tests": True
        })
        
        print(f"✅ Generated {len(order_result.files)} files for Order CRUD:")
        
        # Group files by type
        file_types = {}
        for file in order_result.files:
            file_type = file.path.split('/')[0] if '/' in file.path else 'root'
            if file_type not in file_types:
                file_types[file_type] = []
            file_types[file_type].append(file.path)
        
        for file_type, files in file_types.items():
            print(f"   📁 {file_type.title()}:")
            for file_path in files:
                print(f"      📄 {file_path}")
        
        # Write files
        order_output = temp_path / "order_crud_advanced"
        order_result.write_to_directory(order_output)
        print(f"📁 Files written to: {order_output}")
        
        # Example 7: Performance Metrics
        print("\n\n📊 Example 7: Generation Metrics")
        print("-" * 35)
        
        print("📈 Generation Performance:")
        print(f"   User Model: {len(user_result.files)} files generated")
        print(f"   Product Model: {len(product_result.files)} files generated")
        print(f"   BlogPost Model: {len(blog_result.files)} files generated")
        print(f"   Order Model: {len(order_result.files)} files generated")
        
        print(f"\n🎯 Feature Coverage:")
        print(f"   ✅ Multiple database support (PostgreSQL, MongoDB)")
        print(f"   ✅ Advanced field types and constraints")
        print(f"   ✅ Relationship modeling")
        print(f"   ✅ Custom validation")
        print(f"   ✅ Migration generation")
        print(f"   ✅ Comprehensive test suites")
        print(f"   ✅ API documentation")
        print(f"   ✅ Performance tests")
        print(f"   ✅ Bulk operations")
        print(f"   ✅ Export functionality")
        
        print("\n🎉 Advanced CRUD Generator examples completed!")
        print("\nKey Features Demonstrated:")
        print("✅ Advanced schema validation with constraints")
        print("✅ Multiple database support (SQL and NoSQL)")
        print("✅ Relationship modeling and generation")
        print("✅ Custom validation and business rules")
        print("✅ Comprehensive test generation")
        print("✅ Database migration generation")
        print("✅ API documentation generation")
        print("✅ Performance test generation")
        print("✅ Bulk operations and export functionality")
        print("✅ Type-safe model generation")
        
        print(f"\n📁 All examples generated in: {temp_path}")
        print("Note: Files are in temporary directory and will be cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
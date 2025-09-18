"""
Advanced API Generator Example

Demonstrates the comprehensive API generation capabilities from OpenAPI specifications.
"""

import asyncio
import json
from pathlib import Path
from fastapi_microservices_sdk.templates.generators.api import AdvancedAPIGenerator


# Sample OpenAPI specification
SAMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Pet Store API",
        "description": "A sample API for managing pets",
        "version": "1.0.0"
    },
    "servers": [
        {
            "url": "https://api.petstore.com/v1",
            "description": "Production server"
        }
    ],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "description": "Retrieve a list of all pets in the store",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "description": "Maximum number of pets to return",
                        "required": False,
                        "schema": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10
                        }
                    },
                    {
                        "name": "category",
                        "in": "query",
                        "description": "Filter pets by category",
                        "required": False,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A list of pets",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/Pet"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a new pet",
                "description": "Add a new pet to the store",
                "tags": ["pets"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PetCreate"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Pet created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input"
                    }
                }
            }
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "getPetById",
                "summary": "Get pet by ID",
                "description": "Retrieve a specific pet by its ID",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "description": "ID of the pet to retrieve",
                        "schema": {
                            "type": "integer",
                            "format": "int64"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Pet details",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                }
            },
            "put": {
                "operationId": "updatePet",
                "summary": "Update pet",
                "description": "Update an existing pet",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "description": "ID of the pet to update",
                        "schema": {
                            "type": "integer",
                            "format": "int64"
                        }
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PetUpdate"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Pet updated successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                }
            },
            "delete": {
                "operationId": "deletePet",
                "summary": "Delete pet",
                "description": "Remove a pet from the store",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "description": "ID of the pet to delete",
                        "schema": {
                            "type": "integer",
                            "format": "int64"
                        }
                    }
                ],
                "responses": {
                    "204": {
                        "description": "Pet deleted successfully"
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                }
            }
        },
        "/pets/{petId}/photos": {
            "post": {
                "operationId": "uploadPetPhoto",
                "summary": "Upload pet photo",
                "description": "Upload a photo for a pet",
                "tags": ["pets", "photos"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "description": "ID of the pet",
                        "schema": {
                            "type": "integer",
                            "format": "int64"
                        }
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary"
                                    },
                                    "description": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Photo uploaded successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Photo"
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "required": ["id", "name", "category"],
                "properties": {
                    "id": {
                        "type": "integer",
                        "format": "int64",
                        "description": "Unique identifier for the pet"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the pet",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the pet",
                        "enum": ["dog", "cat", "bird", "fish", "reptile"]
                    },
                    "breed": {
                        "type": "string",
                        "description": "Breed of the pet"
                    },
                    "age": {
                        "type": "integer",
                        "description": "Age of the pet in years",
                        "minimum": 0,
                        "maximum": 30
                    },
                    "weight": {
                        "type": "number",
                        "format": "float",
                        "description": "Weight of the pet in kg",
                        "minimum": 0.1
                    },
                    "vaccinated": {
                        "type": "boolean",
                        "description": "Whether the pet is vaccinated",
                        "default": False
                    },
                    "owner_email": {
                        "type": "string",
                        "format": "email",
                        "description": "Owner's email address"
                    },
                    "microchip_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Microchip identifier"
                    },
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "When the pet was added to the system"
                    },
                    "updated_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "When the pet was last updated"
                    }
                }
            },
            "PetCreate": {
                "type": "object",
                "required": ["name", "category"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the pet",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the pet",
                        "enum": ["dog", "cat", "bird", "fish", "reptile"]
                    },
                    "breed": {
                        "type": "string",
                        "description": "Breed of the pet"
                    },
                    "age": {
                        "type": "integer",
                        "description": "Age of the pet in years",
                        "minimum": 0,
                        "maximum": 30
                    },
                    "weight": {
                        "type": "number",
                        "format": "float",
                        "description": "Weight of the pet in kg",
                        "minimum": 0.1
                    },
                    "vaccinated": {
                        "type": "boolean",
                        "description": "Whether the pet is vaccinated",
                        "default": False
                    },
                    "owner_email": {
                        "type": "string",
                        "format": "email",
                        "description": "Owner's email address"
                    },
                    "microchip_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Microchip identifier"
                    }
                }
            },
            "PetUpdate": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the pet",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the pet",
                        "enum": ["dog", "cat", "bird", "fish", "reptile"]
                    },
                    "breed": {
                        "type": "string",
                        "description": "Breed of the pet"
                    },
                    "age": {
                        "type": "integer",
                        "description": "Age of the pet in years",
                        "minimum": 0,
                        "maximum": 30
                    },
                    "weight": {
                        "type": "number",
                        "format": "float",
                        "description": "Weight of the pet in kg",
                        "minimum": 0.1
                    },
                    "vaccinated": {
                        "type": "boolean",
                        "description": "Whether the pet is vaccinated"
                    },
                    "owner_email": {
                        "type": "string",
                        "format": "email",
                        "description": "Owner's email address"
                    }
                }
            },
            "Photo": {
                "type": "object",
                "required": ["id", "pet_id", "url"],
                "properties": {
                    "id": {
                        "type": "integer",
                        "format": "int64",
                        "description": "Unique identifier for the photo"
                    },
                    "pet_id": {
                        "type": "integer",
                        "format": "int64",
                        "description": "ID of the pet this photo belongs to"
                    },
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "description": "URL of the photo"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the photo"
                    },
                    "uploaded_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "When the photo was uploaded"
                    }
                }
            }
        },
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "apiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
    },
    "security": [
        {
            "bearerAuth": []
        }
    ],
    "tags": [
        {
            "name": "pets",
            "description": "Pet management operations"
        },
        {
            "name": "photos",
            "description": "Pet photo operations"
        }
    ]
}


async def demonstrate_api_generation():
    """Demonstrate comprehensive API generation capabilities."""
    print("🚀 Advanced API Generator Demonstration")
    print("=" * 50)
    
    # Initialize generator
    generator = AdvancedAPIGenerator()
    
    # Generation options
    options = {
        'generate_clients': True,
        'generate_python_client': True,
        'generate_typescript_client': True,
        'generate_tests': True,
        'generate_docs': True,
        'include_authentication': True,
        'include_validation': True,
        'include_error_handling': True
    }
    
    try:
        print("\n📋 Generating API from OpenAPI specification...")
        
        # Generate API code
        result = generator.generate(
            schema={'openapi_spec': SAMPLE_OPENAPI_SPEC},
            options=options
        )
        
        print(f"✅ Generated {len(result.files)} files successfully!")
        print(f"📊 Metadata: {json.dumps(result.metadata, indent=2)}")
        
        # Display generated files
        print("\n📁 Generated Files:")
        for file in result.files:
            print(f"  📄 {file.path} ({file.language})")
            print(f"     Size: {len(file.content)} characters")
        
        # Show sample content from key files
        print("\n🔍 Sample Generated Content:")
        
        # Show models
        models_file = next((f for f in result.files if 'models' in f.path), None)
        if models_file:
            print(f"\n📝 Models ({models_file.path}):")
            print("─" * 40)
            print(models_file.content[:500] + "..." if len(models_file.content) > 500 else models_file.content)
        
        # Show endpoints
        router_file = next((f for f in result.files if 'routers' in f.path), None)
        if router_file:
            print(f"\n🔗 Router ({router_file.path}):")
            print("─" * 40)
            print(router_file.content[:500] + "..." if len(router_file.content) > 500 else router_file.content)
        
        # Show Python client
        python_client = next((f for f in result.files if 'client.py' in f.path), None)
        if python_client:
            print(f"\n🐍 Python Client ({python_client.path}):")
            print("─" * 40)
            print(python_client.content[:500] + "..." if len(python_client.content) > 500 else python_client.content)
        
        # Show TypeScript client
        ts_client = next((f for f in result.files if 'client.ts' in f.path), None)
        if ts_client:
            print(f"\n📘 TypeScript Client ({ts_client.path}):")
            print("─" * 40)
            print(ts_client.content[:500] + "..." if len(ts_client.content) > 500 else ts_client.content)
        
        # Demonstrate writing files to disk
        output_dir = Path("generated_api_example")
        print(f"\n💾 Writing files to {output_dir}...")
        
        result.write_to_directory(output_dir)
        print(f"✅ Files written to {output_dir.absolute()}")
        
        # Show directory structure
        print(f"\n📂 Generated Directory Structure:")
        for file_path in sorted(output_dir.rglob("*")):
            if file_path.is_file():
                relative_path = file_path.relative_to(output_dir)
                print(f"  📄 {relative_path}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        raise


async def demonstrate_openapi_parsing():
    """Demonstrate OpenAPI specification parsing."""
    print("\n🔍 OpenAPI Specification Parsing")
    print("=" * 40)
    
    from fastapi_microservices_sdk.templates.generators.api import OpenAPIParser
    
    parser = OpenAPIParser()
    
    try:
        # Parse the specification
        api_spec = parser.parse(SAMPLE_OPENAPI_SPEC)
        
        print(f"📋 API Title: {api_spec.title}")
        print(f"📋 API Version: {api_spec.version}")
        print(f"📋 API Description: {api_spec.description}")
        print(f"📋 Base URL: {api_spec.base_url}")
        
        print(f"\n🔗 Operations ({len(api_spec.operations)}):")
        for operation in api_spec.operations:
            print(f"  {operation.method.upper()} {operation.path}")
            print(f"    Operation ID: {operation.operation_id}")
            print(f"    Function Name: {operation.get_function_name()}")
            print(f"    Tags: {', '.join(operation.tags)}")
            print(f"    Parameters: {len(operation.parameters)}")
            print(f"    Responses: {len(operation.responses)}")
        
        print(f"\n📊 Schemas ({len(api_spec.schemas)}):")
        for schema in api_spec.schemas:
            print(f"  {schema.name} ({schema.type})")
            print(f"    Class Name: {schema.get_python_class_name()}")
            print(f"    Properties: {len(schema.properties)}")
            print(f"    Required: {len(schema.required)}")
        
        print(f"\n🏷️ Tags: {', '.join(api_spec.get_unique_tags())}")
        
        return api_spec
        
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        raise


async def demonstrate_client_usage():
    """Demonstrate generated client usage."""
    print("\n🔧 Generated Client Usage Examples")
    print("=" * 40)
    
    # Python client usage example
    python_example = '''
# Python Client Usage
from pet_store_api_client import PetStoreAPIClient

# Initialize client
client = PetStoreAPIClient(
    base_url="https://api.petstore.com/v1",
    api_key="your-api-key"
)

# Use the client
with client:
    # List pets
    pets = client.list_pets(limit=10, category="dog")
    
    # Create a new pet
    new_pet = client.create_pet({
        "name": "Buddy",
        "category": "dog",
        "breed": "Golden Retriever",
        "age": 3,
        "vaccinated": True,
        "owner_email": "owner@example.com"
    })
    
    # Get pet by ID
    pet = client.get_pet_by_id(new_pet["id"])
    
    # Update pet
    updated_pet = client.update_pet(pet["id"], {
        "age": 4,
        "weight": 25.5
    })
    
    # Delete pet
    client.delete_pet(pet["id"])
'''
    
    # TypeScript client usage example
    typescript_example = '''
// TypeScript Client Usage
import { PetStoreAPIClient } from './pet_store_api_client';

// Initialize client
const client = new PetStoreAPIClient({
  baseUrl: 'https://api.petstore.com/v1',
  apiKey: 'your-api-key'
});

// Use the client
async function managePets() {
  try {
    // List pets
    const pets = await client.listPets({ limit: 10, category: 'dog' });
    
    // Create a new pet
    const newPet = await client.createPet({
      data: {
        name: 'Buddy',
        category: 'dog',
        breed: 'Golden Retriever',
        age: 3,
        vaccinated: true,
        owner_email: 'owner@example.com'
      }
    });
    
    // Get pet by ID
    const pet = await client.getPetById({ petId: newPet.id });
    
    // Update pet
    const updatedPet = await client.updatePet({
      petId: pet.id,
      data: {
        age: 4,
        weight: 25.5
      }
    });
    
    // Delete pet
    await client.deletePet({ petId: pet.id });
    
  } catch (error) {
    console.error('API Error:', error);
  }
}
'''
    
    print("🐍 Python Client Example:")
    print(python_example)
    
    print("\n📘 TypeScript Client Example:")
    print(typescript_example)


async def main():
    """Main demonstration function."""
    print("🎯 FastAPI Microservices SDK - Advanced API Generator")
    print("=" * 60)
    
    try:
        # Demonstrate OpenAPI parsing
        await demonstrate_openapi_parsing()
        
        # Demonstrate API generation
        result = await demonstrate_api_generation()
        
        # Demonstrate client usage
        await demonstrate_client_usage()
        
        print("\n✨ Advanced API Generator demonstration completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✅ OpenAPI 3.0 specification parsing")
        print("  ✅ FastAPI endpoint generation")
        print("  ✅ Pydantic model generation")
        print("  ✅ Python client SDK generation")
        print("  ✅ TypeScript client SDK generation")
        print("  ✅ Comprehensive test generation")
        print("  ✅ API documentation generation")
        print("  ✅ Parameter validation and typing")
        print("  ✅ Error handling and responses")
        print("  ✅ Authentication integration")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
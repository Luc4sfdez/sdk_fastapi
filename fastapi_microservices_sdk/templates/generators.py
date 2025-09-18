"""
Code Generators

Specialized generators for different types of code generation.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import yaml
from datetime import datetime

from .exceptions import GenerationError
from .config import TemplateConfig
from .generators import AdvancedCRUDGenerator, AdvancedAPIGenerator


@dataclass
class GeneratedFile:
    """Represents a generated code file."""
    path: str
    content: str
    language: str = "python"
    overwrite: bool = True
    
    def write_to_directory(self, base_path: Path) -> None:
        """Write file to directory."""
        file_path = base_path / self.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.content)


@dataclass
class GenerationResult:
    """Result of code generation."""
    files: List[GeneratedFile]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def write_to_directory(self, base_path: Path) -> None:
        """Write all generated files to directory."""
        for file in self.files:
            file.write_to_directory(base_path)


class CodeGenerator(ABC):
    """Base class for code generators."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def generate(self, schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate code from schema."""
        pass
    
    def validate_schema(self, schema: Dict[str, Any]) -> List[str]:
        """Validate input schema."""
        return []


class CRUDGenerator(CodeGenerator):
    """CRUD operations generator from models."""
    
    def __init__(self):
        super().__init__("crud_generator")
        self.supported_databases = ["postgresql", "mysql", "mongodb", "sqlite"]
        self.supported_field_types = {
            "string": "str",
            "text": "str", 
            "integer": "int",
            "bigint": "int",
            "float": "float",
            "decimal": "Decimal",
            "boolean": "bool",
            "datetime": "datetime",
            "date": "date",
            "time": "time",
            "uuid": "UUID",
            "json": "Dict[str, Any]",
            "list": "List[str]",
            "email": "EmailStr",
            "url": "HttpUrl"
        }
    
    def generate(self, schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate CRUD operations from model schema."""
        try:
            options = options or {}
            model_name = schema.get('name', 'Item')
            fields = schema.get('fields', [])
            relationships = schema.get('relationships', [])
            
            # Validate schema
            validation_errors = self.validate_schema(schema)
            if validation_errors:
                raise GenerationError(
                    generator_type=self.name,
                    error_message=f"Schema validation failed: {', '.join(validation_errors)}"
                )
            
            files = []
            database_type = options.get('database', 'postgresql')
            
            # Generate models
            model_files = self._generate_models(model_name, fields, relationships, options)
            files.extend(model_files)
            
            # Generate database models (SQLAlchemy/Beanie)
            if database_type != 'none':
                db_model_file = self._generate_database_model(model_name, fields, relationships, options)
                files.append(db_model_file)
            
            # Generate repository
            repository_file = self._generate_repository(model_name, fields, relationships, options)
            files.append(repository_file)
            
            # Generate service
            service_file = self._generate_service(model_name, fields, relationships, options)
            files.append(service_file)
            
            # Generate endpoints
            endpoints_file = self._generate_endpoints(model_name, fields, relationships, options)
            files.append(endpoints_file)
            
            # Generate schemas for validation
            schemas_file = self._generate_schemas(model_name, fields, relationships, options)
            files.append(schemas_file)
            
            # Generate database migrations
            if database_type in ['postgresql', 'mysql', 'sqlite'] and options.get('generate_migrations', True):
                migration_file = self._generate_migration(model_name, fields, relationships, options)
                files.append(migration_file)
            
            # Generate tests
            if options.get('generate_tests', True):
                test_files = self._generate_comprehensive_tests(model_name, fields, relationships, options)
                files.extend(test_files)
            
            # Generate documentation
            if options.get('generate_docs', True):
                docs_file = self._generate_documentation(model_name, fields, relationships, options)
                files.append(docs_file)
            
            return GenerationResult(
                files=files,
                metadata={
                    'generator': self.name,
                    'model_name': model_name,
                    'database_type': database_type,
                    'fields_count': len(fields),
                    'relationships_count': len(relationships),
                    'generated_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            raise GenerationError(
                generator_type=self.name,
                error_message=str(e),
                context=schema
            )
    
    def validate_schema(self, schema: Dict[str, Any]) -> List[str]:
        """Validate CRUD schema."""
        errors = []
        
        # Validate model name
        if 'name' not in schema:
            errors.append("Model name is required")
        elif not schema['name'].isidentifier():
            errors.append("Model name must be a valid Python identifier")
        
        # Validate fields
        if 'fields' not in schema or not schema['fields']:
            errors.append("At least one field is required")
        
        field_names = set()
        for i, field in enumerate(schema.get('fields', [])):
            if not isinstance(field, dict):
                errors.append(f"Field {i} must be a dictionary")
                continue
            
            # Validate field name
            if 'name' not in field:
                errors.append(f"Field {i} missing name")
            elif not field['name'].isidentifier():
                errors.append(f"Field {i} name must be a valid Python identifier")
            elif field['name'] in field_names:
                errors.append(f"Duplicate field name: {field['name']}")
            else:
                field_names.add(field['name'])
            
            # Validate field type
            if 'type' not in field:
                errors.append(f"Field {i} missing type")
            elif field['type'] not in self.supported_field_types:
                errors.append(f"Field {i} has unsupported type: {field['type']}")
            
            # Validate constraints
            if 'constraints' in field:
                constraint_errors = self._validate_field_constraints(field, i)
                errors.extend(constraint_errors)
        
        # Validate relationships
        for i, relationship in enumerate(schema.get('relationships', [])):
            if not isinstance(relationship, dict):
                errors.append(f"Relationship {i} must be a dictionary")
                continue
            
            required_fields = ['name', 'type', 'target_model']
            for req_field in required_fields:
                if req_field not in relationship:
                    errors.append(f"Relationship {i} missing {req_field}")
        
        return errors
    
    def _validate_field_constraints(self, field: Dict[str, Any], field_index: int) -> List[str]:
        """Validate field constraints."""
        errors = []
        constraints = field.get('constraints', {})
        
        # Validate max_length for string fields
        if field['type'] in ['string', 'text'] and 'max_length' in constraints:
            try:
                max_length = int(constraints['max_length'])
                if max_length <= 0:
                    errors.append(f"Field {field_index} max_length must be positive")
            except (ValueError, TypeError):
                errors.append(f"Field {field_index} max_length must be an integer")
        
        # Validate min/max for numeric fields
        if field['type'] in ['integer', 'float', 'decimal']:
            for constraint in ['min_value', 'max_value']:
                if constraint in constraints:
                    try:
                        float(constraints[constraint])
                    except (ValueError, TypeError):
                        errors.append(f"Field {field_index} {constraint} must be numeric")
        
        return errors
    
    def _generate_models(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate Pydantic models with relationships."""
        files = []
        
        # Generate base model
        base_model = self._generate_base_model(model_name, fields, relationships, options)
        files.append(base_model)
        
        # Generate request/response models
        request_models = self._generate_request_response_models(model_name, fields, relationships, options)
        files.extend(request_models)
        
        return files
    
    def _generate_base_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate base Pydantic model."""
        imports = [
            "from typing import Optional, List, Dict, Any, Union",
            "from pydantic import BaseModel, Field, validator, root_validator",
            "from datetime import datetime, date, time",
            "from decimal import Decimal",
            "from uuid import UUID"
        ]
        
        # Add specific imports based on field types
        field_types = {field['type'] for field in fields}
        if 'email' in field_types:
            imports.append("from pydantic import EmailStr")
        if 'url' in field_types:
            imports.append("from pydantic import HttpUrl")
        if any(rel['type'] == 'foreign_key' for rel in relationships):
            imports.append("from typing import ForwardRef")
        
        # Generate field definitions
        field_definitions = []
        for field in fields:
            field_name = field['name']
            field_type = self._map_field_type(field['type'])
            field_optional = field.get('optional', False)
            field_description = field.get('description', '')
            
            if field_optional:
                field_type = f"Optional[{field_type}]"
            
            field_def = f"    {field_name}: {field_type}"
            
            if field_description or field.get('default') is not None:
                field_attrs = []
                if field_description:
                    field_attrs.append(f'description="{field_description}"')
                if field.get('default') is not None:
                    field_attrs.append(f'default={repr(field["default"])}')
                
                field_def += f" = Field({', '.join(field_attrs)})"
            
            field_definitions.append(field_def)
        
        # Generate model class
        model_content = f'''"""
{model_name} Model

Generated CRUD model for {model_name}.
"""

{chr(10).join(imports)}


class {model_name}Base(BaseModel):
    """Base {model_name} model."""
{chr(10).join(field_definitions)}


class {model_name}Create({model_name}Base):
    """Create {model_name} model."""
    pass


class {model_name}Update(BaseModel):
    """Update {model_name} model."""
{chr(10).join([f"    {field['name']}: Optional[{self._map_field_type(field['type'])}] = None" for field in fields])}


class {model_name}InDB({model_name}Base):
    """Database {model_name} model."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class {model_name}({model_name}InDB):
    """Public {model_name} model."""
    pass
'''
        
        return GeneratedFile(
            path=f"models/{model_name.lower()}.py",
            content=model_content,
            language="python"
        )
    
    def _generate_repository(self, model_name: str, fields: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate repository class."""
        content = f'''"""
{model_name} Repository

Generated CRUD repository for {model_name}.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.{model_name.lower()} import {model_name}, {model_name}Create, {model_name}Update
from ..database.models import {model_name}Model


class {model_name}Repository:
    """Repository for {model_name} operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, obj_in: {model_name}Create) -> {model_name}:
        """Create new {model_name.lower()}."""
        db_obj = {model_name}Model(**obj_in.dict())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return {model_name}.from_orm(db_obj)
    
    def get(self, id: int) -> Optional[{model_name}]:
        """Get {model_name.lower()} by ID."""
        db_obj = self.db.query({model_name}Model).filter({model_name}Model.id == id).first()
        return {model_name}.from_orm(db_obj) if db_obj else None
    
    def get_multi(self, skip: int = 0, limit: int = 100) -> List[{model_name}]:
        """Get multiple {model_name.lower()}s."""
        db_objs = self.db.query({model_name}Model).offset(skip).limit(limit).all()
        return [{model_name}.from_orm(obj) for obj in db_objs]
    
    def update(self, id: int, obj_in: {model_name}Update) -> Optional[{model_name}]:
        """Update {model_name.lower()}."""
        db_obj = self.db.query({model_name}Model).filter({model_name}Model.id == id).first()
        if not db_obj:
            return None
        
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return {model_name}.from_orm(db_obj)
    
    def delete(self, id: int) -> bool:
        """Delete {model_name.lower()}."""
        db_obj = self.db.query({model_name}Model).filter({model_name}Model.id == id).first()
        if not db_obj:
            return False
        
        self.db.delete(db_obj)
        self.db.commit()
        return True
    
    def count(self) -> int:
        """Count total {model_name.lower()}s."""
        return self.db.query({model_name}Model).count()
'''
        
        return GeneratedFile(
            path=f"repositories/{model_name.lower()}.py",
            content=content,
            language="python"
        )
    
    def _generate_service(self, model_name: str, fields: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate service class."""
        content = f'''"""
{model_name} Service

Generated CRUD service for {model_name}.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from ..models.{model_name.lower()} import {model_name}, {model_name}Create, {model_name}Update
from ..repositories.{model_name.lower()} import {model_name}Repository
from ..exceptions import NotFoundError, ValidationError


class {model_name}Service:
    """Service for {model_name} business logic."""
    
    def __init__(self, db: Session):
        self.repository = {model_name}Repository(db)
    
    async def create_{model_name.lower()}(self, obj_in: {model_name}Create) -> {model_name}:
        """Create new {model_name.lower()}."""
        # Add business logic validation here
        return self.repository.create(obj_in)
    
    async def get_{model_name.lower()}(self, id: int) -> {model_name}:
        """Get {model_name.lower()} by ID."""
        obj = self.repository.get(id)
        if not obj:
            raise NotFoundError(f"{model_name} with id {{id}} not found")
        return obj
    
    async def get_{model_name.lower()}s(self, skip: int = 0, limit: int = 100) -> List[{model_name}]:
        """Get multiple {model_name.lower()}s."""
        return self.repository.get_multi(skip=skip, limit=limit)
    
    async def update_{model_name.lower()}(self, id: int, obj_in: {model_name}Update) -> {model_name}:
        """Update {model_name.lower()}."""
        obj = self.repository.update(id, obj_in)
        if not obj:
            raise NotFoundError(f"{model_name} with id {{id}} not found")
        return obj
    
    async def delete_{model_name.lower()}(self, id: int) -> bool:
        """Delete {model_name.lower()}."""
        success = self.repository.delete(id)
        if not success:
            raise NotFoundError(f"{model_name} with id {{id}} not found")
        return success
    
    async def count_{model_name.lower()}s(self) -> int:
        """Count total {model_name.lower()}s."""
        return self.repository.count()
'''
        
        return GeneratedFile(
            path=f"services/{model_name.lower()}.py",
            content=content,
            language="python"
        )
    
    def _generate_endpoints(self, model_name: str, fields: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate FastAPI endpoints."""
        content = f'''"""
{model_name} API Endpoints

Generated CRUD endpoints for {model_name}.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models.{model_name.lower()} import {model_name}, {model_name}Create, {model_name}Update
from ..services.{model_name.lower()} import {model_name}Service
from ..database.session import get_db
from ..exceptions import NotFoundError

router = APIRouter(prefix="/{model_name.lower()}s", tags=["{model_name.lower()}s"])


def get_{model_name.lower()}_service(db: Session = Depends(get_db)) -> {model_name}Service:
    """Get {model_name.lower()} service."""
    return {model_name}Service(db)


@router.post("/", response_model={model_name}, status_code=status.HTTP_201_CREATED)
async def create_{model_name.lower()}(
    obj_in: {model_name}Create,
    service: {model_name}Service = Depends(get_{model_name.lower()}_service)
) -> {model_name}:
    """Create new {model_name.lower()}."""
    return await service.create_{model_name.lower()}(obj_in)


@router.get("/{{id}}", response_model={model_name})
async def get_{model_name.lower()}(
    id: int,
    service: {model_name}Service = Depends(get_{model_name.lower()}_service)
) -> {model_name}:
    """Get {model_name.lower()} by ID."""
    try:
        return await service.get_{model_name.lower()}(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[{model_name}])
async def get_{model_name.lower()}s(
    skip: int = 0,
    limit: int = 100,
    service: {model_name}Service = Depends(get_{model_name.lower()}_service)
) -> List[{model_name}]:
    """Get multiple {model_name.lower()}s."""
    return await service.get_{model_name.lower()}s(skip=skip, limit=limit)


@router.put("/{{id}}", response_model={model_name})
async def update_{model_name.lower()}(
    id: int,
    obj_in: {model_name}Update,
    service: {model_name}Service = Depends(get_{model_name.lower()}_service)
) -> {model_name}:
    """Update {model_name.lower()}."""
    try:
        return await service.update_{model_name.lower()}(id, obj_in)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{model_name.lower()}(
    id: int,
    service: {model_name}Service = Depends(get_{model_name.lower()}_service)
) -> None:
    """Delete {model_name.lower()}."""
    try:
        await service.delete_{model_name.lower()}(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/count", response_model=int)
async def count_{model_name.lower()}s(
    service: {model_name}Service = Depends(get_{model_name.lower()}_service)
) -> int:
    """Count total {model_name.lower()}s."""
    return await service.count_{model_name.lower()}s()
'''
        
        return GeneratedFile(
            path=f"api/endpoints/{model_name.lower()}.py",
            content=content,
            language="python"
        )
    
    def _generate_tests(self, model_name: str, fields: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate test cases."""
        content = f'''"""
{model_name} Tests

Generated test cases for {model_name} CRUD operations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ..models.{model_name.lower()} import {model_name}Create, {model_name}Update


class Test{model_name}CRUD:
    """Test {model_name} CRUD operations."""
    
    def test_create_{model_name.lower()}(self, client: TestClient, db: Session):
        """Test creating {model_name.lower()}."""
        data = {{
{chr(10).join([f'            "{field["name"]}": {self._get_test_value(field)},' for field in fields if not field.get('optional', False)])}
        }}
        
        response = client.post("/{model_name.lower()}s/", json=data)
        assert response.status_code == 201
        
        content = response.json()
        assert content["{fields[0]['name']}"] == data["{fields[0]['name']}"]
        assert "id" in content
        assert "created_at" in content
    
    def test_get_{model_name.lower()}(self, client: TestClient, db: Session):
        """Test getting {model_name.lower()} by ID."""
        # Create test {model_name.lower()}
        data = {{
{chr(10).join([f'            "{field["name"]}": {self._get_test_value(field)},' for field in fields if not field.get('optional', False)])}
        }}
        
        create_response = client.post("/{model_name.lower()}s/", json=data)
        created_id = create_response.json()["id"]
        
        # Get {model_name.lower()}
        response = client.get(f"/{model_name.lower()}s/{{created_id}}")
        assert response.status_code == 200
        
        content = response.json()
        assert content["id"] == created_id
        assert content["{fields[0]['name']}"] == data["{fields[0]['name']}"]
    
    def test_get_{model_name.lower()}s(self, client: TestClient, db: Session):
        """Test getting multiple {model_name.lower()}s."""
        response = client.get("/{model_name.lower()}s/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_update_{model_name.lower()}(self, client: TestClient, db: Session):
        """Test updating {model_name.lower()}."""
        # Create test {model_name.lower()}
        data = {{
{chr(10).join([f'            "{field["name"]}": {self._get_test_value(field)},' for field in fields if not field.get('optional', False)])}
        }}
        
        create_response = client.post("/{model_name.lower()}s/", json=data)
        created_id = create_response.json()["id"]
        
        # Update {model_name.lower()}
        update_data = {{"{fields[0]['name']}": {self._get_test_value(fields[0], updated=True)}}}
        
        response = client.put(f"/{model_name.lower()}s/{{created_id}}", json=update_data)
        assert response.status_code == 200
        
        content = response.json()
        assert content["{fields[0]['name']}"] == update_data["{fields[0]['name']}"]
    
    def test_delete_{model_name.lower()}(self, client: TestClient, db: Session):
        """Test deleting {model_name.lower()}."""
        # Create test {model_name.lower()}
        data = {{
{chr(10).join([f'            "{field["name"]}": {self._get_test_value(field)},' for field in fields if not field.get('optional', False)])}
        }}
        
        create_response = client.post("/{model_name.lower()}s/", json=data)
        created_id = create_response.json()["id"]
        
        # Delete {model_name.lower()}
        response = client.delete(f"/{model_name.lower()}s/{{created_id}}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/{model_name.lower()}s/{{created_id}}")
        assert get_response.status_code == 404
    
    def test_count_{model_name.lower()}s(self, client: TestClient, db: Session):
        """Test counting {model_name.lower()}s."""
        response = client.get("/{model_name.lower()}s/count")
        assert response.status_code == 200
        assert isinstance(response.json(), int)
'''
        
        return GeneratedFile(
            path=f"tests/test_{model_name.lower()}.py",
            content=content,
            language="python"
        )
    
    def _map_field_type(self, field_type: str) -> str:
        """Map field type to Python type."""
        type_mapping = {
            'string': 'str',
            'integer': 'int',
            'float': 'float',
            'boolean': 'bool',
            'datetime': 'datetime',
            'date': 'date',
            'time': 'time',
            'list': 'List[str]',
            'dict': 'Dict[str, Any]'
        }
        return type_mapping.get(field_type, 'str')
    
    def _get_test_value(self, field: Dict[str, Any], updated: bool = False) -> str:
        """Get test value for field."""
        field_type = field['type']
        field_name = field['name']
        
        if field_type == 'string':
            return f'"test_{field_name}{"_updated" if updated else ""}"'
        elif field_type == 'integer':
            return '42' if not updated else '43'
        elif field_type == 'float':
            return '3.14' if not updated else '2.71'
        elif field_type == 'boolean':
            return 'true' if not updated else 'false'
        else:
            return f'"test_value{"_updated" if updated else ""}"'


class APIGenerator(CodeGenerator):
    """API generator from OpenAPI specifications."""
    
    def __init__(self):
        super().__init__("api_generator")
    
    def generate(self, schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate API from OpenAPI specification."""
        try:
            # This is a simplified implementation
            # In a real implementation, you would parse the full OpenAPI spec
            
            api_name = schema.get('info', {}).get('title', 'API')
            paths = schema.get('paths', {})
            
            files = []
            
            # Generate main router
            router_file = self._generate_main_router(api_name, paths, options or {})
            files.append(router_file)
            
            # Generate endpoint files for each path
            for path, methods in paths.items():
                endpoint_file = self._generate_endpoint_file(path, methods, options or {})
                files.append(endpoint_file)
            
            return GenerationResult(
                files=files,
                metadata={
                    'generator': self.name,
                    'api_name': api_name,
                    'generated_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            raise GenerationError(
                generator_type=self.name,
                error_message=str(e),
                context=schema
            )
    
    def _generate_main_router(self, api_name: str, paths: Dict[str, Any], options: Dict[str, Any]) -> GeneratedFile:
        """Generate main API router."""
        content = f'''"""
{api_name} Main Router

Generated main router for {api_name}.
"""

from fastapi import APIRouter

# Import endpoint routers
{chr(10).join([f"from .endpoints.{self._path_to_module_name(path)} import router as {self._path_to_module_name(path)}_router" for path in paths.keys()])}

# Create main router
router = APIRouter()

# Include endpoint routers
{chr(10).join([f"router.include_router({self._path_to_module_name(path)}_router)" for path in paths.keys()])}
'''
        
        return GeneratedFile(
            path="api/main.py",
            content=content,
            language="python"
        )
    
    def _generate_endpoint_file(self, path: str, methods: Dict[str, Any], options: Dict[str, Any]) -> GeneratedFile:
        """Generate endpoint file for a path."""
        module_name = self._path_to_module_name(path)
        
        content = f'''"""
{path} Endpoints

Generated endpoints for {path}.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict

router = APIRouter(prefix="{path}", tags=["{module_name}"])

{chr(10).join([self._generate_endpoint_method(path, method, method_info) for method, method_info in methods.items()])}
'''
        
        return GeneratedFile(
            path=f"api/endpoints/{module_name}.py",
            content=content,
            language="python"
        )
    
    def _generate_endpoint_method(self, path: str, method: str, method_info: Dict[str, Any]) -> str:
        """Generate individual endpoint method."""
        operation_id = method_info.get('operationId', f"{method}_{self._path_to_function_name(path)}")
        summary = method_info.get('summary', f'{method.upper()} {path}')
        
        return f'''
@router.{method.lower()}("/")
async def {operation_id}() -> Dict[str, Any]:
    """
    {summary}
    
    {method_info.get('description', 'Generated endpoint')}
    """
    # TODO: Implement endpoint logic
    return {{"message": "Endpoint not implemented"}}
'''
    
    def _path_to_module_name(self, path: str) -> str:
        """Convert API path to module name."""
        return path.strip('/').replace('/', '_').replace('{', '').replace('}', '').replace('-', '_')
    
    def _path_to_function_name(self, path: str) -> str:
        """Convert API path to function name."""
        return self._path_to_module_name(path)


class TestGenerator(CodeGenerator):
    """Test generator for various code types."""
    
    def __init__(self):
        super().__init__("test_generator")
    
    def generate(self, schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate test cases."""
        try:
            test_type = schema.get('type', 'unit')
            target = schema.get('target', 'module')
            
            files = []
            
            if test_type == 'unit':
                test_file = self._generate_unit_tests(target, schema, options or {})
                files.append(test_file)
            elif test_type == 'integration':
                test_file = self._generate_integration_tests(target, schema, options or {})
                files.append(test_file)
            
            return GenerationResult(
                files=files,
                metadata={
                    'generator': self.name,
                    'test_type': test_type,
                    'target': target,
                    'generated_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            raise GenerationError(
                generator_type=self.name,
                error_message=str(e),
                context=schema
            )
    
    def _generate_unit_tests(self, target: str, schema: Dict[str, Any], options: Dict[str, Any]) -> GeneratedFile:
        """Generate unit test file."""
        content = f'''"""
Unit Tests for {target}

Generated unit tests for {target}.
"""

import pytest
from unittest.mock import Mock, patch

from ..{target} import *


class Test{target.title()}:
    """Unit tests for {target}."""
    
    def test_placeholder(self):
        """Placeholder test."""
        # TODO: Implement actual tests
        assert True
    
    @pytest.fixture
    def mock_dependency(self):
        """Mock dependency fixture."""
        return Mock()
    
    def test_with_mock(self, mock_dependency):
        """Test with mocked dependency."""
        # TODO: Implement test with mock
        assert mock_dependency is not None
'''
        
        return GeneratedFile(
            path=f"tests/unit/test_{target}.py",
            content=content,
            language="python"
        )
    
    def _generate_integration_tests(self, target: str, schema: Dict[str, Any], options: Dict[str, Any]) -> GeneratedFile:
        """Generate integration test file."""
        content = f'''"""
Integration Tests for {target}

Generated integration tests for {target}.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class Test{target.title()}Integration:
    """Integration tests for {target}."""
    
    def test_integration_placeholder(self, client: TestClient, db: Session):
        """Placeholder integration test."""
        # TODO: Implement actual integration tests
        response = client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_async_integration(self, client: TestClient):
        """Async integration test."""
        # TODO: Implement async integration test
        assert True
'''
        
        return GeneratedFile(
            path=f"tests/integration/test_{target}_integration.py",
            content=content,
            language="python"
        )    de
f _generate_request_response_models(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate request and response models."""
        files = []
        
        # Generate Create model
        create_model = self._generate_create_model(model_name, fields, relationships, options)
        files.append(create_model)
        
        # Generate Update model
        update_model = self._generate_update_model(model_name, fields, relationships, options)
        files.append(update_model)
        
        # Generate Response model
        response_model = self._generate_response_model(model_name, fields, relationships, options)
        files.append(response_model)
        
        return files
    
    def _generate_create_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate create model."""
        content = f'''"""
{model_name} Create Model

Pydantic model for creating {model_name} instances.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

{self._generate_field_imports(fields)}


class {model_name}Create(BaseModel):
    """Model for creating {model_name} instances."""
    
{self._generate_create_fields(fields, relationships)}

{self._generate_validators(fields, model_name + "Create")}

    class Config:
        schema_extra = {{
            "example": {self._generate_example_data(fields, relationships, exclude_auto=True)}
        }}
'''
        
        return GeneratedFile(
            path=f"models/{model_name.lower()}_create.py",
            content=content,
            language="python"
        )
    
    def _generate_update_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate update model."""
        content = f'''"""
{model_name} Update Model

Pydantic model for updating {model_name} instances.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

{self._generate_field_imports(fields)}


class {model_name}Update(BaseModel):
    """Model for updating {model_name} instances."""
    
{self._generate_update_fields(fields, relationships)}

{self._generate_validators(fields, model_name + "Update")}

    class Config:
        schema_extra = {{
            "example": {self._generate_example_data(fields, relationships, exclude_auto=True, optional=True)}
        }}
'''
        
        return GeneratedFile(
            path=f"models/{model_name.lower()}_update.py",
            content=content,
            language="python"
        )
    
    def _generate_response_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate response model."""
        content = f'''"""
{model_name} Response Model

Pydantic model for {model_name} API responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

{self._generate_field_imports(fields)}


class {model_name}Response(BaseModel):
    """Model for {model_name} API responses."""
    
    id: int = Field(..., description="Unique identifier")
{self._generate_response_fields(fields, relationships)}
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

{self._generate_relationship_response_fields(relationships)}

    class Config:
        from_attributes = True
        schema_extra = {{
            "example": {self._generate_example_data(fields, relationships, include_id=True)}
        }}


class {model_name}ListResponse(BaseModel):
    """Model for paginated {model_name} list responses."""
    
    items: List[{model_name}Response] = Field(..., description="List of {model_name.lower()} items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    
    class Config:
        schema_extra = {{
            "example": {{
                "items": [{self._generate_example_data(fields, relationships, include_id=True)}],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }}
        }}
'''
        
        return GeneratedFile(
            path=f"models/{model_name.lower()}_response.py",
            content=content,
            language="python"
        )
    
    def _generate_database_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate database model (SQLAlchemy or Beanie)."""
        database_type = options.get('database', 'postgresql')
        
        if database_type == 'mongodb':
            return self._generate_beanie_model(model_name, fields, relationships, options)
        else:
            return self._generate_sqlalchemy_model(model_name, fields, relationships, options)
    
    def _generate_sqlalchemy_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate SQLAlchemy model."""
        database_type = options.get('database', 'postgresql')
        
        content = f'''"""
{model_name} Database Model

SQLAlchemy model for {model_name} database operations.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Time, Float, Numeric, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from ..database.base import Base


class {model_name}Model(Base):
    """SQLAlchemy model for {model_name}."""
    
    __tablename__ = "{model_name.lower()}s"
    
    id = Column(Integer, primary_key=True, index=True)
{self._generate_sqlalchemy_fields(fields, database_type)}
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

{self._generate_sqlalchemy_relationships(relationships)}

    def __repr__(self):
        return f"<{model_name}(id={{self.id}}, {self._get_repr_field(fields)})>"
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {{
            "id": self.id,
{self._generate_to_dict_fields(fields)}
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }}
'''
        
        return GeneratedFile(
            path=f"models/database/{model_name.lower()}_model.py",
            content=content,
            language="python"
        )
    
    def _generate_beanie_model(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate Beanie model for MongoDB."""
        content = f'''"""
{model_name} MongoDB Model

Beanie model for {model_name} MongoDB operations.
"""

from typing import Optional, List, Dict, Any
from beanie import Document, Indexed, Link
from pydantic import Field
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID, uuid4

{self._generate_field_imports(fields)}


class {model_name}Document(Document):
    """Beanie document for {model_name}."""
    
{self._generate_beanie_fields(fields, relationships)}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

{self._generate_beanie_relationships(relationships)}

    class Settings:
        name = "{model_name.lower()}s"
        indexes = [
{self._generate_beanie_indexes(fields)}
        ]
    
    def __repr__(self):
        return f"<{model_name}(id={{self.id}}, {self._get_repr_field(fields)})>"
    
    async def save_with_timestamp(self, **kwargs):
        """Save document with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save(**kwargs)
'''
        
        return GeneratedFile(
            path=f"models/database/{model_name.lower()}_document.py",
            content=content,
            language="python"
        )
    
    def _generate_schemas(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate validation schemas."""
        content = f'''"""
{model_name} Validation Schemas

Pydantic schemas for {model_name} validation and serialization.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from enum import Enum

{self._generate_field_imports(fields)}


class {model_name}FilterSchema(BaseModel):
    """Schema for filtering {model_name} queries."""
    
{self._generate_filter_fields(fields)}
    
    # Pagination
    page: Optional[int] = Field(1, ge=1, description="Page number")
    size: Optional[int] = Field(10, ge=1, le=100, description="Page size")
    
    # Sorting
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$", description="Sort order")
    
    # Search
    search: Optional[str] = Field(None, min_length=1, description="Search query")


class {model_name}BulkCreateSchema(BaseModel):
    """Schema for bulk creating {model_name} instances."""
    
    items: List[{model_name}Create] = Field(..., min_items=1, max_items=100, description="Items to create")
    
    @validator('items')
    def validate_unique_items(cls, v):
        """Validate that items are unique based on key fields."""
        # Add custom validation logic here
        return v


class {model_name}BulkUpdateSchema(BaseModel):
    """Schema for bulk updating {model_name} instances."""
    
    updates: List[Dict[str, Any]] = Field(..., min_items=1, max_items=100, description="Updates to apply")
    
    @validator('updates')
    def validate_updates(cls, v):
        """Validate update operations."""
        for update in v:
            if 'id' not in update:
                raise ValueError("Each update must include an 'id' field")
        return v


class {model_name}ExportSchema(BaseModel):
    """Schema for exporting {model_name} data."""
    
    format: str = Field("csv", regex="^(csv|json|xlsx)$", description="Export format")
    fields: Optional[List[str]] = Field(None, description="Fields to include in export")
    filters: Optional[{model_name}FilterSchema] = Field(None, description="Filters to apply")
    
    @validator('fields')
    def validate_fields(cls, v):
        """Validate that requested fields exist."""
        if v is not None:
            valid_fields = {{{', '.join([f'"{field["name"]}"' for field in fields])}}}
            for field in v:
                if field not in valid_fields:
                    raise ValueError(f"Invalid field: {{field}}")
        return v
'''
        
        return GeneratedFile(
            path=f"schemas/{model_name.lower()}_schemas.py",
            content=content,
            language="python"
        )
    
    def _generate_migration(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate Alembic migration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        revision_id = f"create_{model_name.lower()}_table"
        
        content = f'''"""Create {model_name.lower()} table

Revision ID: {revision_id}
Revises: 
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create {model_name.lower()} table."""
    op.create_table(
        '{model_name.lower()}s',
        sa.Column('id', sa.Integer(), nullable=False),
{self._generate_migration_columns(fields, options.get('database', 'postgresql'))}
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
{self._generate_migration_indexes(fields, model_name)}
    
    # Create foreign key constraints
{self._generate_migration_foreign_keys(relationships, model_name)}


def downgrade() -> None:
    """Drop {model_name.lower()} table."""
    op.drop_table('{model_name.lower()}s')
'''
        
        return GeneratedFile(
            path=f"migrations/versions/{timestamp}_{revision_id}.py",
            content=content,
            language="python"
        )
    
    def _generate_comprehensive_tests(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate comprehensive test suite."""
        files = []
        
        # Unit tests
        unit_tests = self._generate_unit_tests(model_name, fields, relationships, options)
        files.append(unit_tests)
        
        # Integration tests
        integration_tests = self._generate_integration_tests(model_name, fields, relationships, options)
        files.append(integration_tests)
        
        # Performance tests
        if options.get('generate_performance_tests', False):
            performance_tests = self._generate_performance_tests(model_name, fields, relationships, options)
            files.append(performance_tests)
        
        return files
    
    def _generate_documentation(self, model_name: str, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], options: Dict[str, Any]) -> GeneratedFile:
        """Generate comprehensive documentation."""
        content = f'''# {model_name} API Documentation

## Overview

The {model_name} API provides comprehensive CRUD operations for managing {model_name.lower()} resources.

## Model Schema

### Fields

{self._generate_field_documentation(fields)}

### Relationships

{self._generate_relationship_documentation(relationships)}

## API Endpoints

### Create {model_name}

**POST** `/{model_name.lower()}s/`

Creates a new {model_name.lower()} instance.

**Request Body:**
```json
{self._generate_example_json(fields, relationships, exclude_auto=True)}
```

**Response:**
```json
{self._generate_example_json(fields, relationships, include_id=True)}
```

### Get {model_name}

**GET** `/{model_name.lower()}s/{{id}}`

Retrieves a specific {model_name.lower()} by ID.

**Response:**
```json
{self._generate_example_json(fields, relationships, include_id=True)}
```

### List {model_name}s

**GET** `/{model_name.lower()}s/`

Retrieves a paginated list of {model_name.lower()}s.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `size` (int): Page size (default: 10, max: 100)
- `sort_by` (str): Field to sort by
- `sort_order` (str): Sort order (asc/desc)
- `search` (str): Search query

**Response:**
```json
{{
  "items": [{self._generate_example_json(fields, relationships, include_id=True)}],
  "total": 100,
  "page": 1,
  "size": 10,
  "pages": 10
}}
```

### Update {model_name}

**PUT** `/{model_name.lower()}s/{{id}}`

Updates a specific {model_name.lower()}.

**Request Body:**
```json
{self._generate_example_json(fields, relationships, exclude_auto=True, optional=True)}
```

**Response:**
```json
{self._generate_example_json(fields, relationships, include_id=True)}
```

### Delete {model_name}

**DELETE** `/{model_name.lower()}s/{{id}}`

Deletes a specific {model_name.lower()}.

**Response:** 204 No Content

## Advanced Operations

### Bulk Create

**POST** `/{model_name.lower()}s/bulk`

Creates multiple {model_name.lower()} instances.

### Bulk Update

**PUT** `/{model_name.lower()}s/bulk`

Updates multiple {model_name.lower()} instances.

### Export Data

**GET** `/{model_name.lower()}s/export`

Exports {model_name.lower()} data in various formats (CSV, JSON, Excel).

## Error Responses

All endpoints may return the following error responses:

- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server error

## Rate Limiting

API requests are rate limited to 1000 requests per hour per user.

## Authentication

All endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```
'''
        
        return GeneratedFile(
            path=f"docs/{model_name.lower()}_api.md",
            content=content,
            language="markdown"
        )
    
    # Helper methods for code generation
    def _generate_field_imports(self, fields: List[Dict[str, Any]]) -> str:
        """Generate imports based on field types."""
        imports = []
        field_types = {field['type'] for field in fields}
        
        if 'email' in field_types:
            imports.append("from pydantic import EmailStr")
        if 'url' in field_types:
            imports.append("from pydantic import HttpUrl")
        
        return '\n'.join(imports)
    
    def _generate_create_fields(self, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> str:
        """Generate fields for create model."""
        field_definitions = []
        
        for field in fields:
            if field.get('auto_generated', False):
                continue
                
            field_name = field['name']
            field_type = self._map_field_type(field['type'])
            field_optional = field.get('optional', False)
            field_description = field.get('description', '')
            
            if field_optional:
                field_type = f"Optional[{field_type}]"
            
            field_def = f"    {field_name}: {field_type}"
            
            # Add Field with constraints
            field_attrs = []
            if field_description:
                field_attrs.append(f'description="{field_description}"')
            
            # Add constraints
            constraints = field.get('constraints', {})
            if 'max_length' in constraints:
                field_attrs.append(f'max_length={constraints["max_length"]}')
            if 'min_length' in constraints:
                field_attrs.append(f'min_length={constraints["min_length"]}')
            if 'min_value' in constraints:
                field_attrs.append(f'ge={constraints["min_value"]}')
            if 'max_value' in constraints:
                field_attrs.append(f'le={constraints["max_value"]}')
            
            if field.get('default') is not None:
                field_attrs.append(f'default={repr(field["default"])}')
            elif field_optional:
                field_attrs.append('default=None')
            else:
                field_attrs.append('...')
            
            if field_attrs:
                field_def += f" = Field({', '.join(field_attrs)})"
            
            field_definitions.append(field_def)
        
        return '\n'.join(field_definitions)
    
    def _generate_update_fields(self, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> str:
        """Generate fields for update model."""
        field_definitions = []
        
        for field in fields:
            if field.get('auto_generated', False) or field.get('immutable', False):
                continue
                
            field_name = field['name']
            field_type = self._map_field_type(field['type'])
            field_description = field.get('description', '')
            
            field_type = f"Optional[{field_type}]"
            field_def = f"    {field_name}: {field_type}"
            
            # Add Field with constraints
            field_attrs = ['default=None']
            if field_description:
                field_attrs.append(f'description="{field_description}"')
            
            # Add constraints
            constraints = field.get('constraints', {})
            if 'max_length' in constraints:
                field_attrs.append(f'max_length={constraints["max_length"]}')
            if 'min_length' in constraints:
                field_attrs.append(f'min_length={constraints["min_length"]}')
            if 'min_value' in constraints:
                field_attrs.append(f'ge={constraints["min_value"]}')
            if 'max_value' in constraints:
                field_attrs.append(f'le={constraints["max_value"]}')
            
            field_def += f" = Field({', '.join(field_attrs)})"
            field_definitions.append(field_def)
        
        return '\n'.join(field_definitions)
    
    def _generate_response_fields(self, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> str:
        """Generate fields for response model."""
        field_definitions = []
        
        for field in fields:
            field_name = field['name']
            field_type = self._map_field_type(field['type'])
            field_optional = field.get('optional', False)
            field_description = field.get('description', '')
            
            if field_optional:
                field_type = f"Optional[{field_type}]"
            
            field_def = f"    {field_name}: {field_type}"
            
            field_attrs = []
            if field_description:
                field_attrs.append(f'description="{field_description}"')
            
            if field_optional:
                field_attrs.append('default=None')
            else:
                field_attrs.append('...')
            
            if field_attrs:
                field_def += f" = Field({', '.join(field_attrs)})"
            
            field_definitions.append(field_def)
        
        return '\n'.join(field_definitions)
    
    def _generate_validators(self, fields: List[Dict[str, Any]], model_name: str) -> str:
        """Generate Pydantic validators."""
        validators = []
        
        for field in fields:
            if 'validation' in field:
                validation = field['validation']
                field_name = field['name']
                
                if validation.get('custom_validator'):
                    validator_code = f'''
    @validator('{field_name}')
    def validate_{field_name}(cls, v):
        """Custom validation for {field_name}."""
        {validation['custom_validator']}
        return v'''
                    validators.append(validator_code)
        
        return '\n'.join(validators)
    
    def _generate_example_data(self, fields: List[Dict[str, Any]], relationships: List[Dict[str, Any]], exclude_auto: bool = False, optional: bool = False, include_id: bool = False) -> str:
        """Generate example data for schemas."""
        example = {}
        
        if include_id:
            example['id'] = 1
        
        for field in fields:
            if exclude_auto and field.get('auto_generated', False):
                continue
                
            field_name = field['name']
            field_type = field['type']
            
            if optional and field.get('optional', False):
                continue
            
            # Generate example values based on field type
            if field_type == 'string':
                example[field_name] = f"example_{field_name}"
            elif field_type == 'text':
                example[field_name] = f"Example {field_name} content"
            elif field_type == 'integer':
                example[field_name] = 42
            elif field_type == 'float':
                example[field_name] = 3.14
            elif field_type == 'boolean':
                example[field_name] = True
            elif field_type == 'datetime':
                example[field_name] = "2023-01-01T00:00:00Z"
            elif field_type == 'date':
                example[field_name] = "2023-01-01"
            elif field_type == 'time':
                example[field_name] = "12:00:00"
            elif field_type == 'email':
                example[field_name] = "user@example.com"
            elif field_type == 'url':
                example[field_name] = "https://example.com"
            elif field_type == 'uuid':
                example[field_name] = "123e4567-e89b-12d3-a456-426614174000"
            elif field_type == 'json':
                example[field_name] = {"key": "value"}
            elif field_type == 'list':
                example[field_name] = ["item1", "item2"]
        
        if include_id:
            example['created_at'] = "2023-01-01T00:00:00Z"
            example['updated_at'] = "2023-01-01T12:00:00Z"
        
        return str(example).replace("'", '"')
    
    def _map_field_type(self, field_type: str) -> str:
        """Map field type to Python type."""
        return self.supported_field_types.get(field_type, 'str')
    
    def _get_test_value(self, field: Dict[str, Any], updated: bool = False) -> str:
        """Get test value for field."""
        field_type = field['type']
        field_name = field['name']
        
        if field_type in ['string', 'text']:
            return f'"test_{field_name}{"_updated" if updated else ""}"'
        elif field_type == 'integer':
            return '42' if not updated else '43'
        elif field_type == 'float':
            return '3.14' if not updated else '2.71'
        elif field_type == 'boolean':
            return 'true' if not updated else 'false'
        elif field_type == 'email':
            return '"test@example.com"' if not updated else '"updated@example.com"'
        elif field_type == 'url':
            return '"https://example.com"' if not updated else '"https://updated.com"'
        else:
            return f'"test_value{"_updated" if updated else ""}"'


class GeneratorRegistry:
    """Registry for managing code generators."""
    
    def __init__(self):
        self.generators: Dict[str, CodeGenerator] = {}
        self._register_builtin_generators()
    
    def _register_builtin_generators(self):
        """Register built-in generators."""
        self.register_generator("crud", CRUDGenerator())
        self.register_generator("advanced_crud", AdvancedCRUDGenerator())
        self.register_generator("api", APIGenerator())
        self.register_generator("advanced_api", AdvancedAPIGenerator())
        self.register_generator("model", ModelGenerator())
    
    def register_generator(self, name: str, generator: CodeGenerator):
        """Register a code generator."""
        self.generators[name] = generator
    
    def get_generator(self, name: str) -> Optional[CodeGenerator]:
        """Get a registered generator."""
        return self.generators.get(name)
    
    def list_generators(self) -> List[str]:
        """List all registered generator names."""
        return list(self.generators.keys())
    
    def generate(self, generator_name: str, schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate code using specified generator."""
        generator = self.get_generator(generator_name)
        if not generator:
            raise GenerationError(
                generator_type=generator_name,
                error_message=f"Generator '{generator_name}' not found"
            )
        
        return generator.generate(schema, options)


# Global generator registry
generator_registry = GeneratorRegistry()
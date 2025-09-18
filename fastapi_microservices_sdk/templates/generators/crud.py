"""
Advanced CRUD Generator

Generates comprehensive CRUD operations with repository pattern,
validation, and advanced features.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from .base import CodeGenerator, GeneratedFile, GenerationResult


class FieldType(Enum):
    """Supported field types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    JSON = "json"
    TEXT = "text"
    EMAIL = "email"
    URL = "url"


@dataclass
class FieldDefinition:
    """Definition of a model field"""
    name: str
    type: FieldType
    required: bool = True
    default: Any = None
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    description: Optional[str] = None
    unique: bool = False
    indexed: bool = False
    foreign_key: Optional[str] = None
    
    def to_pydantic_type(self) -> str:
        """Convert to Pydantic type annotation"""
        type_mapping = {
            FieldType.STRING: "str",
            FieldType.INTEGER: "int", 
            FieldType.FLOAT: "float",
            FieldType.BOOLEAN: "bool",
            FieldType.DATE: "date",
            FieldType.DATETIME: "datetime",
            FieldType.UUID: "UUID",
            FieldType.JSON: "Dict[str, Any]",
            FieldType.TEXT: "str",
            FieldType.EMAIL: "EmailStr",
            FieldType.URL: "HttpUrl"
        }
        
        base_type = type_mapping.get(self.type, "str")
        
        if not self.required:
            base_type = f"Optional[{base_type}]"
            
        return base_type
    
    def to_sqlalchemy_column(self) -> str:
        """Convert to SQLAlchemy column definition"""
        type_mapping = {
            FieldType.STRING: f"String({self.max_length or 255})",
            FieldType.INTEGER: "Integer",
            FieldType.FLOAT: "Float", 
            FieldType.BOOLEAN: "Boolean",
            FieldType.DATE: "Date",
            FieldType.DATETIME: "DateTime",
            FieldType.UUID: "UUID",
            FieldType.JSON: "JSON",
            FieldType.TEXT: "Text",
            FieldType.EMAIL: f"String({self.max_length or 255})",
            FieldType.URL: f"String({self.max_length or 500})"
        }
        
        column_type = type_mapping.get(self.type, "String(255)")
        
        options = []
        if not self.required:
            options.append("nullable=True")
        if self.unique:
            options.append("unique=True")
        if self.indexed:
            options.append("index=True")
        if self.foreign_key:
            options.append(f"ForeignKey('{self.foreign_key}')")
            
        options_str = ", ".join(options)
        if options_str:
            return f"Column({column_type}, {options_str})"
        else:
            return f"Column({column_type})"


@dataclass
class ModelDefinition:
    """Definition of a data model"""
    name: str
    fields: List[FieldDefinition]
    table_name: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if not self.table_name:
            # Convert CamelCase to snake_case
            import re
            self.table_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', self.name).lower()


class AdvancedCRUDGenerator(CodeGenerator):
    """Advanced CRUD operations generator"""
    
    def __init__(self):
        super().__init__(
            name="AdvancedCRUDGenerator",
            description="Generates comprehensive CRUD operations with repository pattern"
        )
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate CRUD generator configuration"""
        errors = []
        
        if "models" not in config:
            errors.append("Missing 'models' configuration")
            return errors
        
        models = config["models"]
        if not isinstance(models, list):
            errors.append("'models' must be a list")
            return errors
        
        for i, model in enumerate(models):
            if not isinstance(model, dict):
                errors.append(f"Model {i} must be a dictionary")
                continue
                
            if "name" not in model:
                errors.append(f"Model {i} missing 'name'")
            
            if "fields" not in model:
                errors.append(f"Model {i} missing 'fields'")
                continue
                
            fields = model["fields"]
            if not isinstance(fields, list):
                errors.append(f"Model {i} 'fields' must be a list")
                continue
                
            for j, field in enumerate(fields):
                if not isinstance(field, dict):
                    errors.append(f"Model {i} field {j} must be a dictionary")
                    continue
                    
                if "name" not in field:
                    errors.append(f"Model {i} field {j} missing 'name'")
                if "type" not in field:
                    errors.append(f"Model {i} field {j} missing 'type'")
        
        return errors
    
    def generate(self, config: Dict[str, Any], output_path: Path) -> GenerationResult:
        """Generate CRUD operations"""
        self.log_generation_start(config)
        
        # Validate configuration
        errors = self.validate_config(config)
        if errors:
            return GenerationResult(
                files=[],
                success=False,
                errors=errors,
                warnings=[]
            )
        
        files = []
        warnings = []
        
        try:
            # Parse models
            models = self._parse_models(config["models"])
            
            # Generate files for each model
            for model in models:
                model_files = self._generate_model_files(model, config)
                files.extend(model_files)
            
            # Generate common files
            common_files = self._generate_common_files(models, config)
            files.extend(common_files)
            
            result = GenerationResult(
                files=files,
                success=True,
                errors=[],
                warnings=warnings
            )
            
        except Exception as e:
            result = GenerationResult(
                files=[],
                success=False,
                errors=[str(e)],
                warnings=warnings
            )
        
        self.log_generation_complete(result)
        return result
    
    def _parse_models(self, models_config: List[Dict[str, Any]]) -> List[ModelDefinition]:
        """Parse model configurations"""
        models = []
        
        for model_config in models_config:
            fields = []
            
            for field_config in model_config["fields"]:
                field = FieldDefinition(
                    name=field_config["name"],
                    type=FieldType(field_config["type"]),
                    required=field_config.get("required", True),
                    default=field_config.get("default"),
                    max_length=field_config.get("max_length"),
                    min_length=field_config.get("min_length"),
                    description=field_config.get("description"),
                    unique=field_config.get("unique", False),
                    indexed=field_config.get("indexed", False),
                    foreign_key=field_config.get("foreign_key")
                )
                fields.append(field)
            
            model = ModelDefinition(
                name=model_config["name"],
                fields=fields,
                table_name=model_config.get("table_name"),
                description=model_config.get("description")
            )
            models.append(model)
        
        return models
    
    def _generate_model_files(self, model: ModelDefinition, config: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate files for a single model"""
        files = []
        
        # Generate model file
        model_content = self._generate_model_class(model)
        files.append(self.create_file(
            f"app/models/{model.name.lower()}.py",
            model_content
        ))
        
        # Generate schema file
        schema_content = self._generate_schema_classes(model)
        files.append(self.create_file(
            f"app/schemas/{model.name.lower()}.py", 
            schema_content
        ))
        
        # Generate repository file
        repository_content = self._generate_repository_class(model)
        files.append(self.create_file(
            f"app/repositories/{model.name.lower()}.py",
            repository_content
        ))
        
        # Generate service file
        service_content = self._generate_service_class(model)
        files.append(self.create_file(
            f"app/services/{model.name.lower()}.py",
            service_content
        ))
        
        # Generate API router file
        router_content = self._generate_router_class(model)
        files.append(self.create_file(
            f"app/api/v1/{model.name.lower()}.py",
            router_content
        ))
        
        return files
    
    def _generate_common_files(self, models: List[ModelDefinition], config: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate common files"""
        files = []
        
        # Generate __init__.py files
        init_files = [
            "app/__init__.py",
            "app/models/__init__.py", 
            "app/schemas/__init__.py",
            "app/repositories/__init__.py",
            "app/services/__init__.py",
            "app/api/__init__.py",
            "app/api/v1/__init__.py"
        ]
        
        for init_file in init_files:
            files.append(self.create_file(init_file, ""))
        
        return files
    
    def _generate_model_class(self, model: ModelDefinition) -> str:
        """Generate SQLAlchemy model class"""
        template = '''"""
{{ model.name }} model

{{ model.description or "Generated model for " + model.name }}
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, Date, JSON, UUID, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class {{ model.name }}(Base):
    """{{ model.description or model.name + " model" }}"""
    
    __tablename__ = "{{ model.table_name }}"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Fields
{% for field in model.fields %}
    {{ field.name }} = {{ field.to_sqlalchemy_column() }}{% if field.description %}  # {{ field.description }}{% endif %}
{% endfor %}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<{{ model.name }}(id={self.id})>"
'''
        
        return self.render_template(template, {"model": model})
    
    def _generate_schema_classes(self, model: ModelDefinition) -> str:
        """Generate Pydantic schema classes"""
        template = '''"""
{{ model.name }} schemas

Pydantic models for {{ model.name }} serialization and validation.
"""

from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID


class {{ model.name }}Base(BaseModel):
    """Base {{ model.name }} schema"""
    
{% for field in model.fields %}
    {{ field.name }}: {{ field.to_pydantic_type() }}{% if field.description %} = Field(..., description="{{ field.description }}"){% endif %}
{% endfor %}


class {{ model.name }}Create({{ model.name }}Base):
    """Schema for creating {{ model.name }}"""
    pass


class {{ model.name }}Update(BaseModel):
    """Schema for updating {{ model.name }}"""
    
{% for field in model.fields %}
    {{ field.name }}: Optional[{{ field.to_pydantic_type().replace("Optional[", "").replace("]", "") }}] = None
{% endfor %}


class {{ model.name }}InDB({{ model.name }}Base):
    """Schema for {{ model.name }} in database"""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class {{ model.name }}Response({{ model.name }}InDB):
    """Schema for {{ model.name }} API response"""
    pass
'''
        
        return self.render_template(template, {"model": model})
    
    def _generate_repository_class(self, model: ModelDefinition) -> str:
        """Generate repository class"""
        template = '''"""
{{ model.name }} repository

Data access layer for {{ model.name }} operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.{{ model.name.lower() }} import {{ model.name }}
from app.schemas.{{ model.name.lower() }} import {{ model.name }}Create, {{ model.name }}Update


class {{ model.name }}Repository:
    """Repository for {{ model.name }} operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get(self, id: int) -> Optional[{{ model.name }}]:
        """Get {{ model.name }} by ID"""
        return self.db.query({{ model.name }}).filter({{ model.name }}.id == id).first()
    
    def get_multi(self, skip: int = 0, limit: int = 100) -> List[{{ model.name }}]:
        """Get multiple {{ model.name }} records"""
        return self.db.query({{ model.name }}).offset(skip).limit(limit).all()
    
    def create(self, obj_in: {{ model.name }}Create) -> {{ model.name }}:
        """Create new {{ model.name }}"""
        db_obj = {{ model.name }}(**obj_in.dict())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, db_obj: {{ model.name }}, obj_in: {{ model.name }}Update) -> {{ model.name }}:
        """Update {{ model.name }}"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: int) -> Optional[{{ model.name }}]:
        """Delete {{ model.name }}"""
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
        return db_obj
    
    def search(self, query: str, skip: int = 0, limit: int = 100) -> List[{{ model.name }}]:
        """Search {{ model.name }} records"""
        # Add search logic based on model fields
        return self.db.query({{ model.name }}).offset(skip).limit(limit).all()
    
    def count(self) -> int:
        """Count total {{ model.name }} records"""
        return self.db.query({{ model.name }}).count()
'''
        
        return self.render_template(template, {"model": model})
    
    def _generate_service_class(self, model: ModelDefinition) -> str:
        """Generate service class"""
        template = '''"""
{{ model.name }} service

Business logic layer for {{ model.name }} operations.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.{{ model.name.lower() }} import {{ model.name }}Repository
from app.schemas.{{ model.name.lower() }} import {{ model.name }}Create, {{ model.name }}Update, {{ model.name }}Response
from app.models.{{ model.name.lower() }} import {{ model.name }}


class {{ model.name }}Service:
    """Service for {{ model.name }} business logic"""
    
    def __init__(self, db: Session):
        self.repository = {{ model.name }}Repository(db)
    
    def get_{{ model.name.lower() }}(self, id: int) -> Optional[{{ model.name }}Response]:
        """Get {{ model.name }} by ID"""
        db_obj = self.repository.get(id)
        if db_obj:
            return {{ model.name }}Response.from_orm(db_obj)
        return None
    
    def get_{{ model.name.lower() }}s(self, skip: int = 0, limit: int = 100) -> List[{{ model.name }}Response]:
        """Get multiple {{ model.name }} records"""
        db_objs = self.repository.get_multi(skip=skip, limit=limit)
        return [{{ model.name }}Response.from_orm(obj) for obj in db_objs]
    
    def create_{{ model.name.lower() }}(self, obj_in: {{ model.name }}Create) -> {{ model.name }}Response:
        """Create new {{ model.name }}"""
        # Add business logic validation here
        db_obj = self.repository.create(obj_in)
        return {{ model.name }}Response.from_orm(db_obj)
    
    def update_{{ model.name.lower() }}(self, id: int, obj_in: {{ model.name }}Update) -> Optional[{{ model.name }}Response]:
        """Update {{ model.name }}"""
        db_obj = self.repository.get(id)
        if not db_obj:
            return None
        
        # Add business logic validation here
        updated_obj = self.repository.update(db_obj, obj_in)
        return {{ model.name }}Response.from_orm(updated_obj)
    
    def delete_{{ model.name.lower() }}(self, id: int) -> bool:
        """Delete {{ model.name }}"""
        db_obj = self.repository.delete(id)
        return db_obj is not None
    
    def search_{{ model.name.lower() }}s(self, query: str, skip: int = 0, limit: int = 100) -> List[{{ model.name }}Response]:
        """Search {{ model.name }} records"""
        db_objs = self.repository.search(query, skip=skip, limit=limit)
        return [{{ model.name }}Response.from_orm(obj) for obj in db_objs]
'''
        
        return self.render_template(template, {"model": model})
    
    def _generate_router_class(self, model: ModelDefinition) -> str:
        """Generate FastAPI router"""
        template = '''"""
{{ model.name }} API router

REST API endpoints for {{ model.name }} operations.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.services.{{ model.name.lower() }} import {{ model.name }}Service
from app.schemas.{{ model.name.lower() }} import {{ model.name }}Create, {{ model.name }}Update, {{ model.name }}Response
from app.core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[{{ model.name }}Response])
def get_{{ model.name.lower() }}s(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get multiple {{ model.name }} records"""
    service = {{ model.name }}Service(db)
    return service.get_{{ model.name.lower() }}s(skip=skip, limit=limit)


@router.get("/{id}", response_model={{ model.name }}Response)
def get_{{ model.name.lower() }}(id: int, db: Session = Depends(get_db)):
    """Get {{ model.name }} by ID"""
    service = {{ model.name }}Service(db)
    obj = service.get_{{ model.name.lower() }}(id)
    if not obj:
        raise HTTPException(status_code=404, detail="{{ model.name }} not found")
    return obj


@router.post("/", response_model={{ model.name }}Response, status_code=201)
def create_{{ model.name.lower() }}(obj_in: {{ model.name }}Create, db: Session = Depends(get_db)):
    """Create new {{ model.name }}"""
    service = {{ model.name }}Service(db)
    return service.create_{{ model.name.lower() }}(obj_in)


@router.put("/{id}", response_model={{ model.name }}Response)
def update_{{ model.name.lower() }}(id: int, obj_in: {{ model.name }}Update, db: Session = Depends(get_db)):
    """Update {{ model.name }}"""
    service = {{ model.name }}Service(db)
    obj = service.update_{{ model.name.lower() }}(id, obj_in)
    if not obj:
        raise HTTPException(status_code=404, detail="{{ model.name }} not found")
    return obj


@router.delete("/{id}")
def delete_{{ model.name.lower() }}(id: int, db: Session = Depends(get_db)):
    """Delete {{ model.name }}"""
    service = {{ model.name }}Service(db)
    success = service.delete_{{ model.name.lower() }}(id)
    if not success:
        raise HTTPException(status_code=404, detail="{{ model.name }} not found")
    return {"message": "{{ model.name }} deleted successfully"}


@router.get("/search/", response_model=List[{{ model.name }}Response])
def search_{{ model.name.lower() }}s(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Search {{ model.name }} records"""
    service = {{ model.name }}Service(db)
    return service.search_{{ model.name.lower() }}s(q, skip=skip, limit=limit)
'''
        
        return self.render_template(template, {"model": model})
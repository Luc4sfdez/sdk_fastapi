"""
Advanced API Generator

Comprehensive API generator from OpenAPI specifications with support for
multiple languages, client SDKs, and advanced features.
"""

from typing import Dict, Any, List, Optional, Union, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import json
import yaml
import re
from urllib.parse import urlparse

from ..exceptions import GenerationError
from .base import CodeGenerator, GeneratedFile, GenerationResult


@dataclass
class ParameterDefinition:
    """Parameter definition for API operations."""
    name: str
    type: str
    location: str  # "query", "path", "header", "cookie", "body"
    description: str = ""
    required: bool = True
    default: Any = None
    format: Optional[str] = None
    pattern: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    enum: Optional[List[Any]] = None
    
    def get_python_type(self) -> str:
        """Get Python type annotation."""
        type_mapping = {
            'string': 'str',
            'integer': 'int',
            'number': 'float',
            'boolean': 'bool',
            'array': 'List[str]',
            'object': 'Dict[str, Any]',
            'file': 'UploadFile'
        }
        
        base_type = type_mapping.get(self.type, 'str')
        
        if self.format:
            if self.format == 'date-time':
                base_type = 'datetime'
            elif self.format == 'date':
                base_type = 'date'
            elif self.format == 'uuid':
                base_type = 'UUID'
            elif self.format == 'email':
                base_type = 'EmailStr'
            elif self.format == 'uri':
                base_type = 'HttpUrl'
        
        if not self.required:
            return f'Optional[{base_type}]'
        
        return base_type
    
    def get_fastapi_param(self) -> str:
        """Get FastAPI parameter definition."""
        param_type = {
            'query': 'Query',
            'path': 'Path',
            'header': 'Header',
            'cookie': 'Cookie'
        }.get(self.location, 'Query')
        
        args = []
        
        if self.default is not None:
            args.append(f'default={repr(self.default)}')
        elif not self.required:
            args.append('default=None')
        
        if self.description:
            args.append(f'description="{self.description}"')
        
        if self.min_value is not None:
            args.append(f'ge={self.min_value}')
        
        if self.max_value is not None:
            args.append(f'le={self.max_value}')
        
        if self.min_length is not None:
            args.append(f'min_length={self.min_length}')
        
        if self.max_length is not None:
            args.append(f'max_length={self.max_length}')
        
        if self.pattern:
            args.append(f'regex="{self.pattern}"')
        
        args_str = f'({", ".join(args)})' if args else '()'
        return f'{param_type}{args_str}'


@dataclass
class ResponseDefinition:
    """Response definition for API operations."""
    status_code: int
    description: str = ""
    content_type: str = "application/json"
    schema: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def get_response_model(self) -> Optional[str]:
        """Get response model name."""
        if self.schema and '$ref' in self.schema:
            ref = self.schema['$ref']
            return ref.split('/')[-1]
        return None


@dataclass
class OperationDefinition:
    """API operation definition."""
    method: str
    path: str
    operation_id: str
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[ParameterDefinition] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: List[ResponseDefinition] = field(default_factory=list)
    security: List[Dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False
    
    def get_function_name(self) -> str:
        """Get Python function name from operation ID."""
        if self.operation_id:
            # Convert camelCase to snake_case
            name = re.sub(r'(?<!^)(?=[A-Z])', '_', self.operation_id).lower()
            return name
        
        # Generate from method and path
        path_parts = [part for part in self.path.split('/') if part and not part.startswith('{')]
        method_name = self.method.lower()
        
        if path_parts:
            return f"{method_name}_{'_'.join(path_parts)}"
        
        return method_name
    
    def get_path_parameters(self) -> List[ParameterDefinition]:
        """Get path parameters."""
        return [p for p in self.parameters if p.location == 'path']
    
    def get_query_parameters(self) -> List[ParameterDefinition]:
        """Get query parameters."""
        return [p for p in self.parameters if p.location == 'query']
    
    def get_header_parameters(self) -> List[ParameterDefinition]:
        """Get header parameters."""
        return [p for p in self.parameters if p.location == 'header']
    
    def get_request_model(self) -> Optional[str]:
        """Get request body model name."""
        if self.request_body and 'content' in self.request_body:
            content = self.request_body['content']
            for content_type, schema_info in content.items():
                if 'schema' in schema_info and '$ref' in schema_info['schema']:
                    ref = schema_info['schema']['$ref']
                    return ref.split('/')[-1]
        return None


@dataclass
class SchemaDefinition:
    """Schema definition for models."""
    name: str
    type: str
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    enum: Optional[List[Any]] = None
    additional_properties: bool = True
    
    def get_python_class_name(self) -> str:
        """Get Python class name."""
        # Convert to PascalCase
        return ''.join(word.capitalize() for word in re.split(r'[_\-\s]', self.name))


@dataclass
class APISpecification:
    """Complete API specification."""
    title: str
    version: str
    description: str = ""
    base_url: str = ""
    operations: List[OperationDefinition] = field(default_factory=list)
    schemas: List[SchemaDefinition] = field(default_factory=list)
    security_schemes: Dict[str, Any] = field(default_factory=dict)
    tags: List[Dict[str, str]] = field(default_factory=list)
    
    def get_unique_tags(self) -> Set[str]:
        """Get unique tags from operations."""
        tags = set()
        for operation in self.operations:
            tags.update(operation.tags)
        return tags


class OpenAPIParser:
    """Parser for OpenAPI specifications."""
    
    def parse(self, spec_data: Dict[str, Any]) -> APISpecification:
        """Parse OpenAPI specification."""
        try:
            # Basic info
            info = spec_data.get('info', {})
            api_spec = APISpecification(
                title=info.get('title', 'API'),
                version=info.get('version', '1.0.0'),
                description=info.get('description', ''),
                tags=spec_data.get('tags', [])
            )
            
            # Base URL
            servers = spec_data.get('servers', [])
            if servers:
                api_spec.base_url = servers[0].get('url', '')
            
            # Security schemes
            components = spec_data.get('components', {})
            api_spec.security_schemes = components.get('securitySchemes', {})
            
            # Parse schemas
            schemas = components.get('schemas', {})
            for schema_name, schema_data in schemas.items():
                schema_def = self._parse_schema(schema_name, schema_data)
                api_spec.schemas.append(schema_def)
            
            # Parse paths
            paths = spec_data.get('paths', {})
            for path, path_data in paths.items():
                for method, operation_data in path_data.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        operation = self._parse_operation(method.upper(), path, operation_data)
                        api_spec.operations.append(operation)
            
            return api_spec
            
        except Exception as e:
            raise GenerationError(
                generator_type="openapi_parser",
                error_message=f"Failed to parse OpenAPI specification: {str(e)}",
                context=spec_data
            )
    
    def _parse_schema(self, name: str, schema_data: Dict[str, Any]) -> SchemaDefinition:
        """Parse schema definition."""
        return SchemaDefinition(
            name=name,
            type=schema_data.get('type', 'object'),
            description=schema_data.get('description', ''),
            properties=schema_data.get('properties', {}),
            required=schema_data.get('required', []),
            enum=schema_data.get('enum'),
            additional_properties=schema_data.get('additionalProperties', True)
        )
    
    def _parse_operation(self, method: str, path: str, operation_data: Dict[str, Any]) -> OperationDefinition:
        """Parse operation definition."""
        operation = OperationDefinition(
            method=method,
            path=path,
            operation_id=operation_data.get('operationId', ''),
            summary=operation_data.get('summary', ''),
            description=operation_data.get('description', ''),
            tags=operation_data.get('tags', []),
            security=operation_data.get('security', []),
            deprecated=operation_data.get('deprecated', False)
        )
        
        # Parse parameters
        parameters = operation_data.get('parameters', [])
        for param_data in parameters:
            param = self._parse_parameter(param_data)
            operation.parameters.append(param)
        
        # Parse request body
        operation.request_body = operation_data.get('requestBody')
        
        # Parse responses
        responses = operation_data.get('responses', {})
        for status_code, response_data in responses.items():
            try:
                status_int = int(status_code)
                response = ResponseDefinition(
                    status_code=status_int,
                    description=response_data.get('description', ''),
                    headers=response_data.get('headers', {})
                )
                
                # Parse content
                content = response_data.get('content', {})
                for content_type, content_data in content.items():
                    response.content_type = content_type
                    response.schema = content_data.get('schema')
                    break  # Use first content type
                
                operation.responses.append(response)
            except ValueError:
                continue  # Skip non-numeric status codes like 'default'
        
        return operation
    
    def _parse_parameter(self, param_data: Dict[str, Any]) -> ParameterDefinition:
        """Parse parameter definition."""
        schema = param_data.get('schema', {})
        
        return ParameterDefinition(
            name=param_data.get('name', ''),
            type=schema.get('type', 'string'),
            location=param_data.get('in', 'query'),
            description=param_data.get('description', ''),
            required=param_data.get('required', False),
            default=schema.get('default'),
            format=schema.get('format'),
            pattern=schema.get('pattern'),
            min_value=schema.get('minimum'),
            max_value=schema.get('maximum'),
            min_length=schema.get('minLength'),
            max_length=schema.get('maxLength'),
            enum=schema.get('enum')
        )


class AdvancedAPIGenerator(CodeGenerator):
    """Advanced API generator from OpenAPI specifications."""
    
    def __init__(self):
        super().__init__("advanced_api_generator")
        self.parser = OpenAPIParser()
    
    def generate(self, schema: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> GenerationResult:
        """Generate API code from OpenAPI specification."""
        try:
            options = options or {}
            
            # Parse OpenAPI specification
            if 'openapi_spec' in schema:
                spec_data = schema['openapi_spec']
            elif 'spec_file' in schema:
                spec_data = self._load_spec_file(schema['spec_file'])
            else:
                spec_data = schema
            
            api_spec = self.parser.parse(spec_data)
            
            # Validate specification
            validation_errors = self.validate_schema(schema)
            if validation_errors:
                raise GenerationError(
                    generator_type=self.name,
                    error_message=f"API specification validation failed: {', '.join(validation_errors)}"
                )
            
            files = []
            
            # Generate Pydantic models
            models_file = self._generate_models(api_spec, options)
            files.append(models_file)
            
            # Generate FastAPI endpoints
            endpoints_files = self._generate_endpoints(api_spec, options)
            files.extend(endpoints_files)
            
            # Generate client SDKs
            if options.get('generate_clients', True):
                client_files = self._generate_clients(api_spec, options)
                files.extend(client_files)
            
            # Generate tests
            if options.get('generate_tests', True):
                test_files = self._generate_tests(api_spec, options)
                files.extend(test_files)
            
            # Generate documentation
            if options.get('generate_docs', True):
                docs_file = self._generate_documentation(api_spec, options)
                files.append(docs_file)
            
            return GenerationResult(
                files=files,
                metadata={
                    'generator': self.name,
                    'api_title': api_spec.title,
                    'api_version': api_spec.version,
                    'operations_count': len(api_spec.operations),
                    'schemas_count': len(api_spec.schemas),
                    'generated_at': datetime.now().isoformat(),
                    'features': {
                        'clients_generated': options.get('generate_clients', True),
                        'tests_generated': options.get('generate_tests', True),
                        'docs_generated': options.get('generate_docs', True)
                    }
                }
            )
            
        except Exception as e:
            raise GenerationError(
                generator_type=self.name,
                error_message=str(e),
                context=schema
            )
    
    def _load_spec_file(self, file_path: str) -> Dict[str, Any]:
        """Load OpenAPI specification from file."""
        try:
            path = Path(file_path)
            content = path.read_text(encoding='utf-8')
            
            if path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            else:
                return json.loads(content)
                
        except Exception as e:
            raise GenerationError(
                generator_type=self.name,
                error_message=f"Failed to load specification file: {str(e)}"
            )
    
    def validate_schema(self, schema: Dict[str, Any]) -> List[str]:
        """Validate OpenAPI specification."""
        errors = []
        
        # Check for required OpenAPI fields
        spec_data = schema.get('openapi_spec', schema)
        
        if 'openapi' not in spec_data and 'swagger' not in spec_data:
            errors.append("Missing OpenAPI or Swagger version")
        
        if 'info' not in spec_data:
            errors.append("Missing API info section")
        else:
            info = spec_data['info']
            if 'title' not in info:
                errors.append("Missing API title")
            if 'version' not in info:
                errors.append("Missing API version")
        
        if 'paths' not in spec_data or not spec_data['paths']:
            errors.append("No API paths defined")
        
        return errors
    
    def _generate_models(self, api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate Pydantic models from schemas."""
        imports = [
            "from typing import Optional, List, Dict, Any, Union",
            "from pydantic import BaseModel, Field, validator",
            "from datetime import datetime, date",
            "from uuid import UUID",
            "from enum import Enum"
        ]
        
        # Check for special types
        has_email = any('email' in str(schema.properties) for schema in api_spec.schemas)
        has_url = any('uri' in str(schema.properties) for schema in api_spec.schemas)
        
        if has_email:
            imports.append("from pydantic import EmailStr")
        if has_url:
            imports.append("from pydantic import HttpUrl")
        
        models = []
        
        # Generate enum classes
        for schema in api_spec.schemas:
            if schema.enum:
                enum_class = self._generate_enum_class(schema)
                models.append(enum_class)
        
        # Generate model classes
        for schema in api_spec.schemas:
            if not schema.enum:
                model_class = self._generate_model_class(schema)
                models.append(model_class)
        
        content = f'''"""
{api_spec.title} API Models

Generated Pydantic models from OpenAPI specification.
Version: {api_spec.version}
"""

{chr(10).join(imports)}


{chr(10).join(models)}
'''
        
        return GeneratedFile(
            path="models/api_models.py",
            content=content,
            language="python"
        )
    
    def _generate_enum_class(self, schema: SchemaDefinition) -> str:
        """Generate enum class."""
        class_name = schema.get_python_class_name()
        
        enum_values = []
        for value in schema.enum:
            # Convert value to valid Python identifier
            name = str(value).upper().replace('-', '_').replace(' ', '_')
            name = re.sub(r'[^A-Z0-9_]', '', name)
            enum_values.append(f'    {name} = "{value}"')
        
        return f'''class {class_name}(str, Enum):
    """{schema.description or f'{class_name} enumeration'}"""
{chr(10).join(enum_values)}
'''
    
    def _generate_model_class(self, schema: SchemaDefinition) -> str:
        """Generate Pydantic model class."""
        class_name = schema.get_python_class_name()
        
        fields = []
        validators = []
        
        for prop_name, prop_data in schema.properties.items():
            field_def = self._generate_model_field(prop_name, prop_data, prop_name in schema.required)
            fields.append(field_def)
            
            # Generate validators if needed
            if 'pattern' in prop_data:
                validator_code = f'''
    @validator('{prop_name}')
    def validate_{prop_name}(cls, v):
        import re
        if v and not re.match(r'{prop_data["pattern"]}', v):
            raise ValueError('Invalid {prop_name} format')
        return v'''
                validators.append(validator_code)
        
        fields_str = '\n'.join(fields) if fields else '    pass'
        validators_str = ''.join(validators)
        
        return f'''class {class_name}(BaseModel):
    """{schema.description or f'{class_name} model'}"""
{fields_str}{validators_str}

    class Config:
        from_attributes = True
        json_encoders = {{
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }}
'''
    
    def _generate_model_field(self, name: str, prop_data: Dict[str, Any], required: bool) -> str:
        """Generate model field definition."""
        # Determine Python type
        prop_type = prop_data.get('type', 'string')
        prop_format = prop_data.get('format')
        
        type_mapping = {
            'string': 'str',
            'integer': 'int',
            'number': 'float',
            'boolean': 'bool',
            'array': 'List[str]',  # Simplified
            'object': 'Dict[str, Any]'
        }
        
        python_type = type_mapping.get(prop_type, 'str')
        
        # Handle formats
        if prop_format:
            if prop_format == 'date-time':
                python_type = 'datetime'
            elif prop_format == 'date':
                python_type = 'date'
            elif prop_format == 'uuid':
                python_type = 'UUID'
            elif prop_format == 'email':
                python_type = 'EmailStr'
            elif prop_format == 'uri':
                python_type = 'HttpUrl'
        
        # Handle references
        if '$ref' in prop_data:
            ref_name = prop_data['$ref'].split('/')[-1]
            python_type = ref_name
        
        # Handle arrays with items
        if prop_type == 'array' and 'items' in prop_data:
            items = prop_data['items']
            if '$ref' in items:
                item_type = items['$ref'].split('/')[-1]
            else:
                item_type = type_mapping.get(items.get('type', 'string'), 'str')
            python_type = f'List[{item_type}]'
        
        # Make optional if not required
        if not required:
            python_type = f'Optional[{python_type}]'
        
        # Generate Field parameters
        field_args = []
        
        if 'description' in prop_data:
            field_args.append(f'description="{prop_data["description"]}"')
        
        if 'default' in prop_data:
            default_val = prop_data['default']
            if isinstance(default_val, str):
                field_args.append(f'default="{default_val}"')
            else:
                field_args.append(f'default={default_val}')
        elif not required:
            field_args.append('default=None')
        
        if 'minimum' in prop_data:
            field_args.append(f'ge={prop_data["minimum"]}')
        
        if 'maximum' in prop_data:
            field_args.append(f'le={prop_data["maximum"]}')
        
        if 'minLength' in prop_data:
            field_args.append(f'min_length={prop_data["minLength"]}')
        
        if 'maxLength' in prop_data:
            field_args.append(f'max_length={prop_data["maxLength"]}')
        
        # Generate field definition
        if field_args:
            field_def = f' = Field({", ".join(field_args)})'
        else:
            field_def = ''
        
        return f'    {name}: {python_type}{field_def}'
    
    def _generate_endpoints(self, api_spec: APISpecification, options: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate FastAPI endpoints."""
        files = []
        
        # Group operations by tags
        operations_by_tag = {}
        for operation in api_spec.operations:
            tags = operation.tags or ['default']
            for tag in tags:
                if tag not in operations_by_tag:
                    operations_by_tag[tag] = []
                operations_by_tag[tag].append(operation)
        
        # Generate router file for each tag
        for tag, operations in operations_by_tag.items():
            router_file = self._generate_router_file(tag, operations, api_spec, options)
            files.append(router_file)
        
        # Generate main app file
        main_file = self._generate_main_app(api_spec, list(operations_by_tag.keys()), options)
        files.append(main_file)
        
        return files
    
    def _generate_router_file(self, tag: str, operations: List[OperationDefinition], 
                             api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate FastAPI router file for a tag."""
        router_name = tag.lower().replace(' ', '_').replace('-', '_')
        
        imports = [
            "from typing import List, Optional, Dict, Any",
            "from fastapi import APIRouter, Depends, HTTPException, Query, Path, Header, Body, status",
            "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials",
            "from pydantic import BaseModel",
            "",
            "from ..models.api_models import *",
            "from ..dependencies import get_current_user, get_db",
            "from ..services import *"
        ]
        
        # Generate router
        router_def = f'''
router = APIRouter(
    prefix="/{router_name}",
    tags=["{tag}"],
    responses={{404: {{"description": "Not found"}}}}
)
'''
        
        # Generate endpoint functions
        endpoints = []
        for operation in operations:
            endpoint_func = self._generate_endpoint_function(operation, api_spec)
            endpoints.append(endpoint_func)
        
        content = f'''"""
{tag.title()} API Router

Generated FastAPI router for {tag} operations.
"""

{chr(10).join(imports)}

{router_def}

{chr(10).join(endpoints)}
'''
        
        return GeneratedFile(
            path=f"routers/{router_name}.py",
            content=content,
            language="python"
        )
    
    def _generate_endpoint_function(self, operation: OperationDefinition, api_spec: APISpecification) -> str:
        """Generate FastAPI endpoint function."""
        func_name = operation.get_function_name()
        
        # Generate function parameters
        params = []
        
        # Path parameters
        for param in operation.get_path_parameters():
            param_type = param.get_python_type()
            fastapi_param = param.get_fastapi_param()
            params.append(f'{param.name}: {param_type} = {fastapi_param}')
        
        # Query parameters
        for param in operation.get_query_parameters():
            param_type = param.get_python_type()
            fastapi_param = param.get_fastapi_param()
            params.append(f'{param.name}: {param_type} = {fastapi_param}')
        
        # Header parameters
        for param in operation.get_header_parameters():
            param_type = param.get_python_type()
            fastapi_param = param.get_fastapi_param()
            params.append(f'{param.name}: {param_type} = {fastapi_param}')
        
        # Request body
        request_model = operation.get_request_model()
        if request_model:
            params.append(f'request_data: {request_model}')
        
        # Dependencies
        if operation.security:
            params.append('current_user = Depends(get_current_user)')
        
        params.append('db = Depends(get_db)')
        
        # Generate response model
        success_responses = [r for r in operation.responses if 200 <= r.status_code < 300]
        response_model = None
        if success_responses:
            response_model = success_responses[0].get_response_model()
        
        # Generate decorator
        decorator_args = [f'"{operation.path}"']
        
        if response_model:
            decorator_args.append(f'response_model={response_model}')
        
        if operation.summary:
            decorator_args.append(f'summary="{operation.summary}"')
        
        if operation.description:
            decorator_args.append(f'description="{operation.description}"')
        
        # Generate status code responses
        status_responses = {}
        for response in operation.responses:
            if response.status_code != 200:
                status_responses[response.status_code] = {"description": response.description}
        
        if status_responses:
            decorator_args.append(f'responses={status_responses}')
        
        decorator = f'@router.{operation.method.lower()}({", ".join(decorator_args)})'
        
        # Generate function signature
        params_str = ',\n    '.join(params) if params else ''
        if params_str:
            params_str = f'\n    {params_str}\n'
        
        return_type = response_model or 'Dict[str, Any]'
        
        # Generate function body
        body_lines = [
            '    """',
            f'    {operation.summary or f"{operation.method} {operation.path}"}',
            ''
        ]
        
        if operation.description:
            body_lines.extend([
                f'    {operation.description}',
                ''
            ])
        
        body_lines.extend([
            '    """',
            '    try:',
            '        # TODO: Implement business logic',
            f'        # This is a generated endpoint for {operation.method} {operation.path}',
            '        pass',
            '    except Exception as e:',
            '        raise HTTPException(',
            '            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,',
            '            detail=str(e)',
            '        )'
        ])
        
        return f'''{decorator}
async def {func_name}({params_str}) -> {return_type}:
{chr(10).join(body_lines)}
'''
    
    def _generate_main_app(self, api_spec: APISpecification, tags: List[str], options: Dict[str, Any]) -> GeneratedFile:
        """Generate main FastAPI application."""
        router_imports = []
        router_includes = []
        
        for tag in tags:
            router_name = tag.lower().replace(' ', '_').replace('-', '_')
            router_imports.append(f'from .routers import {router_name}')
            router_includes.append(f'app.include_router({router_name}.router)')
        
        content = f'''"""
{api_spec.title} FastAPI Application

Generated FastAPI application from OpenAPI specification.
Version: {api_spec.version}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

{chr(10).join(router_imports)}

app = FastAPI(
    title="{api_spec.title}",
    description="{api_spec.description}",
    version="{api_spec.version}"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{chr(10).join(router_includes)}


@app.get("/")
async def root():
    """Root endpoint."""
    return {{
        "message": "Welcome to {api_spec.title}",
        "version": "{api_spec.version}",
        "docs": "/docs"
    }}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        
        return GeneratedFile(
            path="main.py",
            content=content,
            language="python"
        )
    
    def _generate_clients(self, api_spec: APISpecification, options: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate client SDKs."""
        files = []
        
        # Generate Python client
        if options.get('generate_python_client', True):
            python_client = self._generate_python_client(api_spec, options)
            files.append(python_client)
        
        # Generate TypeScript client
        if options.get('generate_typescript_client', False):
            ts_client = self._generate_typescript_client(api_spec, options)
            files.append(ts_client)
        
        return files
    
    def _generate_python_client(self, api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate Python client SDK."""
        content = f'''"""
{api_spec.title} Python Client

Generated Python client SDK for {api_spec.title} API.
Version: {api_spec.version}
"""

import httpx
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin


class {api_spec.title.replace(' ', '')}Client:
    """Python client for {api_spec.title} API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        headers = {{"User-Agent": f"{api_spec.title.replace(' ', '')}-Python-Client/{api_spec.version}"}}
        if api_key:
            headers["Authorization"] = f"Bearer {{api_key}}"
        
        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
'''
        
        # Generate client methods for each operation
        for operation in api_spec.operations:
            method_code = self._generate_client_method(operation)
            content += f'\n{method_code}'
        
        return GeneratedFile(
            path=f"clients/{api_spec.title.lower().replace(' ', '_')}_client.py",
            content=content,
            language="python"
        )
    
    def _generate_client_method(self, operation: OperationDefinition) -> str:
        """Generate client method for an operation."""
        method_name = operation.get_function_name()
        
        # Generate parameters
        params = []
        path_params = []
        query_params = []
        
        for param in operation.parameters:
            param_type = param.get_python_type()
            
            if param.required:
                params.append(f'{param.name}: {param_type}')
            else:
                default = 'None' if param.default is None else repr(param.default)
                params.append(f'{param.name}: {param_type} = {default}')
            
            if param.location == 'path':
                path_params.append(param.name)
            elif param.location == 'query':
                query_params.append(param.name)
        
        # Add request body parameter
        request_model = operation.get_request_model()
        if request_model:
            params.append(f'data: {request_model}')
        
        # Generate method signature
        params_str = ', '.join(params)
        
        # Generate method body
        path_substitution = operation.path
        for param_name in path_params:
            path_substitution = path_substitution.replace(f'{{{param_name}}}', f'{{param_name}}')
        
        query_building = []
        if query_params:
            query_building.append('        params = {}')
            for param_name in query_params:
                query_building.append(f'        if {param_name} is not None:')
                query_building.append(f'            params["{param_name}"] = {param_name}')
        
        request_args = [f'"{operation.method.upper()}"', f'f"{path_substitution}"']
        
        if query_params:
            request_args.append('params=params')
        
        if request_model:
            request_args.append('json=data.dict() if hasattr(data, "dict") else data')
        
        return f'''
    def {method_name}(self, {params_str}) -> Dict[str, Any]:
        """
        {operation.summary or f"{operation.method} {operation.path}"}
        
        {operation.description or ""}
        """
{chr(10).join(query_building)}
        
        response = self.client.request(
            {', '.join(request_args)}
        )
        response.raise_for_status()
        return response.json()'''
    
    def _generate_typescript_client(self, api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate TypeScript client SDK."""
        content = f'''/**
 * {api_spec.title} TypeScript Client
 * 
 * Generated TypeScript client SDK for {api_spec.title} API.
 * Version: {api_spec.version}
 */

export interface ClientConfig {{
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
}}

export class {api_spec.title.replace(' ', '')}Client {{
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  constructor(config: ClientConfig) {{
    this.baseUrl = config.baseUrl.replace(/\\/$/, '');
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
  }}

  private async request<T>(
    method: string,
    path: string,
    options?: {{
      params?: Record<string, any>;
      data?: any;
      headers?: Record<string, string>;
    }}
  ): Promise<T> {{
    const url = new URL(path, this.baseUrl);
    
    if (options?.params) {{
      Object.entries(options.params).forEach(([key, value]) => {{
        if (value !== undefined && value !== null) {{
          url.searchParams.append(key, String(value));
        }}
      }});
    }}

    const headers: Record<string, string> = {{
      'Content-Type': 'application/json',
      'User-Agent': '{api_spec.title.replace(' ', '')}-TypeScript-Client/{api_spec.version}',
      ...options?.headers,
    }};

    if (this.apiKey) {{
      headers['Authorization'] = `Bearer ${{this.apiKey}}`;
    }}

    const response = await fetch(url.toString(), {{
      method,
      headers,
      body: options?.data ? JSON.stringify(options.data) : undefined,
      signal: AbortSignal.timeout(this.timeout),
    }});

    if (!response.ok) {{
      throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
    }}

    return response.json();
  }}
'''
        
        # Generate TypeScript methods for each operation
        for operation in api_spec.operations:
            ts_method = self._generate_typescript_method(operation)
            content += f'\n{ts_method}'
        
        content += '\n}'
        
        return GeneratedFile(
            path=f"clients/{api_spec.title.lower().replace(' ', '_')}_client.ts",
            content=content,
            language="typescript"
        )
    
    def _generate_typescript_method(self, operation: OperationDefinition) -> str:
        """Generate TypeScript client method."""
        method_name = operation.get_function_name()
        
        # Generate parameters interface
        params = []
        path_params = []
        query_params = []
        
        for param in operation.parameters:
            ts_type = self._get_typescript_type(param.type, param.format)
            optional = '' if param.required else '?'
            params.append(f'    {param.name}{optional}: {ts_type};')
            
            if param.location == 'path':
                path_params.append(param.name)
            elif param.location == 'query':
                query_params.append(param.name)
        
        request_model = operation.get_request_model()
        if request_model:
            params.append(f'    data: {request_model};')
        
        interface_name = f'{method_name.title().replace("_", "")}Params'
        
        if params:
            params_interface = f'''
  interface {interface_name} {{
{chr(10).join(params)}
  }}'''
        else:
            params_interface = ''
            interface_name = '{}'
        
        # Generate path substitution
        path_substitution = operation.path
        for param_name in path_params:
            path_substitution = path_substitution.replace(f'{{{param_name}}}', f'${{params.{param_name}}}')
        
        # Generate query params
        query_building = ''
        if query_params:
            query_list = ', '.join([f'{p}: params.{p}' for p in query_params])
            query_building = f'      params: {{ {query_list} }},'
        
        # Generate data
        data_building = ''
        if request_model:
            data_building = '      data: params.data,'
        
        return f'''{params_interface}

  async {method_name}(params: {interface_name}): Promise<any> {{
    return this.request(
      '{operation.method.upper()}',
      `{path_substitution}`,
      {{
{query_building}
{data_building}
      }}
    );
  }}'''
    
    def _get_typescript_type(self, python_type: str, format_type: Optional[str] = None) -> str:
        """Convert Python type to TypeScript type."""
        type_mapping = {
            'string': 'string',
            'integer': 'number',
            'number': 'number',
            'boolean': 'boolean',
            'array': 'any[]',
            'object': 'Record<string, any>'
        }
        
        ts_type = type_mapping.get(python_type, 'any')
        
        if format_type:
            if format_type in ['date-time', 'date']:
                ts_type = 'string'  # ISO string format
            elif format_type == 'uuid':
                ts_type = 'string'
        
        return ts_type
    
    def _generate_tests(self, api_spec: APISpecification, options: Dict[str, Any]) -> List[GeneratedFile]:
        """Generate test files."""
        files = []
        
        # Generate API tests
        api_tests = self._generate_api_tests(api_spec, options)
        files.append(api_tests)
        
        # Generate client tests
        client_tests = self._generate_client_tests(api_spec, options)
        files.append(client_tests)
        
        return files
    
    def _generate_api_tests(self, api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate API endpoint tests."""
        content = f'''"""
{api_spec.title} API Tests

Generated tests for {api_spec.title} API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from ..main import app


client = TestClient(app)


class TestAPI:
    """Test cases for API endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
'''
        
        # Generate tests for each operation
        for operation in api_spec.operations:
            test_method = self._generate_operation_test(operation)
            content += f'\n{test_method}'
        
        return GeneratedFile(
            path="tests/test_api.py",
            content=content,
            language="python"
        )
    
    def _generate_operation_test(self, operation: OperationDefinition) -> str:
        """Generate test for an operation."""
        test_name = f"test_{operation.get_function_name()}"
        
        # Generate test data
        path_params = {}
        query_params = {}
        
        for param in operation.parameters:
            if param.location == 'path':
                if param.type == 'integer':
                    path_params[param.name] = 1
                else:
                    path_params[param.name] = 'test'
            elif param.location == 'query':
                if param.type == 'integer':
                    query_params[param.name] = 1
                else:
                    query_params[param.name] = 'test'
        
        # Build test path
        test_path = operation.path
        for param_name, param_value in path_params.items():
            test_path = test_path.replace(f'{{{param_name}}}', str(param_value))
        
        # Build request
        request_args = [f'"{test_path}"']
        
        if query_params:
            params_str = ', '.join([f'"{k}": "{v}"' for k, v in query_params.items()])
            request_args.append(f'params={{{params_str}}}')
        
        if operation.request_body:
            request_args.append('json={"test": "data"}')
        
        return f'''
    def {test_name}(self):
        """Test {operation.method} {operation.path}."""
        # TODO: Add proper test data and assertions
        response = client.{operation.method.lower()}({', '.join(request_args)})
        # Add appropriate assertions based on expected responses
        assert response.status_code in [200, 201, 204, 404]  # Adjust as needed'''
    
    def _generate_client_tests(self, api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate client SDK tests."""
        client_name = f"{api_spec.title.replace(' ', '')}Client"
        
        content = f'''"""
{api_spec.title} Client Tests

Generated tests for {api_spec.title} client SDK.
"""

import pytest
from unittest.mock import Mock, patch
import httpx

from ..clients.{api_spec.title.lower().replace(' ', '_')}_client import {client_name}


class Test{client_name}:
    """Test cases for API client."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = {client_name}(
            base_url="https://api.example.com",
            api_key="test-key"
        )
    
    def teardown_method(self):
        """Clean up test client."""
        self.client.close()
    
    @patch('httpx.Client.request')
    def test_client_initialization(self, mock_request):
        """Test client initialization."""
        assert self.client.base_url == "https://api.example.com"
        assert self.client.api_key == "test-key"
        assert self.client.timeout == 30.0
    
    @patch('httpx.Client.request')
    def test_client_context_manager(self, mock_request):
        """Test client as context manager."""
        with {client_name}("https://api.example.com") as client:
            assert client is not None
'''
        
        # Generate client method tests
        for operation in api_spec.operations:
            client_test = self._generate_client_method_test(operation)
            content += f'\n{client_test}'
        
        return GeneratedFile(
            path="tests/test_client.py",
            content=content,
            language="python"
        )
    
    def _generate_client_method_test(self, operation: OperationDefinition) -> str:
        """Generate test for client method."""
        method_name = operation.get_function_name()
        test_name = f"test_{method_name}"
        
        # Generate test parameters
        test_params = []
        for param in operation.parameters:
            if param.type == 'integer':
                test_params.append(f'{param.name}=1')
            else:
                test_params.append(f'{param.name}="test"')
        
        if operation.get_request_model():
            test_params.append('data={"test": "data"}')
        
        params_str = ', '.join(test_params)
        
        return f'''
    @patch('httpx.Client.request')
    def {test_name}(self, mock_request):
        """Test {method_name} method."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {{"result": "success"}}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        # Call method
        result = self.client.{method_name}({params_str})
        
        # Assertions
        assert result == {{"result": "success"}}
        mock_request.assert_called_once()'''
    
    def _generate_documentation(self, api_spec: APISpecification, options: Dict[str, Any]) -> GeneratedFile:
        """Generate API documentation."""
        content = f'''# {api_spec.title} API Documentation

{api_spec.description}

**Version:** {api_spec.version}

## Overview

This documentation describes the {api_spec.title} API endpoints and how to use them.

## Authentication

The API uses Bearer token authentication. Include your API key in the Authorization header:

```
Authorization: Bearer YOUR_API_KEY
```

## Base URL

```
{api_spec.base_url or 'https://api.example.com'}
```

## Endpoints

'''
        
        # Group operations by tags
        operations_by_tag = {}
        for operation in api_spec.operations:
            tags = operation.tags or ['Default']
            for tag in tags:
                if tag not in operations_by_tag:
                    operations_by_tag[tag] = []
                operations_by_tag[tag].append(operation)
        
        # Generate documentation for each tag
        for tag, operations in operations_by_tag.items():
            content += f'\n### {tag}\n\n'
            
            for operation in operations:
                content += self._generate_operation_docs(operation)
        
        # Add client SDK documentation
        content += f'''
## Client SDKs

### Python Client

```python
from {api_spec.title.lower().replace(' ', '_')}_client import {api_spec.title.replace(' ', '')}Client

# Initialize client
client = {api_spec.title.replace(' ', '')}Client(
    base_url="https://api.example.com",
    api_key="your-api-key"
)

# Use client methods
result = client.some_method(param="value")
```

### TypeScript Client

```typescript
import {{ {api_spec.title.replace(' ', '')}Client }} from './{api_spec.title.lower().replace(' ', '_')}_client';

// Initialize client
const client = new {api_spec.title.replace(' ', '')}Client({{
  baseUrl: 'https://api.example.com',
  apiKey: 'your-api-key'
}});

// Use client methods
const result = await client.someMethod({{ param: 'value' }});
```

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

Error responses include a JSON object with error details:

```json
{{
  "detail": "Error description"
}}
```
'''
        
        return GeneratedFile(
            path="docs/api_documentation.md",
            content=content,
            language="markdown"
        )
    
    def _generate_operation_docs(self, operation: OperationDefinition) -> str:
        """Generate documentation for an operation."""
        docs = f'''
#### {operation.method.upper()} {operation.path}

{operation.summary or f"{operation.method.upper()} {operation.path}"}

{operation.description or ""}

**Parameters:**

'''
        
        if operation.parameters:
            for param in operation.parameters:
                required = "**Required**" if param.required else "Optional"
                docs += f'- `{param.name}` ({param.location}) - {param.type} - {required}\n'
                if param.description:
                    docs += f'  {param.description}\n'
        else:
            docs += 'None\n'
        
        if operation.request_body:
            docs += '\n**Request Body:**\n\n'
            request_model = operation.get_request_model()
            if request_model:
                docs += f'Content-Type: application/json\nModel: {request_model}\n'
            else:
                docs += 'Content-Type: application/json\n'
        
        docs += '\n**Responses:**\n\n'
        for response in operation.responses:
            docs += f'- `{response.status_code}` - {response.description}\n'
        
        docs += '\n**Example:**\n\n'
        docs += f'```bash\ncurl -X {operation.method.upper()} "{operation.path}" \\\n'
        docs += '  -H "Authorization: Bearer YOUR_API_KEY" \\\n'
        docs += '  -H "Content-Type: application/json"\n```\n\n'
        
        return docs
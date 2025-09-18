"""
Advanced Code Generators

Comprehensive code generators for FastAPI microservices including
CRUD operations, API endpoints, and client SDKs.
"""

from .base import CodeGenerator, GeneratedFile, GenerationResult
from .crud import AdvancedCRUDGenerator, ModelDefinition, FieldDefinition
from .test_generator import TestGenerator

# Aliases for backward compatibility
CRUDGenerator = AdvancedCRUDGenerator
APIGenerator = TestGenerator  # Temporary alias until APIGenerator is implemented

__all__ = [
    'CodeGenerator',
    'GeneratedFile', 
    'GenerationResult',
    'AdvancedCRUDGenerator',
    'CRUDGenerator',
    'ModelDefinition',
    'FieldDefinition',
    'TestGenerator',
    'APIGenerator'
]
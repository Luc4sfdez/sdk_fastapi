"""
Database Generator for FastAPI microservices.

This module provides database schema generation, migration scripts,
and database configuration for FastAPI microservices.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
from dataclasses import dataclass, field

from ..config import TemplateConfig, TemplateVariable, VariableType
from ..exceptions import TemplateError


class BaseTemplate:
    """Base template class."""
    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
    
    def get_config(self) -> TemplateConfig:
        """Get template configuration."""
        raise NotImplementedError
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate files from template."""
        raise NotImplementedError


@dataclass
class DatabaseField:
    """Database field definition."""
    name: str
    type: str
    nullable: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default: Any = None
    unique: bool = False
    index: bool = False


@dataclass
class DatabaseTable:
    """Database table definition."""
    name: str
    fields: List[DatabaseField] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)


class DatabaseGenerator:
    """Generator for database schemas and configurations."""
    
    def __init__(self):
        self.supported_databases = ["postgresql", "mysql", "sqlite", "mongodb"]
        self.supported_orms = ["sqlalchemy", "tortoise", "peewee", "mongoengine"]
    
    def generate_schema(self, tables: List[DatabaseTable], database_type: str = "postgresql", 
                       orm: str = "sqlalchemy") -> Dict[str, str]:
        """Generate database schema files."""
        if database_type not in self.supported_databases:
            raise TemplateError(f"Unsupported database type: {database_type}")
        
        if orm not in self.supported_orms:
            raise TemplateError(f"Unsupported ORM: {orm}")
        
        files = {}
        
        if orm == "sqlalchemy":
            files.update(self._generate_sqlalchemy_schema(tables, database_type))
        elif orm == "tortoise":
            files.update(self._generate_tortoise_schema(tables, database_type))
        elif orm == "mongoengine":
            files.update(self._generate_mongoengine_schema(tables))
        
        # Generate migration files
        files.update(self._generate_migrations(tables, database_type, orm))
        
        # Generate database configuration
        files.update(self._generate_database_config(database_type, orm))
        
        return files
    
    def _generate_sqlalchemy_schema(self, tables: List[DatabaseTable], 
                                   database_type: str) -> Dict[str, str]:
        """Generate SQLAlchemy schema files."""
        files = {}
        
        # Generate models.py
        models_content = self._generate_sqlalchemy_models(tables, database_type)
        files["app/models/__init__.py"] = '"""Database models."""\n\nfrom .models import *\n'
        files["app/models/models.py"] = models_content
        
        # Generate database.py
        database_content = self._generate_sqlalchemy_database(database_type)
        files["app/database.py"] = database_content
        
        return files
    
    def _generate_sqlalchemy_models(self, tables: List[DatabaseTable], 
                                   database_type: str) -> str:
        """Generate SQLAlchemy model definitions."""
        content = '''"""
SQLAlchemy database models.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


'''
        
        for table in tables:
            content += self._generate_sqlalchemy_model(table, database_type)
            content += "\n\n"
        
        return content
    
    def _generate_sqlalchemy_model(self, table: DatabaseTable, database_type: str) -> str:
        """Generate individual SQLAlchemy model."""
        class_name = self._to_pascal_case(table.name)
        
        content = f'class {class_name}(Base):\n'
        content += f'    """Model for {table.name} table."""\n'
        content += f'    __tablename__ = "{table.name}"\n\n'
        
        # Generate fields
        for field in table.fields:
            content += f'    {field.name} = {self._generate_sqlalchemy_column(field, database_type)}\n'
        
        # Generate relationships
        for rel in table.relationships:
            content += f'    {rel["name"]} = relationship("{rel["model"]}"'
            if rel.get("back_populates"):
                content += f', back_populates="{rel["back_populates"]}"'
            content += ')\n'
        
        # Add timestamps if not present
        has_created_at = any(f.name == "created_at" for f in table.fields)
        has_updated_at = any(f.name == "updated_at" for f in table.fields)
        
        if not has_created_at:
            content += '    created_at = Column(DateTime, default=datetime.utcnow)\n'
        if not has_updated_at:
            content += '    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)\n'
        
        return content
    
    def _generate_sqlalchemy_column(self, field: DatabaseField, database_type: str) -> str:
        """Generate SQLAlchemy column definition."""
        column_type = self._map_field_type_sqlalchemy(field.type, database_type)
        
        parts = [f"Column({column_type}"]
        
        if field.foreign_key:
            parts.append(f'ForeignKey("{field.foreign_key}")')
        
        if field.primary_key:
            parts.append("primary_key=True")
        
        if field.unique:
            parts.append("unique=True")
        
        if field.index:
            parts.append("index=True")
        
        if not field.nullable:
            parts.append("nullable=False")
        
        if field.default is not None:
            if isinstance(field.default, str):
                parts.append(f'default="{field.default}"')
            else:
                parts.append(f'default={field.default}')
        
        return ", ".join(parts) + ")"
    
    def _generate_sqlalchemy_database(self, database_type: str) -> str:
        """Generate SQLAlchemy database configuration."""
        return f'''"""
Database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import os

from .models import Base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "{self._get_default_database_url(database_type)}"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    {self._get_engine_options(database_type)}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Get database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
'''
    
    def _generate_tortoise_schema(self, tables: List[DatabaseTable], 
                                 database_type: str) -> Dict[str, str]:
        """Generate Tortoise ORM schema files."""
        files = {}
        
        # Generate models.py
        models_content = self._generate_tortoise_models(tables)
        files["app/models/__init__.py"] = '"""Database models."""\n\nfrom .models import *\n'
        files["app/models/models.py"] = models_content
        
        # Generate database.py
        database_content = self._generate_tortoise_database(database_type)
        files["app/database.py"] = database_content
        
        return files
    
    def _generate_tortoise_models(self, tables: List[DatabaseTable]) -> str:
        """Generate Tortoise ORM model definitions."""
        content = '''"""
Tortoise ORM database models.
"""

from tortoise.models import Model
from tortoise import fields


'''
        
        for table in tables:
            content += self._generate_tortoise_model(table)
            content += "\n\n"
        
        return content
    
    def _generate_tortoise_model(self, table: DatabaseTable) -> str:
        """Generate individual Tortoise ORM model."""
        class_name = self._to_pascal_case(table.name)
        
        content = f'class {class_name}(Model):\n'
        content += f'    """Model for {table.name} table."""\n\n'
        
        # Generate fields
        for field in table.fields:
            if field.primary_key and field.name == "id":
                continue  # Tortoise auto-generates id field
            content += f'    {field.name} = {self._generate_tortoise_field(field)}\n'
        
        # Add Meta class
        content += f'\n    class Meta:\n'
        content += f'        table = "{table.name}"\n'
        
        return content
    
    def _generate_tortoise_field(self, field: DatabaseField) -> str:
        """Generate Tortoise ORM field definition."""
        field_type = self._map_field_type_tortoise(field.type)
        
        parts = [field_type]
        
        if field.primary_key:
            parts.append("pk=True")
        
        if field.unique:
            parts.append("unique=True")
        
        if field.index:
            parts.append("index=True")
        
        if field.nullable:
            parts.append("null=True")
        
        if field.default is not None:
            if isinstance(field.default, str):
                parts.append(f'default="{field.default}"')
            else:
                parts.append(f'default={field.default}')
        
        if len(parts) == 1:
            return f"fields.{parts[0]}()"
        else:
            options = ", ".join(parts[1:])
            return f"fields.{parts[0]}({options})"
    
    def _generate_mongoengine_schema(self, tables: List[DatabaseTable]) -> Dict[str, str]:
        """Generate MongoEngine schema files."""
        files = {}
        
        # Generate models.py
        models_content = self._generate_mongoengine_models(tables)
        files["app/models/__init__.py"] = '"""Database models."""\n\nfrom .models import *\n'
        files["app/models/models.py"] = models_content
        
        # Generate database.py
        database_content = self._generate_mongoengine_database()
        files["app/database.py"] = database_content
        
        return files
    
    def _generate_mongoengine_models(self, tables: List[DatabaseTable]) -> str:
        """Generate MongoEngine model definitions."""
        content = '''"""
MongoEngine database models.
"""

from mongoengine import Document, EmbeddedDocument
from mongoengine import StringField, IntField, BooleanField, DateTimeField
from mongoengine import ListField, ReferenceField, EmbeddedDocumentField
from datetime import datetime


'''
        
        for table in tables:
            content += self._generate_mongoengine_model(table)
            content += "\n\n"
        
        return content
    
    def _generate_migrations(self, tables: List[DatabaseTable], 
                           database_type: str, orm: str) -> Dict[str, str]:
        """Generate migration files."""
        files = {}
        
        if orm == "sqlalchemy":
            # Generate Alembic migration
            migration_content = self._generate_alembic_migration(tables, database_type)
            files["migrations/versions/001_initial_migration.py"] = migration_content
            files["migrations/alembic.ini"] = self._generate_alembic_config(database_type)
            files["migrations/env.py"] = self._generate_alembic_env()
        
        return files
    
    def _generate_alembic_migration(self, tables: List[DatabaseTable], database_type: str) -> str:
        """Generate Alembic migration file."""
        return f'''"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create tables."""
{self._generate_alembic_upgrade_operations(tables, database_type)}

def downgrade():
    """Drop tables."""
{self._generate_alembic_downgrade_operations(tables)}
'''
    
    def _generate_alembic_config(self, database_type: str) -> str:
        """Generate Alembic configuration file."""
        return f'''# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# version_path_separator =

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = {self._get_default_database_url(database_type)}

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
    
    def _generate_alembic_env(self) -> str:
        """Generate Alembic env.py file."""
        return '''from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add your model's MetaData object here for 'autogenerate' support
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.models import Base
target_metadata = Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    def _generate_alembic_upgrade_operations(self, tables: List[DatabaseTable], database_type: str) -> str:
        """Generate Alembic upgrade operations."""
        operations = []
        
        for table in tables:
            op_lines = [f"    op.create_table('{table.name}',"]
            
            for field in table.fields:
                column_def = self._generate_alembic_column(field, database_type)
                op_lines.append(f"        {column_def},")
            
            op_lines.append("    )")
            operations.append("\n".join(op_lines))
        
        return "\n\n".join(operations)
    
    def _generate_alembic_downgrade_operations(self, tables: List[DatabaseTable]) -> str:
        """Generate Alembic downgrade operations."""
        operations = []
        
        # Drop tables in reverse order
        for table in reversed(tables):
            operations.append(f"    op.drop_table('{table.name}')")
        
        return "\n".join(operations)
    
    def _generate_alembic_column(self, field: DatabaseField, database_type: str) -> str:
        """Generate Alembic column definition."""
        column_type = self._map_field_type_sqlalchemy(field.type, database_type)
        
        parts = [f"sa.Column('{field.name}', sa.{column_type}"]
        
        if field.primary_key:
            parts.append("primary_key=True")
        
        if field.unique:
            parts.append("unique=True")
        
        if not field.nullable:
            parts.append("nullable=False")
        
        if field.default is not None:
            if isinstance(field.default, str):
                parts.append(f'default="{field.default}"')
            else:
                parts.append(f'default={field.default}')
        
        return ", ".join(parts) + ")"
    
    def _generate_database_config(self, database_type: str, orm: str) -> Dict[str, str]:
        """Generate database configuration files."""
        files = {}
        
        # Generate requirements
        requirements = self._get_database_requirements(database_type, orm)
        files["requirements_db.txt"] = "\n".join(requirements)
        
        # Generate environment file
        env_content = self._generate_env_template(database_type)
        files[".env.example"] = env_content
        
        return files
    
    def _map_field_type_sqlalchemy(self, field_type: str, database_type: str) -> str:
        """Map field type to SQLAlchemy column type."""
        mapping = {
            "string": "String(255)",
            "text": "Text",
            "integer": "Integer",
            "boolean": "Boolean",
            "datetime": "DateTime",
            "date": "Date",
            "time": "Time",
            "float": "Float",
            "decimal": "Numeric",
            "json": "JSON" if database_type == "postgresql" else "Text",
            "uuid": "String(36)"
        }
        return mapping.get(field_type.lower(), "String(255)")
    
    def _map_field_type_tortoise(self, field_type: str) -> str:
        """Map field type to Tortoise ORM field type."""
        mapping = {
            "string": "CharField",
            "text": "TextField",
            "integer": "IntField",
            "boolean": "BooleanField",
            "datetime": "DatetimeField",
            "date": "DateField",
            "time": "TimeField",
            "float": "FloatField",
            "decimal": "DecimalField",
            "json": "JSONField",
            "uuid": "UUIDField"
        }
        return mapping.get(field_type.lower(), "CharField")
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return "".join(word.capitalize() for word in snake_str.split("_"))
    
    def _get_default_database_url(self, database_type: str) -> str:
        """Get default database URL for type."""
        urls = {
            "postgresql": "postgresql://user:password@localhost/dbname",
            "mysql": "mysql://user:password@localhost/dbname",
            "sqlite": "sqlite:///./app.db",
            "mongodb": "mongodb://localhost:27017/dbname"
        }
        return urls.get(database_type, urls["sqlite"])
    
    def _get_engine_options(self, database_type: str) -> str:
        """Get SQLAlchemy engine options."""
        if database_type == "sqlite":
            return 'connect_args={"check_same_thread": False}'
        return 'pool_pre_ping=True'
    
    def _get_database_requirements(self, database_type: str, orm: str) -> List[str]:
        """Get database-specific requirements."""
        requirements = []
        
        if orm == "sqlalchemy":
            requirements.extend([
                "sqlalchemy>=1.4.0",
                "alembic>=1.8.0"
            ])
        elif orm == "tortoise":
            requirements.extend([
                "tortoise-orm>=0.19.0",
                "aerich>=0.7.0"
            ])
        elif orm == "mongoengine":
            requirements.append("mongoengine>=0.24.0")
        
        # Database drivers
        if database_type == "postgresql":
            requirements.append("psycopg2-binary>=2.9.0")
        elif database_type == "mysql":
            requirements.append("pymysql>=1.0.0")
        elif database_type == "mongodb":
            requirements.append("pymongo>=4.0.0")
        
        return requirements
    
    def _generate_env_template(self, database_type: str) -> str:
        """Generate environment template."""
        return f'''# Database Configuration
DATABASE_URL={self._get_default_database_url(database_type)}

# Database Connection Pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Database SSL (for production)
DB_SSL_MODE=prefer
'''


class DatabaseTemplate(BaseTemplate):
    """Template for database generation."""
    
    def __init__(self):
        super().__init__(
            name="database",
            description="Database schema and configuration generator",
            version="1.0.0"
        )
        self.generator = DatabaseGenerator()
    
    def get_config(self) -> TemplateConfig:
        """Get template configuration."""
        return TemplateConfig(
            variables=[
                TemplateVariable(
                    name="database_type",
                    description="Database type",
                    type=VariableType.STRING,
                    choices=["postgresql", "mysql", "sqlite", "mongodb"],
                    default="postgresql"
                ),
                TemplateVariable(
                    name="orm",
                    description="ORM framework",
                    type=VariableType.STRING,
                    choices=["sqlalchemy", "tortoise", "mongoengine"],
                    default="sqlalchemy"
                ),
                TemplateVariable(
                    name="tables",
                    description="Database tables configuration",
                    type=VariableType.STRING,
                    default="[]"
                )
            ]
        )
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate database files."""
        database_type = context.get("database_type", "postgresql")
        orm = context.get("orm", "sqlalchemy")
        tables_config = context.get("tables", "[]")
        
        # Parse tables configuration
        if isinstance(tables_config, str):
            tables_config = json.loads(tables_config)
        
        tables = []
        for table_config in tables_config:
            table = DatabaseTable(
                name=table_config["name"],
                fields=[
                    DatabaseField(**field_config) 
                    for field_config in table_config.get("fields", [])
                ],
                relationships=table_config.get("relationships", []),
                indexes=table_config.get("indexes", [])
            )
            tables.append(table)
        
        # Generate default tables if none provided
        if not tables:
            tables = self._get_default_tables()
        
        return self.generator.generate_schema(tables, database_type, orm)
    
    def _get_default_tables(self) -> List[DatabaseTable]:
        """Get default table structure."""
        return [
            DatabaseTable(
                name="users",
                fields=[
                    DatabaseField("id", "integer", primary_key=True),
                    DatabaseField("email", "string", unique=True),
                    DatabaseField("username", "string", unique=True),
                    DatabaseField("password_hash", "string"),
                    DatabaseField("is_active", "boolean", default=True),
                    DatabaseField("is_superuser", "boolean", default=False)
                ]
            ),
            DatabaseTable(
                name="items",
                fields=[
                    DatabaseField("id", "integer", primary_key=True),
                    DatabaseField("title", "string"),
                    DatabaseField("description", "text", nullable=True),
                    DatabaseField("owner_id", "integer", foreign_key="users.id"),
                    DatabaseField("is_published", "boolean", default=False)
                ],
                relationships=[
                    {"name": "owner", "model": "User", "back_populates": "items"}
                ]
            )
        ]
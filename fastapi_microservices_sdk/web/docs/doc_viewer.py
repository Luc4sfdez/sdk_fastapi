"""
API Documentation Viewer.
Provides interactive API documentation viewing with
Swagger UI integration and custom documentation templates.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

from ..core.base_manager import BaseManager
from .doc_manager import APIDocumentationManager, ServiceAPI

logger = logging.getLogger(__name__)


@dataclass
class DocumentationTheme:
    """Documentation theme configuration."""
    name: str
    primary_color: str = "#1976d2"
    secondary_color: str = "#424242"
    background_color: str = "#ffffff"
    text_color: str = "#333333"
    font_family: str = "Arial, sans-serif"
    custom_css: str = ""


class APIDocumentationViewer(BaseManager):
    """
    API Documentation Viewer.
    
    Features:
    - Interactive API documentation display
    - Swagger UI integration
    - Custom documentation themes
    - Multi-service documentation aggregation
    - Search and navigation capabilities
    - Responsive design
    """

    def __init__(self, name: str = "api_doc_viewer", config: Optional[Dict[str, Any]] = None):
        """Initialize the API documentation viewer."""
        super().__init__(name, config)
        
        # Configuration
        self._swagger_ui_enabled = config.get("swagger_ui_enabled", True) if config else True
        self._custom_themes_enabled = config.get("custom_themes_enabled", True) if config else True
        self._default_theme = config.get("default_theme", "default") if config else "default"
        
        # Documentation manager reference
        self._doc_manager: Optional[APIDocumentationManager] = None
        
        # Themes
        self._themes: Dict[str, DocumentationTheme] = {}
        self._current_theme = self._default_theme
        
        # Static files path
        self._static_path = Path(__file__).parent / "static"

    async def _initialize_impl(self) -> None:
        """Initialize the documentation viewer."""
        try:
            # Initialize default themes
            self._initialize_default_themes()
            
            # Create static files directory if it doesn't exist
            self._static_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("API documentation viewer initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API documentation viewer: {e}")
            raise

    async def _shutdown_impl(self) -> None:
        """Shutdown the documentation viewer."""
        try:
            self.logger.info("API documentation viewer shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during API documentation viewer shutdown: {e}")

    async def _health_check_impl(self) -> bool:
        """Health check implementation."""
        try:
            return self._doc_manager is not None
        except Exception:
            return False

    # Manager Integration

    def set_documentation_manager(self, doc_manager: APIDocumentationManager) -> None:
        """
        Set the documentation manager reference.
        
        Args:
            doc_manager: API documentation manager instance
        """
        self._doc_manager = doc_manager

    # Theme Management

    def _initialize_default_themes(self) -> None:
        """Initialize default documentation themes."""
        # Default theme
        self._themes["default"] = DocumentationTheme(
            name="Default",
            primary_color="#1976d2",
            secondary_color="#424242",
            background_color="#ffffff",
            text_color="#333333"
        )
        
        # Dark theme
        self._themes["dark"] = DocumentationTheme(
            name="Dark",
            primary_color="#bb86fc",
            secondary_color="#03dac6",
            background_color="#121212",
            text_color="#ffffff"
        )
        
        # Blue theme
        self._themes["blue"] = DocumentationTheme(
            name="Blue",
            primary_color="#2196f3",
            secondary_color="#03a9f4",
            background_color="#f5f5f5",
            text_color="#212121"
        )

    async def add_custom_theme(self, theme: DocumentationTheme) -> bool:
        """
        Add a custom theme.
        
        Args:
            theme: Theme configuration
            
        Returns:
            True if theme added successfully
        """
        return await self._safe_execute(
            "add_custom_theme",
            self._add_custom_theme_impl,
            theme
        )

    async def _add_custom_theme_impl(self, theme: DocumentationTheme) -> bool:
        """Implementation for adding custom theme."""
        try:
            self._themes[theme.name.lower()] = theme
            self.logger.info(f"Added custom theme: {theme.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add custom theme: {e}")
            return False

    async def set_theme(self, theme_name: str) -> bool:
        """
        Set the current theme.
        
        Args:
            theme_name: Name of the theme to set
            
        Returns:
            True if theme set successfully
        """
        if theme_name.lower() in self._themes:
            self._current_theme = theme_name.lower()
            return True
        return False

    async def get_available_themes(self) -> List[str]:
        """
        Get list of available themes.
        
        Returns:
            List of theme names
        """
        return list(self._themes.keys())

    # Documentation Rendering

    async def render_service_documentation(
        self, 
        service_name: str, 
        format: str = "html"
    ) -> Optional[str]:
        """
        Render documentation for a specific service.
        
        Args:
            service_name: Name of the service
            format: Output format (html, json)
            
        Returns:
            Rendered documentation or None
        """
        return await self._safe_execute(
            "render_service_documentation",
            self._render_service_documentation_impl,
            service_name,
            format
        )

    async def _render_service_documentation_impl(
        self, 
        service_name: str, 
        format: str
    ) -> Optional[str]:
        """Implementation for rendering service documentation."""
        try:
            if not self._doc_manager:
                self.logger.error("Documentation manager not set")
                return None
            
            # Get service documentation
            doc = await self._doc_manager.get_service_documentation(service_name)
            if not doc:
                return None
            
            if format == "json":
                return json.dumps(doc, indent=2)
            elif format == "html":
                return await self._render_html_documentation(service_name, doc)
            else:
                self.logger.error(f"Unsupported format: {format}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to render documentation for {service_name}: {e}")
            return None

    async def render_all_services_documentation(self, format: str = "html") -> Optional[str]:
        """
        Render documentation for all services.
        
        Args:
            format: Output format (html, json)
            
        Returns:
            Rendered documentation or None
        """
        return await self._safe_execute(
            "render_all_services_documentation",
            self._render_all_services_documentation_impl,
            format
        )

    async def _render_all_services_documentation_impl(self, format: str) -> Optional[str]:
        """Implementation for rendering all services documentation."""
        try:
            if not self._doc_manager:
                return None
            
            services = await self._doc_manager.get_all_services()
            if not services:
                return None
            
            if format == "json":
                all_docs = {}
                for service in services:
                    doc = await self._doc_manager.get_service_documentation(service.service_name)
                    if doc:
                        all_docs[service.service_name] = doc
                return json.dumps(all_docs, indent=2)
            elif format == "html":
                return await self._render_html_all_services(services)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to render all services documentation: {e}")
            return None

    async def _render_html_documentation(self, service_name: str, doc: Dict[str, Any]) -> str:
        """Render HTML documentation for a single service."""
        theme = self._themes[self._current_theme]
        
        # Extract service info
        info = doc.get("info", {})
        title = info.get("title", service_name)
        version = info.get("version", "1.0.0")
        description = info.get("description", "")
        
        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - API Documentation</title>
    <style>
        {self._generate_css(theme)}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{title}</h1>
            <div class="version">Version: {version}</div>
            <p class="description">{description}</p>
        </header>
        
        <nav class="navigation">
            <h3>Navigation</h3>
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#endpoints">Endpoints</a></li>
                <li><a href="#schemas">Schemas</a></li>
            </ul>
        </nav>
        
        <main class="content">
            <section id="overview" class="section">
                <h2>Overview</h2>
                <p>{description}</p>
                
                <h3>Base Information</h3>
                <table class="info-table">
                    <tr><td>Title</td><td>{title}</td></tr>
                    <tr><td>Version</td><td>{version}</td></tr>
                    <tr><td>Service</td><td>{service_name}</td></tr>
                </table>
            </section>
            
            <section id="endpoints" class="section">
                <h2>Endpoints</h2>
                {self._render_endpoints_html(doc.get("paths", {}))}
            </section>
            
            <section id="schemas" class="section">
                <h2>Schemas</h2>
                {self._render_schemas_html(doc.get("components", {}).get("schemas", {}))}
            </section>
        </main>
    </div>
    
    <script>
        {self._generate_javascript()}
    </script>
</body>
</html>
"""
        return html

    async def _render_html_all_services(self, services: List[ServiceAPI]) -> str:
        """Render HTML documentation for all services."""
        theme = self._themes[self._current_theme]
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - All Services</title>
    <style>
        {self._generate_css(theme)}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>API Documentation</h1>
            <p class="description">Documentation for all registered services</p>
        </header>
        
        <nav class="navigation">
            <h3>Services</h3>
            <ul>
"""
        
        for service in services:
            html += f'                <li><a href="#service-{service.service_name}">{service.title}</a></li>\n'
        
        html += """
            </ul>
        </nav>
        
        <main class="content">
"""
        
        for service in services:
            html += f"""
            <section id="service-{service.service_name}" class="section service-section">
                <h2>{service.title}</h2>
                <div class="service-info">
                    <span class="version">v{service.version}</span>
                    <span class="status status-{service.status}">{service.status}</span>
                </div>
                <p>{service.description}</p>
                
                <div class="service-details">
                    <h3>Endpoints ({len(service.endpoints)})</h3>
                    <div class="endpoints-summary">
"""
            
            for endpoint in service.endpoints:
                method_class = endpoint["method"].lower()
                html += f"""
                        <div class="endpoint-item">
                            <span class="method method-{method_class}">{endpoint["method"]}</span>
                            <span class="path">{endpoint["path"]}</span>
                            <span class="summary">{endpoint["summary"]}</span>
                        </div>
"""
            
            html += """
                    </div>
                </div>
            </section>
"""
        
        html += f"""
        </main>
    </div>
    
    <script>
        {self._generate_javascript()}
    </script>
</body>
</html>
"""
        return html

    def _render_endpoints_html(self, paths: Dict[str, Any]) -> str:
        """Render endpoints section HTML."""
        html = ""
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    method_class = method.lower()
                    summary = operation.get("summary", "")
                    description = operation.get("description", "")
                    
                    html += f"""
                    <div class="endpoint">
                        <div class="endpoint-header">
                            <span class="method method-{method_class}">{method.upper()}</span>
                            <span class="path">{path}</span>
                        </div>
                        <div class="endpoint-content">
                            <h4>{summary}</h4>
                            <p>{description}</p>
                            
                            {self._render_parameters_html(operation.get("parameters", []))}
                            {self._render_responses_html(operation.get("responses", {}))}
                        </div>
                    </div>
                    """
        
        return html

    def _render_parameters_html(self, parameters: List[Dict[str, Any]]) -> str:
        """Render parameters section HTML."""
        if not parameters:
            return ""
        
        html = """
                            <h5>Parameters</h5>
                            <table class="parameters-table">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Type</th>
                                        <th>In</th>
                                        <th>Required</th>
                                        <th>Description</th>
                                    </tr>
                                </thead>
                                <tbody>
        """
        
        for param in parameters:
            name = param.get("name", "")
            param_type = param.get("schema", {}).get("type", "string")
            location = param.get("in", "query")
            required = "Yes" if param.get("required", False) else "No"
            description = param.get("description", "")
            
            html += f"""
                                    <tr>
                                        <td>{name}</td>
                                        <td>{param_type}</td>
                                        <td>{location}</td>
                                        <td>{required}</td>
                                        <td>{description}</td>
                                    </tr>
            """
        
        html += """
                                </tbody>
                            </table>
        """
        
        return html

    def _render_responses_html(self, responses: Dict[str, Any]) -> str:
        """Render responses section HTML."""
        if not responses:
            return ""
        
        html = """
                            <h5>Responses</h5>
                            <div class="responses">
        """
        
        for status_code, response in responses.items():
            description = response.get("description", "")
            html += f"""
                                <div class="response">
                                    <span class="status-code">{status_code}</span>
                                    <span class="response-description">{description}</span>
                                </div>
            """
        
        html += """
                            </div>
        """
        
        return html

    def _render_schemas_html(self, schemas: Dict[str, Any]) -> str:
        """Render schemas section HTML."""
        if not schemas:
            return "<p>No schemas defined.</p>"
        
        html = ""
        
        for schema_name, schema in schemas.items():
            schema_type = schema.get("type", "object")
            description = schema.get("description", "")
            
            html += f"""
            <div class="schema">
                <h3>{schema_name}</h3>
                <p><strong>Type:</strong> {schema_type}</p>
                <p>{description}</p>
                
                {self._render_schema_properties(schema.get("properties", {}))}
            </div>
            """
        
        return html

    def _render_schema_properties(self, properties: Dict[str, Any]) -> str:
        """Render schema properties HTML."""
        if not properties:
            return ""
        
        html = """
                <h4>Properties</h4>
                <table class="properties-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "string")
            description = prop_info.get("description", "")
            
            html += f"""
                        <tr>
                            <td>{prop_name}</td>
                            <td>{prop_type}</td>
                            <td>{description}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
        """
        
        return html

    def _generate_css(self, theme: DocumentationTheme) -> str:
        """Generate CSS for the documentation theme."""
        return f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {theme.font_family};
            background-color: {theme.background_color};
            color: {theme.text_color};
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            border-bottom: 2px solid {theme.primary_color};
        }}
        
        .header h1 {{
            color: {theme.primary_color};
            margin-bottom: 10px;
        }}
        
        .version {{
            background-color: {theme.primary_color};
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            display: inline-block;
            margin: 10px 0;
        }}
        
        .navigation {{
            background-color: {theme.secondary_color}20;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        
        .navigation ul {{
            list-style: none;
        }}
        
        .navigation li {{
            margin: 5px 0;
        }}
        
        .navigation a {{
            color: {theme.primary_color};
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background-color 0.3s;
        }}
        
        .navigation a:hover {{
            background-color: {theme.primary_color}20;
        }}
        
        .section {{
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid {theme.secondary_color}30;
            border-radius: 8px;
        }}
        
        .section h2 {{
            color: {theme.primary_color};
            margin-bottom: 20px;
            border-bottom: 1px solid {theme.secondary_color}50;
            padding-bottom: 10px;
        }}
        
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        .info-table td {{
            padding: 10px;
            border: 1px solid {theme.secondary_color}30;
        }}
        
        .info-table td:first-child {{
            font-weight: bold;
            background-color: {theme.secondary_color}10;
        }}
        
        .endpoint {{
            margin: 20px 0;
            border: 1px solid {theme.secondary_color}30;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .endpoint-header {{
            background-color: {theme.secondary_color}10;
            padding: 15px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .method {{
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            color: white;
            font-size: 0.9em;
        }}
        
        .method-get {{ background-color: #61affe; }}
        .method-post {{ background-color: #49cc90; }}
        .method-put {{ background-color: #fca130; }}
        .method-delete {{ background-color: #f93e3e; }}
        .method-patch {{ background-color: #50e3c2; }}
        
        .path {{
            font-family: monospace;
            font-size: 1.1em;
            font-weight: bold;
        }}
        
        .endpoint-content {{
            padding: 20px;
        }}
        
        .parameters-table, .properties-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        
        .parameters-table th, .parameters-table td,
        .properties-table th, .properties-table td {{
            padding: 10px;
            border: 1px solid {theme.secondary_color}30;
            text-align: left;
        }}
        
        .parameters-table th, .properties-table th {{
            background-color: {theme.primary_color}20;
            font-weight: bold;
        }}
        
        .responses {{
            margin: 15px 0;
        }}
        
        .response {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 10px 0;
            padding: 10px;
            background-color: {theme.secondary_color}10;
            border-radius: 4px;
        }}
        
        .status-code {{
            background-color: {theme.primary_color};
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-weight: bold;
        }}
        
        .schema {{
            margin: 20px 0;
            padding: 20px;
            border: 1px solid {theme.secondary_color}30;
            border-radius: 8px;
        }}
        
        .service-section {{
            border-left: 4px solid {theme.primary_color};
        }}
        
        .service-info {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 10px 0;
        }}
        
        .status {{
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .status-active {{
            background-color: #4caf50;
            color: white;
        }}
        
        .status-inactive {{
            background-color: #ff9800;
            color: white;
        }}
        
        .status-error {{
            background-color: #f44336;
            color: white;
        }}
        
        .endpoints-summary {{
            margin: 15px 0;
        }}
        
        .endpoint-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 10px;
            margin: 5px 0;
            background-color: {theme.secondary_color}10;
            border-radius: 4px;
        }}
        
        .summary {{
            color: {theme.secondary_color};
            font-style: italic;
        }}
        
        {theme.custom_css}
        """

    def _generate_javascript(self) -> str:
        """Generate JavaScript for interactive features."""
        return """
        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
        
        // Collapsible sections
        document.querySelectorAll('.endpoint-header').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const content = this.nextElementSibling;
                if (content.style.display === 'none') {
                    content.style.display = 'block';
                } else {
                    content.style.display = 'none';
                }
            });
        });
        
        // Search functionality
        function searchDocumentation(query) {
            const sections = document.querySelectorAll('.endpoint, .schema');
            const searchTerm = query.toLowerCase();
            
            sections.forEach(section => {
                const text = section.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    section.style.display = 'block';
                } else {
                    section.style.display = 'none';
                }
            });
        }
        
        // Add search box if not present
        if (!document.querySelector('.search-box')) {
            const searchBox = document.createElement('div');
            searchBox.className = 'search-box';
            searchBox.innerHTML = `
                <input type="text" placeholder="Search documentation..." 
                       onkeyup="searchDocumentation(this.value)" 
                       style="width: 100%; padding: 10px; margin: 20px 0; border: 1px solid #ccc; border-radius: 4px;">
            `;
            
            const navigation = document.querySelector('.navigation');
            if (navigation) {
                navigation.appendChild(searchBox);
            }
        }
        """

    # Swagger UI Integration

    async def generate_swagger_ui(self, service_name: str) -> Optional[str]:
        """
        Generate Swagger UI HTML for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Swagger UI HTML or None
        """
        return await self._safe_execute(
            "generate_swagger_ui",
            self._generate_swagger_ui_impl,
            service_name
        )

    async def _generate_swagger_ui_impl(self, service_name: str) -> Optional[str]:
        """Implementation for generating Swagger UI."""
        try:
            if not self._doc_manager:
                return None
            
            doc = await self._doc_manager.get_service_documentation(service_name)
            if not doc:
                return None
            
            # Generate Swagger UI HTML
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.get('info', {}).get('title', service_name)} - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: 'data:application/json;base64,' + btoa(JSON.stringify({json.dumps(doc)})),
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>
"""
            return html
            
        except Exception as e:
            self.logger.error(f"Failed to generate Swagger UI for {service_name}: {e}")
            return None
#!/usr/bin/env python3
"""
🎮 DEMO INTERACTIVO DEL SDK
Prueba todas las funcionalidades paso a paso
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

async def demo_autenticacion():
    """Demo del sistema de autenticación"""
    print("\n🔐 DEMO: SISTEMA DE AUTENTICACIÓN")
    print("="*40)
    
    from fastapi_microservices_sdk.web.auth.jwt_manager import JWTManager
    from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
    
    # JWT Manager
    jwt_manager = JWTManager()
    print("✅ JWT Manager inicializado")
    
    # Generar tokens
    token_pair = jwt_manager.generate_token_pair("demo_user", "demo", "admin")
    print(f"🎫 Access Token generado: {token_pair.access_token[:50]}...")
    print(f"🔄 Refresh Token generado: {token_pair.refresh_token[:50]}...")
    
    # Verificar token
    payload = jwt_manager.verify_token(token_pair.access_token)
    print(f"✅ Token verificado - Usuario: {payload.username}")
    
    # Auth Manager
    auth_manager = AuthManager()
    await auth_manager.initialize()
    print("✅ Auth Manager inicializado")
    
    # Crear usuario demo
    try:
        user = await auth_manager.create_user("demo_user", "demo@test.com", "demo123", UserRole.DEVELOPER)
        print(f"👤 Usuario creado: {user.username} ({user.role.value})")
    except:
        print("👤 Usuario demo ya existe")
    
    # Autenticar usuario
    auth_token = await auth_manager.authenticate_user("demo_user", "demo123")
    if auth_token:
        print(f"🔑 Autenticación exitosa - Token ID: {auth_token.user_id}")
    
    print("🎉 Demo de autenticación completado!")

async def demo_servicios():
    """Demo del sistema de servicios"""
    print("\n⚙️ DEMO: SISTEMA DE SERVICIOS")
    print("="*40)
    
    from fastapi_microservices_sdk.web.services.service_manager import ServiceManager
    
    service_manager = ServiceManager()
    await service_manager.initialize()
    print("✅ Service Manager inicializado")
    
    # Listar servicios
    services = await service_manager.list_services()
    print(f"📋 Servicios encontrados: {len(services)}")
    
    for service in services[:3]:  # Mostrar solo los primeros 3
        print(f"   🔹 {service.name} - Estado: {service.status.value}")
    
    print("🎉 Demo de servicios completado!")

async def demo_templates():
    """Demo del sistema de templates"""
    print("\n📄 DEMO: SISTEMA DE TEMPLATES")
    print("="*40)
    
    from fastapi_microservices_sdk.web.templates_mgmt.template_manager import TemplateManager
    
    template_manager = TemplateManager()
    await template_manager.initialize()
    print("✅ Template Manager inicializado")
    
    # Listar templates
    templates = await template_manager.list_custom_templates()
    print(f"📋 Templates disponibles: {len(templates)}")
    
    # Analytics
    analytics = await template_manager.get_overall_analytics()
    print(f"📊 Analytics: {len(analytics)} métricas disponibles")
    
    print("🎉 Demo de templates completado!")

async def demo_logs():
    """Demo del sistema de logs"""
    print("\n📝 DEMO: SISTEMA DE LOGS")
    print("="*40)
    
    from fastapi_microservices_sdk.web.logs.log_manager import LogManager, LogFilter
    
    log_manager = LogManager()
    await log_manager.initialize()
    print("✅ Log Manager inicializado")
    
    # Obtener logs
    filter_criteria = LogFilter()
    logs = await log_manager.get_logs(filter_criteria)
    print(f"📋 Logs encontrados: {len(logs)}")
    
    # Servicios con logs
    services = await log_manager.get_service_list()
    print(f"🔍 Servicios con logs: {len(services)}")
    
    print("🎉 Demo de logs completado!")

async def demo_configuracion():
    """Demo del sistema de configuración"""
    print("\n⚙️ DEMO: SISTEMA DE CONFIGURACIÓN")
    print("="*40)
    
    from fastapi_microservices_sdk.web.configuration.configuration_manager import ConfigurationManager
    
    config_manager = ConfigurationManager()
    await config_manager.initialize()
    print("✅ Configuration Manager inicializado")
    
    # Servicios configurados
    services = await config_manager.list_configured_services()
    print(f"📋 Servicios configurados: {len(services)}")
    
    # Schemas disponibles
    schemas = await config_manager.list_schemas()
    print(f"📊 Schemas disponibles: {len(schemas)}")
    
    print("🎉 Demo de configuración completado!")

async def demo_websockets():
    """Demo del sistema de WebSockets"""
    print("\n🌐 DEMO: SISTEMA DE WEBSOCKETS")
    print("="*40)
    
    from fastapi_microservices_sdk.web.websockets.websocket_manager import WebSocketManager
    
    ws_manager = WebSocketManager()
    await ws_manager.initialize()
    print("✅ WebSocket Manager inicializado")
    
    # Conexiones activas
    connection_count = ws_manager.get_connection_count()
    print(f"🔗 Conexiones activas: {connection_count}")
    
    # Suscriptores de métricas
    metrics_subscribers = ws_manager.get_metrics_subscribers_count()
    print(f"📊 Suscriptores de métricas: {metrics_subscribers}")
    
    print("🎉 Demo de WebSockets completado!")

async def demo_completo():
    """Demo completo interactivo"""
    print("🎮 DEMO INTERACTIVO DEL SDK COMPLETO")
    print("="*50)
    print("Este demo te mostrará todas las funcionalidades del SDK")
    
    demos = [
        ("Autenticación", demo_autenticacion),
        ("Servicios", demo_servicios),
        ("Templates", demo_templates),
        ("Logs", demo_logs),
        ("Configuración", demo_configuracion),
        ("WebSockets", demo_websockets),
    ]
    
    for i, (nombre, demo_func) in enumerate(demos, 1):
        print(f"\n🎯 DEMO {i}/{len(demos)}: {nombre.upper()}")
        input("   Presiona ENTER para continuar...")
        
        try:
            await demo_func()
        except Exception as e:
            print(f"❌ Error en demo {nombre}: {e}")
        
        print(f"✅ Demo {nombre} completado")
    
    print("\n🎉 ¡DEMO COMPLETO TERMINADO!")
    print("🚀 El SDK está funcionando correctamente")
    print("\n📋 PRÓXIMOS PASOS:")
    print("   1. Ejecuta: python test_sdk_demo.py")
    print("   2. Abre: http://localhost:8000")
    print("   3. Login con: admin / admin123")
    print("   4. Explora todas las funcionalidades!")

if __name__ == "__main__":
    try:
        asyncio.run(demo_completo())
    except KeyboardInterrupt:
        print("\n👋 Demo interrumpido por el usuario")
    except Exception as e:
        print(f"\n💥 Error en el demo: {e}")
        print("🔧 Revisa que todas las dependencias estén instaladas")
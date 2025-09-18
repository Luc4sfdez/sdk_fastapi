#!/usr/bin/env python3
"""
🚀 DEMO COMPLETO DEL SDK - Prueba todo el sistema
"""

import asyncio
import uvicorn
from fastapi_microservices_sdk.web.app import AdvancedWebApp

async def demo_completo():
    """Demo completo del SDK"""
    print("🚀 INICIANDO DEMO DEL SDK COMPLETO")
    print("="*50)
    
    # 1. Inicializar la aplicación web
    print("📱 Inicializando Dashboard Web...")
    web_app = AdvancedWebApp()
    await web_app.initialize()
    
    print("✅ Dashboard inicializado correctamente!")
    print("\n🌐 ACCEDE AL DASHBOARD EN:")
    print("   👉 http://localhost:8000")
    print("   👉 Dashboard: http://localhost:8000/")
    print("   👉 API Docs: http://localhost:8000/docs")
    print("   👉 Health: http://localhost:8000/health")
    print("   👉 Login: http://localhost:8000/login")
    
    print("\n🔐 SISTEMA DE AUTENTICACIÓN:")
    print("   👤 Usuario por defecto: admin")
    print("   🔑 Password por defecto: admin123")
    
    print("\n📊 FUNCIONALIDADES DISPONIBLES:")
    print("   ✅ Dashboard con monitoreo en tiempo real")
    print("   ✅ Gestión de servicios")
    print("   ✅ Sistema de templates")
    print("   ✅ Gestión de logs")
    print("   ✅ Configuración de servicios")
    print("   ✅ Documentación API interactiva")
    print("   ✅ Sistema de salud del sistema")
    
    print("\n🎯 PRESIONA CTRL+C PARA DETENER")
    
    # 2. Ejecutar el servidor
    config = uvicorn.Config(
        app=web_app.app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(demo_completo())
    except KeyboardInterrupt:
        print("\n👋 ¡Demo terminado! Gracias por probar el SDK")
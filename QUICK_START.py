#!/usr/bin/env python3
"""
🚀 QUICK START - SDK FastAPI Microservices

Script para iniciar rápidamente el SDK
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    print("🚀 QUICK START - SDK FastAPI Microservices")
    print("=" * 50)
    
    print("\n1. 🧪 Ejecutando tests básicos...")
    try:
        result = subprocess.run([sys.executable, "test_6_services.py"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("   ✅ Tests básicos: OK")
        else:
            print("   ⚠️ Tests básicos: Algunos fallos (normal si servicios no están corriendo)")
    except Exception as e:
        print(f"   ⚠️ Error en tests: {e}")
    
    print("\n2. 🌐 Iniciando dashboard web...")
    print("   📍 URL: http://localhost:8000")
    print("   👤 Usuario: admin")
    print("   🔑 Password: admin123")
    print("\n   ⏳ Iniciando servidor...")
    
    # Abrir navegador después de 3 segundos
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8000")
    
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Ejecutar dashboard
    try:
        subprocess.run([sys.executable, "test_sdk_demo.py"])
    except KeyboardInterrupt:
        print("\n\n👋 ¡Gracias por probar el SDK!")
        print("\n📚 Próximos pasos:")
        print("   • Lee: README.md")
        print("   • Explora: docs/")
        print("   • Prueba: python test_ocr_service.py")
        print("   • Crea servicios: python create_service.py")

if __name__ == "__main__":
    main()

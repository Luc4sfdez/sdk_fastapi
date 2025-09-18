#!/usr/bin/env python3
"""
Script para instalar dependencias de OCR
"""

import subprocess
import sys
import os

def install_package(package):
    """Instalar paquete con pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🔧 INSTALANDO DEPENDENCIAS DE OCR")
    print("=" * 50)
    
    # Dependencias básicas
    basic_packages = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0", 
        "pydantic==2.5.0",
        "python-multipart==0.0.6",
        "pillow==10.1.0"
    ]
    
    print("1. 📦 Instalando dependencias básicas...")
    for package in basic_packages:
        print(f"   Instalando {package}...")
        if install_package(package):
            print(f"   ✅ {package} instalado")
        else:
            print(f"   ❌ Error instalando {package}")
    
    # Dependencias de OCR
    print("\n2. 🔍 Instalando dependencias de OCR...")
    
    # Intentar instalar EasyOCR (más fácil)
    print("   Intentando instalar EasyOCR...")
    if install_package("easyocr==1.7.0"):
        print("   ✅ EasyOCR instalado correctamente")
        
        # Dependencias adicionales para EasyOCR
        additional_packages = [
            "opencv-python==4.8.1.78",
            "numpy==1.24.3"
        ]
        
        for package in additional_packages:
            print(f"   Instalando {package}...")
            if install_package(package):
                print(f"   ✅ {package} instalado")
            else:
                print(f"   ⚠️ {package} falló, pero EasyOCR puede funcionar")
        
        print("\n🎉 ¡INSTALACIÓN COMPLETADA!")
        print("✅ EasyOCR está listo para usar")
        
    else:
        print("   ❌ EasyOCR falló, intentando Tesseract...")
        
        # Intentar instalar Tesseract
        if install_package("pytesseract==0.3.10"):
            print("   ✅ PyTesseract instalado")
            print("   ⚠️ NOTA: También necesitas instalar Tesseract OCR:")
            print("   📋 Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   📋 macOS: brew install tesseract")
            print("   📋 Ubuntu: sudo apt install tesseract-ocr")
            
        else:
            print("   ❌ No se pudo instalar ningún motor de OCR")
            print("   📋 El servicio funcionará con OCR simulado")
    
    print("\n🚀 PRÓXIMOS PASOS:")
    print("1. cd ocr-service")
    print("2. python main.py")
    print("3. Abre http://localhost:8006")
    print("4. ¡Prueba subiendo una imagen!")

if __name__ == "__main__":
    main()
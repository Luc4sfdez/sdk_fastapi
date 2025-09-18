#!/usr/bin/env python3
"""
🧪 EJECUTAR TODOS LOS TESTS DEL SDK
"""

import asyncio
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"\n🔍 {description}")
    print("="*50)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minutos timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {description}: ÉXITO")
            if result.stdout:
                print("📊 Resultado:")
                print(result.stdout[-500:])  # Últimas 500 líneas
        else:
            print(f"❌ {description}: FALLÓ")
            if result.stderr:
                print("🚨 Error:")
                print(result.stderr[-500:])
                
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description}: TIMEOUT (>5 min)")
        return False
    except Exception as e:
        print(f"💥 {description}: ERROR - {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🚀 EJECUTANDO TODOS LOS TESTS DEL SDK")
    print("="*60)
    
    tests = [
        # Tests básicos
        ("python test_authentication_system.py", "Sistema de Autenticación"),
        ("python tests/integration/test_auth_integration.py", "Integración de Autenticación"),
        ("python tests/integration/test_full_system.py", "Integración Completa del Sistema"),
        
        # Tests de componentes específicos
        ("python test_web_dashboard_complete.py", "Dashboard Web Completo"),
        ("python test_template_management_complete.py", "Sistema de Templates"),
        ("python test_log_management_complete.py", "Sistema de Logs"),
        ("python test_configuration_api_complete.py", "API de Configuración"),
        
        # Tests de performance
        ("python tests/performance/test_performance_benchmarks.py", "Benchmarks de Performance"),
        
        # Tests finales
        ("python test_sdk_final_validation.py", "Validación Final del SDK"),
    ]
    
    results = {}
    total_tests = len(tests)
    passed_tests = 0
    
    for command, description in tests:
        success = run_command(command, description)
        results[description] = "✅ PASSED" if success else "❌ FAILED"
        if success:
            passed_tests += 1
    
    # Resumen final
    print("\n" + "="*60)
    print("📋 RESUMEN FINAL DE TESTS")
    print("="*60)
    
    for test_name, result in results.items():
        print(f"{test_name}: {result}")
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"\n📊 RESULTADOS FINALES:")
    print(f"   ✅ Tests Exitosos: {passed_tests}/{total_tests}")
    print(f"   📈 Tasa de Éxito: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print(f"\n🎉 ¡EXCELENTE! El SDK está funcionando correctamente")
        print(f"🚀 Listo para usar en producción")
    elif success_rate >= 60:
        print(f"\n⚠️  El SDK funciona bien pero tiene algunas áreas de mejora")
        print(f"🔧 Revisar los tests que fallaron")
    else:
        print(f"\n🚨 El SDK necesita atención - varios tests fallaron")
        print(f"🛠️  Revisar y corregir los problemas identificados")

if __name__ == "__main__":
    main()
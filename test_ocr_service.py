#!/usr/bin/env python3
"""
Test script para OCR Service
"""

import requests
import time
import json
from pathlib import Path

# URL del servicio
OCR_SERVICE_URL = "http://localhost:8006"

def test_ocr_service():
    """Test completo del servicio OCR"""
    
    print("🔍 TESTING OCR SERVICE")
    print("=" * 50)
    
    # 1. Test health check
    print("\n1. 🏥 Health Check:")
    try:
        response = requests.get(f"{OCR_SERVICE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data['status']}")
            print(f"   📊 Stats: {data['stats']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error connecting to service: {e}")
        return
    
    # 2. Test service info
    print("\n2. 📋 Service Info:")
    try:
        response = requests.get(OCR_SERVICE_URL)
        if response.status_code == 200:
            data = response.json()
            print(f"   📝 Service: {data['service']}")
            print(f"   🔢 Version: {data['version']}")
            print(f"   📁 Supported formats: {data['supported_formats']}")
            print(f"   📏 Max file size: {data['max_file_size']}")
        else:
            print(f"   ❌ Service info failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting service info: {e}")
    
    # 3. Test upload (simulado)
    print("\n3. 📤 File Upload Test:")
    
    # Crear archivo de prueba
    test_content = b"Test image content for OCR"
    test_filename = "test_certificado.jpg"
    
    try:
        files = {"file": (test_filename, test_content, "image/jpeg")}
        response = requests.post(f"{OCR_SERVICE_URL}/upload", files=files)
        
        if response.status_code == 200:
            upload_data = response.json()
            file_id = upload_data["file_id"]
            print(f"   ✅ Upload successful")
            print(f"   🆔 File ID: {file_id}")
            print(f"   📁 Filename: {upload_data['filename']}")
            print(f"   📏 Size: {upload_data['size']} bytes")
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return
    
    # 4. Test OCR processing
    print("\n4. 🔍 OCR Processing Test:")
    
    try:
        ocr_request = {
            "file_id": file_id,
            "language": "spa",
            "extract_tables": False,
            "extract_metadata": True
        }
        
        response = requests.post(
            f"{OCR_SERVICE_URL}/process",
            json=ocr_request
        )
        
        if response.status_code == 200:
            process_data = response.json()
            task_id = process_data["task_id"]
            print(f"   ✅ Processing started")
            print(f"   🆔 Task ID: {task_id}")
            print(f"   📊 Status: {process_data['status']}")
        else:
            print(f"   ❌ Processing failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Processing error: {e}")
        return
    
    # 5. Test status monitoring
    print("\n5. 📊 Status Monitoring:")
    
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{OCR_SERVICE_URL}/status/{task_id}")
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data["status"]
                progress = status_data["progress"]
                message = status_data["message"]
                
                print(f"   📊 Status: {status} ({progress}%)")
                print(f"   💬 Message: {message}")
                
                if status == "completed":
                    print("   ✅ Processing completed!")
                    break
                elif status == "failed":
                    print("   ❌ Processing failed!")
                    return
                else:
                    print("   ⏳ Waiting...")
                    time.sleep(1)
                    attempt += 1
            else:
                print(f"   ❌ Status check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Status error: {e}")
            return
    
    if attempt >= max_attempts:
        print("   ⏰ Timeout waiting for completion")
        return
    
    # 6. Test results retrieval
    print("\n6. 📄 Results Retrieval:")
    
    try:
        response = requests.get(f"{OCR_SERVICE_URL}/results/{task_id}")
        
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Results retrieved successfully")
            print(f"   📝 Filename: {results['filename']}")
            print(f"   🔤 Language: {results['language']}")
            print(f"   📊 Confidence: {results['confidence']}%")
            print(f"   ⏱️ Processing time: {results['processing_time']}s")
            print(f"   📄 Pages: {results['pages']}")
            print(f"   📏 Text length: {len(results['text'])} characters")
            print(f"   📋 Text preview:")
            print(f"      {results['text'][:200]}...")
            print(f"   🔧 Metadata: {results['metadata']}")
        else:
            print(f"   ❌ Results retrieval failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Results error: {e}")
        return
    
    # 7. Test list results
    print("\n7. 📋 List Results:")
    
    try:
        response = requests.get(f"{OCR_SERVICE_URL}/list?limit=5")
        
        if response.status_code == 200:
            list_data = response.json()
            print(f"   ✅ List retrieved successfully")
            print(f"   📊 Total results: {list_data['total']}")
            print(f"   📄 Showing: {len(list_data['results'])} results")
            
            for i, result in enumerate(list_data['results'][:3]):
                print(f"   📝 Result {i+1}: {result['filename']} ({result['confidence']}%)")
        else:
            print(f"   ❌ List failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ List error: {e}")
    
    # 8. Test cleanup (opcional)
    print("\n8. 🧹 Cleanup Test:")
    
    try:
        response = requests.delete(f"{OCR_SERVICE_URL}/results/{task_id}")
        
        if response.status_code == 200:
            print("   ✅ Result deleted successfully")
        else:
            print(f"   ⚠️ Delete failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Delete error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 OCR SERVICE TEST COMPLETED!")
    print("\n🌐 Access points:")
    print(f"   Service: {OCR_SERVICE_URL}")
    print(f"   Docs: {OCR_SERVICE_URL}/docs")
    print(f"   Health: {OCR_SERVICE_URL}/health")

if __name__ == "__main__":
    test_ocr_service()
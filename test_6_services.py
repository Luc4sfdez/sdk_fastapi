#!/usr/bin/env python3
"""
Test script for the 6 basic services
"""

import requests
import time
import json
from datetime import datetime

# Service URLs
SERVICES = {
    "API Gateway": "http://localhost:8000",
    "Auth Service": "http://localhost:8001", 
    "User Service": "http://localhost:8002",
    "Notification Service": "http://localhost:8003",
    "File Storage Service": "http://localhost:8004",
    "Monitoring Service": "http://localhost:8005"
}

def test_service_health(name, url):
    """Test service health endpoint"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {name}: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

def test_service_root(name, url):
    """Test service root endpoint"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   📋 Service: {data.get('service', 'unknown')}")
            print(f"   📋 Version: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"   ❌ Root endpoint failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Root endpoint error: {str(e)}")
        return False

def test_auth_service():
    """Test authentication service functionality"""
    print("\n🔐 TESTING AUTH SERVICE FUNCTIONALITY:")
    
    # Test login (will fail but should return proper error)
    try:
        response = requests.post(
            "http://localhost:8001/login",
            json={"email": "test@example.com", "password": "testpass"},
            timeout=5
        )
        print(f"   📋 Login endpoint: HTTP {response.status_code}")
        
        # Test token validation endpoint
        response = requests.post(
            "http://localhost:8001/validate",
            headers={"Authorization": "Bearer invalid-token"},
            timeout=5
        )
        print(f"   📋 Validate endpoint: HTTP {response.status_code}")
        
    except Exception as e:
        print(f"   ❌ Auth functionality error: {str(e)}")

def test_notification_service():
    """Test notification service functionality"""
    print("\n📧 TESTING NOTIFICATION SERVICE FUNCTIONALITY:")
    
    try:
        # Test send notification
        response = requests.post(
            "http://localhost:8003/send",
            json={
                "recipient": "test@example.com",
                "channel": "email",
                "subject": "Test Notification",
                "content": "This is a test notification"
            },
            timeout=5
        )
        print(f"   📋 Send notification: HTTP {response.status_code}")
        
        # Test templates endpoint
        response = requests.get("http://localhost:8003/templates", timeout=5)
        print(f"   📋 Templates endpoint: HTTP {response.status_code}")
        
    except Exception as e:
        print(f"   ❌ Notification functionality error: {str(e)}")

def test_file_storage_service():
    """Test file storage service functionality"""
    print("\n📁 TESTING FILE STORAGE SERVICE FUNCTIONALITY:")
    
    try:
        # Test files listing
        response = requests.get("http://localhost:8004/files", timeout=5)
        print(f"   📋 Files listing: HTTP {response.status_code}")
        
        # Test upload endpoint (without actual file)
        response = requests.get("http://localhost:8004/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   📋 Max file size: {data.get('max_file_size', 'unknown')}")
            print(f"   📋 Supported types: {len(data.get('supported_types', []))}")
        
    except Exception as e:
        print(f"   ❌ File storage functionality error: {str(e)}")

def test_monitoring_service():
    """Test monitoring service functionality"""
    print("\n📊 TESTING MONITORING SERVICE FUNCTIONALITY:")
    
    try:
        # Test services health
        response = requests.get("http://localhost:8005/services", timeout=5)
        print(f"   📋 Services health: HTTP {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   📋 Monitored services: {data.get('total', 0)}")
            print(f"   📋 Healthy services: {data.get('healthy', 0)}")
        
        # Test logs endpoint
        response = requests.get("http://localhost:8005/logs", timeout=5)
        print(f"   📋 Logs endpoint: HTTP {response.status_code}")
        
        # Test Prometheus metrics
        response = requests.get("http://localhost:8005/metrics/prometheus", timeout=5)
        print(f"   📋 Prometheus metrics: HTTP {response.status_code}")
        
    except Exception as e:
        print(f"   ❌ Monitoring functionality error: {str(e)}")

def main():
    """Main test function"""
    print("🚀 TESTING 6 BASIC SERVICES")
    print("=" * 50)
    
    print(f"\n⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test all service health endpoints
    print("\n🏥 HEALTH CHECK RESULTS:")
    healthy_services = 0
    
    for name, url in SERVICES.items():
        if test_service_health(name, url):
            healthy_services += 1
    
    print(f"\n📊 SUMMARY: {healthy_services}/{len(SERVICES)} services are healthy")
    
    # Test service root endpoints
    print("\n📋 SERVICE INFORMATION:")
    for name, url in SERVICES.items():
        print(f"\n{name}:")
        test_service_root(name, url)
    
    # Test specific functionality
    test_auth_service()
    test_notification_service() 
    test_file_storage_service()
    test_monitoring_service()
    
    print("\n" + "=" * 50)
    print("🎉 TEST COMPLETED!")
    
    if healthy_services == len(SERVICES):
        print("✅ ALL SERVICES ARE RUNNING CORRECTLY!")
        print("\n🌐 ACCESS POINTS:")
        for name, url in SERVICES.items():
            print(f"   {name}: {url}")
            print(f"   {name} Docs: {url}/docs")
    else:
        print(f"⚠️  {len(SERVICES) - healthy_services} services need attention")
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
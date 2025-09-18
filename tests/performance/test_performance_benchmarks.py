#!/usr/bin/env python3
"""
Performance Benchmarks for FastAPI Microservices SDK
Tests performance of key components and identifies bottlenecks
"""

import asyncio
import time
import statistics
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import psutil
import gc

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class PerformanceBenchmark:
    """Performance benchmarking utilities"""
    
    def __init__(self):
        self.results = {}
        self.process = psutil.Process()
    
    def measure_time(self, func_name: str):
        """Decorator to measure execution time"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Measure memory before
                memory_before = self.process.memory_info().rss / 1024 / 1024  # MB
                
                # Measure time
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                
                # Measure memory after
                memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
                
                execution_time = end_time - start_time
                memory_used = memory_after - memory_before
                
                if func_name not in self.results:
                    self.results[func_name] = {
                        'times': [],
                        'memory_usage': [],
                        'success_count': 0,
                        'error_count': 0
                    }
                
                self.results[func_name]['times'].append(execution_time)
                self.results[func_name]['memory_usage'].append(memory_used)
                
                if result is not None:
                    self.results[func_name]['success_count'] += 1
                else:
                    self.results[func_name]['error_count'] += 1
                
                return result
            return wrapper
        return decorator
    
    def get_statistics(self, func_name: str) -> Dict[str, Any]:
        """Get performance statistics for a function"""
        if func_name not in self.results:
            return {}
        
        data = self.results[func_name]
        times = data['times']
        memory = data['memory_usage']
        
        if not times:
            return {}
        
        return {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'median_time': statistics.median(times),
            'std_dev_time': statistics.stdev(times) if len(times) > 1 else 0,
            'avg_memory': statistics.mean(memory),
            'max_memory': max(memory),
            'success_count': data['success_count'],
            'error_count': data['error_count'],
            'success_rate': data['success_count'] / (data['success_count'] + data['error_count']) * 100 if (data['success_count'] + data['error_count']) > 0 else 0
        }
    
    def print_report(self):
        """Print performance report"""
        print("\n" + "="*80)
        print("📊 PERFORMANCE BENCHMARK REPORT")
        print("="*80)
        
        for func_name, stats in [(name, self.get_statistics(name)) for name in self.results.keys()]:
            if not stats:
                continue
                
            print(f"\n🔍 {func_name.replace('_', ' ').title()}")
            print(f"   ⏱️  Average Time: {stats['avg_time']:.4f}s")
            print(f"   ⚡ Min Time: {stats['min_time']:.4f}s")
            print(f"   🐌 Max Time: {stats['max_time']:.4f}s")
            print(f"   📊 Median Time: {stats['median_time']:.4f}s")
            print(f"   📈 Std Deviation: {stats['std_dev_time']:.4f}s")
            print(f"   💾 Avg Memory: {stats['avg_memory']:.2f}MB")
            print(f"   🔥 Max Memory: {stats['max_memory']:.2f}MB")
            print(f"   ✅ Success Rate: {stats['success_rate']:.1f}%")
            print(f"   📈 Executions: {stats['success_count']} success, {stats['error_count']} errors")

# Global benchmark instance
benchmark = PerformanceBenchmark()

async def test_authentication_performance():
    """Test authentication system performance"""
    print("\n" + "="*60)
    print("🔐 TESTING AUTHENTICATION PERFORMANCE")
    print("="*60)
    
    from fastapi_microservices_sdk.web.auth.jwt_manager import JWTManager
    from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
    
    jwt_manager = JWTManager()
    auth_manager = AuthManager()
    await auth_manager.initialize()
    
    # Test JWT token generation performance
    @benchmark.measure_time("jwt_token_generation")
    async def test_jwt_generation():
        token_pair = jwt_manager.generate_token_pair("user123", "testuser", "admin")
        return token_pair.access_token
    
    # Test JWT token verification performance
    @benchmark.measure_time("jwt_token_verification")
    async def test_jwt_verification():
        token_pair = jwt_manager.generate_token_pair("user123", "testuser", "admin")
        payload = jwt_manager.verify_token(token_pair.access_token)
        return payload
    
    # Test user authentication performance
    @benchmark.measure_time("user_authentication")
    async def test_user_auth():
        # Create user if not exists
        try:
            user = await auth_manager.create_user("perf_test_user", "perf@test.com", "perfpass123", UserRole.DEVELOPER)
        except:
            pass  # User might already exist
        
        auth_token = await auth_manager.authenticate_user("perf_test_user", "perfpass123")
        return auth_token
    
    # Run performance tests
    iterations = 100
    print(f"Running {iterations} iterations for each test...")
    
    # JWT Generation Test
    for i in range(iterations):
        await test_jwt_generation()
        if i % 20 == 0:
            print(f"JWT Generation: {i}/{iterations}")
    
    # JWT Verification Test
    for i in range(iterations):
        await test_jwt_verification()
        if i % 20 == 0:
            print(f"JWT Verification: {i}/{iterations}")
    
    # User Authentication Test (fewer iterations due to database operations)
    for i in range(20):
        await test_user_auth()
        if i % 5 == 0:
            print(f"User Authentication: {i}/20")
    
    print("✅ Authentication performance tests completed!")

async def test_dashboard_performance():
    """Test dashboard loading performance"""
    print("\n" + "="*60)
    print("🌐 TESTING DASHBOARD PERFORMANCE")
    print("="*60)
    
    from fastapi_microservices_sdk.web.app import AdvancedWebApp
    from fastapi.testclient import TestClient
    
    # Test web app initialization performance
    @benchmark.measure_time("web_app_initialization")
    async def test_web_app_init():
        web_app = AdvancedWebApp()
        await web_app.initialize()
        await web_app.shutdown()
        return True
    
    # Test dashboard page loading
    @benchmark.measure_time("dashboard_page_load")
    async def test_dashboard_load():
        web_app = AdvancedWebApp()
        await web_app.initialize()
        
        client = TestClient(web_app.app)
        response = client.get("/")
        
        await web_app.shutdown()
        return response.status_code == 200
    
    # Test API endpoint performance
    @benchmark.measure_time("api_endpoint_response")
    async def test_api_response():
        web_app = AdvancedWebApp()
        await web_app.initialize()
        
        client = TestClient(web_app.app)
        response = client.get("/health")
        
        await web_app.shutdown()
        return response.status_code == 200
    
    # Run performance tests
    print("Testing web app initialization (5 iterations)...")
    for i in range(5):
        await test_web_app_init()
        print(f"Web App Init: {i+1}/5")
        gc.collect()  # Force garbage collection between tests
    
    print("Testing dashboard page loading (5 iterations)...")
    for i in range(5):
        await test_dashboard_load()
        print(f"Dashboard Load: {i+1}/5")
        gc.collect()
    
    print("Testing API endpoint response (10 iterations)...")
    for i in range(10):
        await test_api_response()
        if i % 2 == 0:
            print(f"API Response: {i+1}/10")
        gc.collect()
    
    print("✅ Dashboard performance tests completed!")

async def test_service_management_performance():
    """Test service management performance"""
    print("\n" + "="*60)
    print("⚙️ TESTING SERVICE MANAGEMENT PERFORMANCE")
    print("="*60)
    
    from fastapi_microservices_sdk.web.services.service_manager import ServiceManager
    
    service_manager = ServiceManager()
    await service_manager.initialize()
    
    # Test service listing performance
    @benchmark.measure_time("service_listing")
    async def test_service_listing():
        services = await service_manager.list_services()
        return len(services)
    
    # Test service health check performance
    @benchmark.measure_time("service_health_check")
    async def test_service_health():
        health = await service_manager.get_service_health("test-service")
        return health
    
    # Run performance tests
    iterations = 50
    print(f"Running {iterations} iterations for service tests...")
    
    for i in range(iterations):
        await test_service_listing()
        if i % 10 == 0:
            print(f"Service Listing: {i}/{iterations}")
    
    for i in range(iterations):
        await test_service_health()
        if i % 10 == 0:
            print(f"Service Health: {i}/{iterations}")
    
    print("✅ Service management performance tests completed!")

async def test_memory_usage():
    """Test memory usage patterns"""
    print("\n" + "="*60)
    print("💾 TESTING MEMORY USAGE PATTERNS")
    print("="*60)
    
    process = psutil.Process()
    
    # Measure baseline memory
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"Baseline Memory: {baseline_memory:.2f}MB")
    
    # Test memory usage during heavy operations
    from fastapi_microservices_sdk.web.app import AdvancedWebApp
    
    memory_measurements = []
    
    for i in range(5):
        # Create and initialize web app
        web_app = AdvancedWebApp()
        await web_app.initialize()
        
        current_memory = process.memory_info().rss / 1024 / 1024
        memory_measurements.append(current_memory - baseline_memory)
        
        print(f"Iteration {i+1}: Memory usage: {current_memory:.2f}MB (+{current_memory - baseline_memory:.2f}MB)")
        
        await web_app.shutdown()
        gc.collect()
        
        # Wait a bit for cleanup
        await asyncio.sleep(0.1)
    
    avg_memory = statistics.mean(memory_measurements)
    max_memory = max(memory_measurements)
    
    print(f"\n📊 Memory Usage Summary:")
    print(f"   Average Memory Increase: {avg_memory:.2f}MB")
    print(f"   Maximum Memory Increase: {max_memory:.2f}MB")
    print(f"   Memory Efficiency: {'Good' if avg_memory < 50 else 'Needs Optimization'}")
    
    print("✅ Memory usage tests completed!")

async def main():
    """Run all performance benchmarks"""
    print("🚀 Starting Performance Benchmarks...")
    
    start_time = time.time()
    
    # Run all performance tests
    await test_authentication_performance()
    await test_dashboard_performance()
    await test_service_management_performance()
    await test_memory_usage()
    
    # Print comprehensive report
    benchmark.print_report()
    
    total_time = time.time() - start_time
    print(f"\n⏱️ Total benchmark time: {total_time:.2f}s")
    
    # Performance analysis
    print("\n" + "="*80)
    print("📈 PERFORMANCE ANALYSIS")
    print("="*80)
    
    # Analyze results and provide recommendations
    jwt_stats = benchmark.get_statistics("jwt_token_generation")
    if jwt_stats and jwt_stats['avg_time'] > 0.01:
        print("⚠️  JWT token generation is slower than expected (>10ms)")
        print("   Recommendation: Consider token caching or optimization")
    
    auth_stats = benchmark.get_statistics("user_authentication")
    if auth_stats and auth_stats['avg_time'] > 0.1:
        print("⚠️  User authentication is slower than expected (>100ms)")
        print("   Recommendation: Optimize database queries or add caching")
    
    dashboard_stats = benchmark.get_statistics("dashboard_page_load")
    if dashboard_stats and dashboard_stats['avg_time'] > 2.0:
        print("⚠️  Dashboard loading is slower than expected (>2s)")
        print("   Recommendation: Optimize static assets and reduce initialization time")
    
    print("\n🎯 Performance benchmark completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
"""
Comprehensive Health Monitoring and Kubernetes Probes Example for FastAPI Microservices SDK.

This example demonstrates the complete health monitoring system including:
- Kubernetes readiness, liveness, and startup probes
- Dependency health checking with circuit breakers
- Health check registry with automatic discovery
- Health status aggregation and reporting
- FastAPI endpoint integration

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
import uvicorn

from fastapi_microservices_sdk.observability.health import (
    # Configuration
    HealthConfig,
    ProbeConfig,
    DependencyConfig,
    HealthStatus,
    ProbeType,
    DependencyType,
    create_health_config,
    create_database_dependency,
    create_cache_dependency,
    create_api_dependency,
    
    # Core Health Monitoring
    HealthCheckResult,
    SystemInfo,
    HealthMonitor,
    create_health_monitor,
    
    # Kubernetes Probes
    ProbeStatus,
    ProbeResult,
    ProbeManager,
    create_kubernetes_probes,
    
    # Dependency Health
    CircuitState,
    DependencyHealth,
    DependencyChecker,
    create_dependency_checker,
    
    # Health Registry
    HealthCheckCategory,
    HealthCheckInfo,
    HealthCheckRegistry,
    create_health_registry,
    
    # Health Endpoints
    HealthEndpoints,
    create_health_endpoints,
    
    # Exceptions
    HealthCheckError,
    DependencyHealthError
)


class HealthMonitoringDemo:
    """Comprehensive health monitoring demonstration."""
    
    def __init__(self):
        self.setup_configuration()
        self.setup_health_monitoring()
        self.setup_kubernetes_probes()
        self.setup_dependency_checking()
        self.setup_health_registry()
        self.setup_fastapi_app()
    
    def setup_configuration(self):
        """Setup health monitoring configuration."""
        print("🔧 Setting up health monitoring configuration...")
        
        # Create comprehensive health configuration
        self.health_config = create_health_config(
            service_name="health-demo-service",
            service_version="1.0.0",
            environment="production",
            
            # Enable all features
            enabled=True,
            health_check_interval=30,
            health_timeout=10.0,
            
            # Kubernetes probe configurations
            readiness_probe=ProbeConfig(
                enabled=True,
                path="/health/ready",
                port=8000,
                initial_delay_seconds=5,
                period_seconds=10,
                timeout_seconds=5,
                failure_threshold=3,
                success_threshold=1
            ),
            
            liveness_probe=ProbeConfig(
                enabled=True,
                path="/health/live",
                port=8000,
                initial_delay_seconds=30,
                period_seconds=30,
                timeout_seconds=10,
                failure_threshold=3,
                success_threshold=1
            ),
            
            startup_probe=ProbeConfig(
                enabled=True,
                path="/health/startup",
                port=8000,
                initial_delay_seconds=0,
                period_seconds=5,
                timeout_seconds=3,
                failure_threshold=30,
                success_threshold=1
            ),
            
            # Health aggregation settings
            aggregate_health=True,
            fail_on_dependency_failure=False,
            degraded_threshold=0.8,
            
            # Monitoring settings
            collect_health_metrics=True,
            expose_detailed_health=True,
            include_system_info=True,
            
            # Caching settings
            cache_health_results=True,
            cache_ttl_seconds=30,
            
            # Security settings (disabled for demo)
            require_authentication=False,
            allowed_ips=[],
            health_check_token=None
        )
        
        # Add dependency configurations
        self._add_dependency_configurations()
        
        print("✅ Health monitoring configuration completed")
    
    def _add_dependency_configurations(self):
        """Add dependency configurations."""
        # Database dependency
        database_dep = create_database_dependency(
            name="primary_database",
            host="localhost",
            port=5432,
            database_name="demo_db",
            timeout_seconds=5.0,
            circuit_breaker_enabled=True,
            failure_threshold=5,
            recovery_timeout=60
        )
        self.health_config.add_dependency(database_dep)
        
        # Cache dependency
        cache_dep = create_cache_dependency(
            name="redis_cache",
            host="localhost",
            port=6379,
            timeout_seconds=3.0,
            circuit_breaker_enabled=True,
            failure_threshold=3,
            recovery_timeout=30
        )
        self.health_config.add_dependency(cache_dep)
        
        # External API dependency
        api_dep = create_api_dependency(
            name="external_service",
            url="https://httpbin.org/status/200",
            timeout_seconds=10.0,
            circuit_breaker_enabled=True,
            failure_threshold=5,
            recovery_timeout=120
        )
        self.health_config.add_dependency(api_dep)
        
        # Message queue dependency
        mq_dep = DependencyConfig(
            name="message_queue",
            type=DependencyType.MESSAGE_QUEUE,
            host="localhost",
            port=5672,
            timeout_seconds=5.0,
            circuit_breaker_enabled=True,
            failure_threshold=3,
            recovery_timeout=60
        )
        self.health_config.add_dependency(mq_dep)
    
    def setup_health_monitoring(self):
        """Setup core health monitoring."""
        print("🏥 Setting up health monitoring...")
        
        # Create health monitor
        self.health_monitor = create_health_monitor(self.health_config)
        
        # Register custom health checks
        self._register_custom_health_checks()
        
        print("✅ Health monitoring setup completed")
    
    def _register_custom_health_checks(self):
        """Register custom health checks."""
        
        # Custom business logic health check
        async def business_logic_check():
            """Custom business logic health check."""
            start_time = time.time()
            
            try:
                # Simulate business logic validation
                await asyncio.sleep(0.1)  # Simulate some work
                
                # Check some business conditions
                business_conditions = {
                    'feature_flags_loaded': True,
                    'configuration_valid': True,
                    'license_valid': True,
                    'data_consistency': True
                }
                
                all_healthy = all(business_conditions.values())
                status = HealthStatus.HEALTHY if all_healthy else HealthStatus.DEGRADED
                
                duration_ms = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    name="business_logic",
                    status=status,
                    message="Business logic validation completed",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    details=business_conditions
                )
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="business_logic",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Business logic check failed: {e}",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    error=str(e)
                )
        
        # Register the custom check
        self.health_monitor.register_health_check("business_logic", business_logic_check)
        
        # Custom security health check
        async def security_check():
            """Custom security health check."""
            start_time = time.time()
            
            try:
                # Simulate security validations
                security_checks = {
                    'ssl_certificates_valid': True,
                    'security_policies_loaded': True,
                    'authentication_service': True,
                    'rate_limiting_active': True
                }
                
                all_secure = all(security_checks.values())
                status = HealthStatus.HEALTHY if all_secure else HealthStatus.UNHEALTHY
                
                duration_ms = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    name="security",
                    status=status,
                    message="Security validation completed",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    details=security_checks
                )
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="security",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Security check failed: {e}",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    error=str(e)
                )
        
        # Register the security check
        self.health_monitor.register_health_check("security", security_check)
    
    def setup_kubernetes_probes(self):
        """Setup Kubernetes probes."""
        print("☸️ Setting up Kubernetes probes...")
        
        # Create probe manager
        self.probe_manager = create_kubernetes_probes(
            config=self.health_config,
            health_monitor=self.health_monitor
        )
        
        print("✅ Kubernetes probes setup completed")
    
    def setup_dependency_checking(self):
        """Setup dependency health checking."""
        print("🔗 Setting up dependency checking...")
        
        # Create dependency checkers
        self.dependency_checkers = {}
        
        for dependency in self.health_config.dependencies:
            checker = create_dependency_checker(dependency)
            self.dependency_checkers[dependency.name] = checker
            
            # Register with health monitor
            async def create_dependency_wrapper(dep_name=dependency.name):
                checker = self.dependency_checkers[dep_name]
                health = await checker.check_health()
                
                return HealthCheckResult(
                    name=health.name,
                    status=health.status,
                    message=health.message,
                    timestamp=health.timestamp,
                    duration_ms=health.response_time_ms,
                    details=health.details,
                    error=health.error
                )
            
            self.health_monitor.register_dependency_checker(
                dependency.name,
                create_dependency_wrapper
            )
        
        print("✅ Dependency checking setup completed")
    
    def setup_health_registry(self):
        """Setup health check registry."""
        print("📋 Setting up health check registry...")
        
        # Create health registry
        self.health_registry = create_health_registry(
            config=self.health_config,
            health_monitor=self.health_monitor
        )
        
        # Add custom health check info
        custom_check_info = HealthCheckInfo(
            name="custom_integration",
            category=HealthCheckCategory.CUSTOM,
            description="Custom integration health check",
            enabled=True,
            timeout_seconds=5.0,
            tags={"custom", "integration", "demo"},
            metadata={
                'version': '1.0.0',
                'author': 'demo',
                'criticality': 'medium'
            }
        )
        
        # Register custom check with function
        async def custom_integration_check():
            """Custom integration health check."""
            start_time = time.time()
            
            try:
                # Simulate integration check
                await asyncio.sleep(0.05)
                
                integration_status = {
                    'third_party_api': True,
                    'webhook_endpoints': True,
                    'data_sync': True
                }
                
                all_integrated = all(integration_status.values())
                status = HealthStatus.HEALTHY if all_integrated else HealthStatus.DEGRADED
                
                duration_ms = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    name="custom_integration",
                    status=status,
                    message="Integration health check completed",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    details=integration_status
                )
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name="custom_integration",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Integration check failed: {e}",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    error=str(e)
                )
        
        custom_check_info.check_function = custom_integration_check
        self.health_registry.register_health_check(custom_check_info)
        
        print("✅ Health check registry setup completed")
    
    def setup_fastapi_app(self):
        """Setup FastAPI application with health endpoints."""
        print("🚀 Setting up FastAPI application...")
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Health Monitoring Demo Service",
            description="Comprehensive health monitoring and Kubernetes probes demonstration",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add some demo endpoints
        @self.app.get("/")
        async def root():
            return {
                "message": "Health Monitoring Demo Service",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/simulate-load")
        async def simulate_load():
            """Simulate some load for testing."""
            await asyncio.sleep(0.1)
            return {"message": "Load simulation completed"}
        
        @self.app.get("/simulate-error")
        async def simulate_error():
            """Simulate an error for testing."""
            raise Exception("Simulated error for testing")
        
        # Create health endpoints
        self.health_endpoints = create_health_endpoints(
            app=self.app,
            config=self.health_config,
            health_monitor=self.health_monitor,
            probe_manager=self.probe_manager,
            registry=self.health_registry
        )
        
        print("✅ FastAPI application setup completed")
    
    async def demonstrate_health_monitoring(self):
        """Demonstrate health monitoring capabilities."""
        print("\n🏥 === HEALTH MONITORING DEMONSTRATION ===")
        
        # 1. Overall Health Check
        print("📊 Checking overall health...")
        health_report = await self.health_monitor.get_overall_health()
        print(f"   ✅ Overall Status: {health_report['status']}")
        print(f"   📋 Total Checks: {len(health_report['checks'])}")
        print(f"   ⏱️ Service Uptime: {health_report['statistics']['uptime_seconds']:.1f}s")
        
        # 2. Individual Health Checks
        print("\n🔍 Running individual health checks...")
        individual_results = await self.health_monitor.check_health()
        
        for name, result in individual_results.items():
            status_emoji = "✅" if result.status == HealthStatus.HEALTHY else "❌"
            print(f"   {status_emoji} {name}: {result.status.value} ({result.duration_ms:.1f}ms)")
        
        # 3. Dependency Health Checks
        print("\n🔗 Checking dependency health...")
        dependency_results = await self.health_monitor.check_dependencies()
        
        for name, result in dependency_results.items():
            status_emoji = "✅" if result.status == HealthStatus.HEALTHY else "❌"
            print(f"   {status_emoji} {name}: {result.status.value} ({result.duration_ms:.1f}ms)")
        
        # 4. Health Statistics
        print("\n📊 Health monitoring statistics:")
        stats = self.health_monitor.get_health_statistics()
        print(f"   📈 Total Checks: {stats['total_checks']}")
        print(f"   ❌ Total Failures: {stats['total_failures']}")
        print(f"   📊 Failure Rate: {stats['failure_rate']:.2%}")
        print(f"   ⏱️ Avg Check Time: {stats['average_check_time_ms']:.1f}ms")
    
    async def demonstrate_kubernetes_probes(self):
        """Demonstrate Kubernetes probes."""
        print("\n☸️ === KUBERNETES PROBES DEMONSTRATION ===")
        
        # 1. Readiness Probe
        print("🟢 Testing readiness probe...")
        readiness_result = await self.probe_manager.check_probe(ProbeType.READINESS)
        status_emoji = "✅" if readiness_result.status == ProbeStatus.READY else "❌"
        print(f"   {status_emoji} Readiness: {readiness_result.status.value}")
        print(f"   💬 Message: {readiness_result.message}")
        
        # 2. Liveness Probe
        print("\n💓 Testing liveness probe...")
        liveness_result = await self.probe_manager.check_probe(ProbeType.LIVENESS)
        status_emoji = "✅" if liveness_result.status == ProbeStatus.ALIVE else "❌"
        print(f"   {status_emoji} Liveness: {liveness_result.status.value}")
        print(f"   💬 Message: {liveness_result.message}")
        
        # 3. Startup Probe
        print("\n🚀 Testing startup probe...")
        startup_result = await self.probe_manager.check_probe(ProbeType.STARTUP)
        status_emoji = "✅" if startup_result.status == ProbeStatus.STARTED else "❌"
        print(f"   {status_emoji} Startup: {startup_result.status.value}")
        print(f"   💬 Message: {startup_result.message}")
        
        # 4. All Probes
        print("\n📋 All probe statuses:")
        all_probes = await self.probe_manager.check_all_probes()
        for probe_type, result in all_probes.items():
            status_emoji = "✅" if "ready" in result.status.value or "alive" in result.status.value or "started" in result.status.value else "❌"
            print(f"   {status_emoji} {probe_type.value}: {result.status.value}")
        
        # 5. Probe Statistics
        print("\n📊 Probe statistics:")
        probe_stats = self.probe_manager.get_probe_statistics()
        for probe_type, stats in probe_stats.items():
            print(f"   📈 {probe_type}:")
            print(f"      Total Checks: {stats['total_checks']}")
            print(f"      Success Rate: {stats['success_rate']:.2%}")
            print(f"      Current Status: {stats['current_status']}")
    
    async def demonstrate_dependency_checking(self):
        """Demonstrate dependency health checking."""
        print("\n🔗 === DEPENDENCY HEALTH CHECKING DEMONSTRATION ===")
        
        for name, checker in self.dependency_checkers.items():
            print(f"\n🔍 Checking dependency: {name}")
            
            try:
                # Check dependency health
                health = await checker.check_health()
                
                status_emoji = "✅" if health.status == HealthStatus.HEALTHY else "❌"
                print(f"   {status_emoji} Status: {health.status.value}")
                print(f"   ⏱️ Response Time: {health.response_time_ms:.1f}ms")
                print(f"   💬 Message: {health.message}")
                
                if health.circuit_breaker_state:
                    print(f"   🔌 Circuit Breaker: {health.circuit_breaker_state.value}")
                
                # Get checker statistics
                stats = checker.get_statistics()
                print(f"   📊 Statistics:")
                print(f"      Total Checks: {stats['total_checks']}")
                print(f"      Success Rate: {stats['success_rate']:.2%}")
                print(f"      Avg Response Time: {stats['average_response_time_ms']:.1f}ms")
                
                if 'circuit_breaker' in stats:
                    cb_stats = stats['circuit_breaker']
                    print(f"      Circuit Breaker State: {cb_stats['state']}")
                    print(f"      Failure Count: {cb_stats['failure_count']}")
                
            except Exception as e:
                print(f"   ❌ Dependency check failed: {e}")
    
    async def demonstrate_health_registry(self):
        """Demonstrate health check registry."""
        print("\n📋 === HEALTH CHECK REGISTRY DEMONSTRATION ===")
        
        # 1. List all health checks
        print("📝 Registered health checks:")
        all_checks = self.health_registry.list_health_checks()
        
        for check in all_checks:
            status_emoji = "✅" if check.enabled else "❌"
            print(f"   {status_emoji} {check.name} ({check.category.value})")
            print(f"      Description: {check.description}")
            print(f"      Tags: {', '.join(check.tags)}")
        
        # 2. Filter by category
        print(f"\n🏷️ Dependency health checks:")
        dependency_checks = self.health_registry.list_health_checks(
            category=HealthCheckCategory.DEPENDENCY,
            enabled_only=True
        )
        
        for check in dependency_checks:
            print(f"   🔗 {check.name}")
            if check.metadata:
                print(f"      Host: {check.metadata.get('host', 'N/A')}")
                print(f"      Port: {check.metadata.get('port', 'N/A')}")
        
        # 3. Registry statistics
        print(f"\n📊 Registry statistics:")
        registry_stats = self.health_registry.get_registry_statistics()
        print(f"   📈 Total Checks: {registry_stats['total_checks']}")
        print(f"   ✅ Enabled Checks: {registry_stats['enabled_checks']}")
        print(f"   ❌ Disabled Checks: {registry_stats['disabled_checks']}")
        print(f"   🔗 Dependency Checkers: {registry_stats['dependency_checkers']}")
        
        # 4. Category breakdown
        print(f"   📊 Category Breakdown:")
        for category, count in registry_stats['category_counts'].items():
            print(f"      {category}: {count}")
    
    async def demonstrate_kubernetes_manifest_generation(self):
        """Demonstrate Kubernetes manifest generation."""
        print("\n☸️ === KUBERNETES MANIFEST GENERATION ===")
        
        # Generate Kubernetes deployment manifest
        manifest = self.health_config.to_kubernetes_manifest()
        
        print("📄 Generated Kubernetes Deployment Manifest:")
        print("```yaml")
        
        # Convert to YAML-like format for display
        import json
        manifest_json = json.dumps(manifest, indent=2)
        print(manifest_json)
        
        print("```")
        
        # Show probe configurations
        container = manifest["spec"]["template"]["spec"]["containers"][0]
        
        if "readinessProbe" in container:
            print(f"\n🟢 Readiness Probe Configuration:")
            readiness = container["readinessProbe"]
            print(f"   Path: {readiness['httpGet']['path']}")
            print(f"   Port: {readiness['httpGet']['port']}")
            print(f"   Initial Delay: {readiness['initialDelaySeconds']}s")
            print(f"   Period: {readiness['periodSeconds']}s")
            print(f"   Timeout: {readiness['timeoutSeconds']}s")
            print(f"   Failure Threshold: {readiness['failureThreshold']}")
        
        if "livenessProbe" in container:
            print(f"\n💓 Liveness Probe Configuration:")
            liveness = container["livenessProbe"]
            print(f"   Path: {liveness['httpGet']['path']}")
            print(f"   Port: {liveness['httpGet']['port']}")
            print(f"   Initial Delay: {liveness['initialDelaySeconds']}s")
            print(f"   Period: {liveness['periodSeconds']}s")
            print(f"   Timeout: {liveness['timeoutSeconds']}s")
            print(f"   Failure Threshold: {liveness['failureThreshold']}")
        
        if "startupProbe" in container:
            print(f"\n🚀 Startup Probe Configuration:")
            startup = container["startupProbe"]
            print(f"   Path: {startup['httpGet']['path']}")
            print(f"   Port: {startup['httpGet']['port']}")
            print(f"   Initial Delay: {startup['initialDelaySeconds']}s")
            print(f"   Period: {startup['periodSeconds']}s")
            print(f"   Timeout: {startup['timeoutSeconds']}s")
            print(f"   Failure Threshold: {startup['failureThreshold']}")
    
    async def run_comprehensive_demo(self):
        """Run the complete health monitoring demonstration."""
        print("🚀 === FASTAPI MICROSERVICES SDK - HEALTH MONITORING & KUBERNETES PROBES DEMO ===")
        print("This demo showcases comprehensive health monitoring and Kubernetes integration.\n")
        
        try:
            # Start background monitoring
            await self.health_monitor.start_monitoring()
            
            # Run all demonstrations
            await self.demonstrate_health_monitoring()
            await self.demonstrate_kubernetes_probes()
            await self.demonstrate_dependency_checking()
            await self.demonstrate_health_registry()
            await self.demonstrate_kubernetes_manifest_generation()
            
            print("\n🎉 === DEMONSTRATION COMPLETED SUCCESSFULLY ===")
            print("All health monitoring and Kubernetes probe features have been demonstrated!")
            
            # Final summary
            print("\n📋 === FEATURE SUMMARY ===")
            features = [
                "✅ Kubernetes Readiness, Liveness, and Startup Probes",
                "✅ Comprehensive Health Monitoring",
                "✅ Dependency Health Checking with Circuit Breakers",
                "✅ Health Check Registry with Auto-Discovery",
                "✅ Health Status Aggregation and Reporting",
                "✅ FastAPI Endpoint Integration",
                "✅ System Information Collection",
                "✅ Health Statistics and Metrics",
                "✅ Kubernetes Manifest Generation",
                "✅ Timeout and Failure Handling"
            ]
            
            for feature in features:
                print(f"  {feature}")
            
            # Show FastAPI server info
            print(f"\n🌐 === FASTAPI SERVER INFORMATION ===")
            print(f"Server will start on: http://localhost:8000")
            print(f"API Documentation: http://localhost:8000/docs")
            print(f"Health Endpoints:")
            print(f"  - Overall Health: http://localhost:8000/health")
            print(f"  - Detailed Health: http://localhost:8000/health/detailed")
            print(f"  - Readiness Probe: http://localhost:8000/health/ready")
            print(f"  - Liveness Probe: http://localhost:8000/health/live")
            print(f"  - Startup Probe: http://localhost:8000/health/startup")
            print(f"  - Health Registry: http://localhost:8000/health/registry")
            print(f"  - Health Statistics: http://localhost:8000/health/statistics")
            print(f"  - Probe Status: http://localhost:8000/health/probes")
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            raise
        
        finally:
            # Cleanup
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        print("\n🧹 Cleaning up resources...")
        
        # Stop health monitoring
        if hasattr(self, 'health_monitor'):
            await self.health_monitor.stop_monitoring()
        
        print("✅ Cleanup completed")
    
    def run_server(self):
        """Run the FastAPI server."""
        print("\n🚀 Starting FastAPI server...")
        print("Press Ctrl+C to stop the server")
        
        # Run the server
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )


async def main():
    """Main function to run the health monitoring demo."""
    demo = HealthMonitoringDemo()
    await demo.run_comprehensive_demo()
    
    # Optionally start the server
    print("\n❓ Would you like to start the FastAPI server? (y/n)")
    # For demo purposes, we'll just show the demo without starting the server
    # In a real scenario, you would uncomment the next line:
    # demo.run_server()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
"""
Health Check Endpoints for FastAPI Microservices SDK.

This module provides FastAPI endpoints for Kubernetes probes and
health monitoring with comprehensive status reporting.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import HealthConfig, ProbeType, HealthStatus
from .monitor import HealthMonitor
from .probes import ProbeManager, ProbeStatus
from .registry import HealthCheckRegistry
from .exceptions import HealthCheckError, ProbeConfigurationError


class HealthEndpoints:
    """FastAPI health check endpoints."""
    
    def __init__(
        self,
        app: FastAPI,
        config: HealthConfig,
        health_monitor: HealthMonitor,
        probe_manager: ProbeManager,
        registry: HealthCheckRegistry
    ):
        self.app = app
        self.config = config
        self.health_monitor = health_monitor
        self.probe_manager = probe_manager
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        
        # Security
        self.security = HTTPBearer(auto_error=False) if config.require_authentication else None
        
        # Register endpoints
        self._register_endpoints()
    
    def _register_endpoints(self):
        """Register all health check endpoints."""
        # Kubernetes probe endpoints
        self.app.get(
            self.config.readiness_probe.path,
            response_class=JSONResponse,
            tags=["health"],
            summary="Kubernetes Readiness Probe"
        )(self.readiness_probe)
        
        self.app.get(
            self.config.liveness_probe.path,
            response_class=JSONResponse,
            tags=["health"],
            summary="Kubernetes Liveness Probe"
        )(self.liveness_probe)
        
        self.app.get(
            self.config.startup_probe.path,
            response_class=JSONResponse,
            tags=["health"],
            summary="Kubernetes Startup Probe"
        )(self.startup_probe)
        
        # Comprehensive health endpoints
        self.app.get(
            "/health",
            response_class=JSONResponse,
            tags=["health"],
            summary="Overall Health Status"
        )(self.overall_health)
        
        self.app.get(
            "/health/detailed",
            response_class=JSONResponse,
            tags=["health"],
            summary="Detailed Health Information"
        )(self.detailed_health)
        
        self.app.get(
            "/health/check/{check_name}",
            response_class=JSONResponse,
            tags=["health"],
            summary="Individual Health Check"
        )(self.individual_health_check)
        
        # Health management endpoints
        if self.config.expose_detailed_health:
            self.app.get(
                "/health/registry",
                response_class=JSONResponse,
                tags=["health"],
                summary="Health Check Registry"
            )(self.health_registry)
            
            self.app.get(
                "/health/statistics",
                response_class=JSONResponse,
                tags=["health"],
                summary="Health Statistics"
            )(self.health_statistics)
            
            self.app.get(
                "/health/probes",
                response_class=JSONResponse,
                tags=["health"],
                summary="Probe Status"
            )(self.probe_status)
    
    async def _check_authentication(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None
    ):
        """Check authentication if required."""
        if not self.config.require_authentication:
            return True
        
        # Check IP whitelist
        if self.config.allowed_ips:
            client_ip = request.client.host
            if client_ip not in self.config.allowed_ips:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="IP address not allowed"
                )
        
        # Check token authentication
        if self.config.health_check_token:
            if not credentials or credentials.credentials != self.config.health_check_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
        
        return True
    
    async def readiness_probe(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Kubernetes readiness probe endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            # Check readiness probe
            result = await self.probe_manager.check_probe(ProbeType.READINESS)
            
            if result.status == ProbeStatus.READY:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": "ready",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message
                    }
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "not_ready",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message,
                        "details": result.details
                    }
                )
                
        except ProbeConfigurationError as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Readiness probe not configured: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Readiness probe failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "message": f"Readiness probe failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def liveness_probe(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Kubernetes liveness probe endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            # Check liveness probe
            result = await self.probe_manager.check_probe(ProbeType.LIVENESS)
            
            if result.status == ProbeStatus.ALIVE:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": "alive",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message
                    }
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "not_alive",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message,
                        "details": result.details
                    }
                )
                
        except ProbeConfigurationError as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Liveness probe not configured: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Liveness probe failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "message": f"Liveness probe failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def startup_probe(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Kubernetes startup probe endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            # Check startup probe
            result = await self.probe_manager.check_probe(ProbeType.STARTUP)
            
            if result.status == ProbeStatus.STARTED:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": "started",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message
                    }
                )
            elif result.status == ProbeStatus.STARTING:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "starting",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message,
                        "details": result.details
                    }
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "startup_failed",
                        "timestamp": result.timestamp.isoformat(),
                        "message": result.message,
                        "details": result.details
                    }
                )
                
        except ProbeConfigurationError as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Startup probe not configured: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Startup probe failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "message": f"Startup probe failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def overall_health(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Overall health status endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            # Get overall health
            health_report = await self.health_monitor.get_overall_health()
            overall_status = HealthStatus(health_report['status'])
            
            # Determine HTTP status code
            if overall_status == HealthStatus.HEALTHY:
                http_status = status.HTTP_200_OK
            elif overall_status == HealthStatus.DEGRADED:
                http_status = status.HTTP_200_OK  # Still operational
            else:
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            
            # Prepare response
            response_data = {
                "status": overall_status.value,
                "timestamp": health_report['timestamp'],
                "service": health_report['service']
            }
            
            # Add summary information
            if self.config.expose_detailed_health:
                response_data.update({
                    "checks_summary": {
                        "total": len(health_report['checks']),
                        "healthy": len([c for c in health_report['checks'].values() if c['status'] == 'healthy']),
                        "unhealthy": len([c for c in health_report['checks'].values() if c['status'] == 'unhealthy']),
                        "degraded": len([c for c in health_report['checks'].values() if c['status'] == 'degraded'])
                    },
                    "statistics": health_report['statistics']
                })
            
            return JSONResponse(
                status_code=http_status,
                content=response_data
            )
            
        except Exception as e:
            self.logger.error(f"Overall health check failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "message": f"Health check failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def detailed_health(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Detailed health information endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            if not self.config.expose_detailed_health:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Detailed health information is not enabled"
                )
            
            # Get comprehensive health report
            health_report = await self.health_monitor.get_overall_health()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=health_report
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Detailed health check failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Detailed health check failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def individual_health_check(
        self,
        check_name: str,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Individual health check endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            # Check if health check exists
            check_info = self.registry.get_health_check(check_name)
            if not check_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Health check '{check_name}' not found"
                )
            
            if not check_info.enabled:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Health check '{check_name}' is disabled"
                )
            
            # Run specific health check
            results = await self.health_monitor.check_health(check_name)
            
            if check_name in results:
                result = results[check_name]
                
                # Determine HTTP status
                if result.status == HealthStatus.HEALTHY:
                    http_status = status.HTTP_200_OK
                else:
                    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
                
                return JSONResponse(
                    status_code=http_status,
                    content=result.to_dict()
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to execute health check '{check_name}'"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Individual health check {check_name} failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Health check failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def health_registry(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Health check registry endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            if not self.config.expose_detailed_health:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Health registry information is not enabled"
                )
            
            # Get registry information
            registry_data = self.registry.export_registry()
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=registry_data
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Health registry endpoint failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Registry endpoint failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def health_statistics(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Health statistics endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            if not self.config.expose_detailed_health:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Health statistics are not enabled"
                )
            
            # Collect all statistics
            statistics = {
                "health_monitor": self.health_monitor.get_health_statistics(),
                "registry": self.registry.get_registry_statistics(),
                "probes": self.probe_manager.get_probe_statistics(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=statistics
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Health statistics endpoint failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Statistics endpoint failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    
    async def probe_status(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)
    ):
        """Probe status endpoint."""
        try:
            await self._check_authentication(request, credentials)
            
            if not self.config.expose_detailed_health:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Probe status information is not enabled"
                )
            
            # Get all probe statuses
            probe_statuses = self.probe_manager.get_all_probe_statuses()
            probe_statistics = self.probe_manager.get_probe_statistics()
            
            response_data = {
                "probe_statuses": {
                    probe_type.value: status.value
                    for probe_type, status in probe_statuses.items()
                },
                "probe_statistics": probe_statistics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Probe status endpoint failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": f"Probe status endpoint failed: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )


def create_health_endpoints(
    app: FastAPI,
    config: HealthConfig,
    health_monitor: HealthMonitor,
    probe_manager: ProbeManager,
    registry: HealthCheckRegistry
) -> HealthEndpoints:
    """Create and register health endpoints with FastAPI app."""
    return HealthEndpoints(app, config, health_monitor, probe_manager, registry)


# Export main classes and functions
__all__ = [
    'HealthEndpoints',
    'create_health_endpoints',
]
"""
Structured Logging with ELK Integration Example

This example demonstrates the structured logging capabilities including
JSON formatting, trace correlation, data masking, compliance logging,
and ELK stack integration.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any

from fastapi_microservices_sdk.observability.logging import (
    LoggingConfig,
    ELKConfig,
    SecurityConfig,
    RetentionConfig,
    LogLevel,
    LogFormat,
    ComplianceStandard,
    create_logging_config
)

from fastapi_microservices_sdk.observability.logging.structured_logger import (
    StructuredLogger,
    LogEventType,
    create_logger,
    set_correlation_id,
    set_request_id,
    set_user_id,
    generate_correlation_id
)

from fastapi_microservices_sdk.observability.logging.formatters import (
    JSONFormatter,
    ELKFormatter,
    ComplianceFormatter,
    StructuredFormatter,
    create_formatter
)

from fastapi_microservices_sdk.observability.logging.handlers import (
    ConsoleHandler,
    FileHandler,
    BufferedHandler,
    RetryHandler,
    AsyncHandler,
    create_handler
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_basic_structured_logging():
    """Demonstrate basic structured logging capabilities."""
    logger.info("=== Basic Structured Logging Demo ===")
    
    # Create logging configuration
    config = LoggingConfig(
        service_name="logging-demo-service",
        service_version="1.0.0",
        environment="demo",
        root_level=LogLevel.DEBUG,
        log_format=LogFormat.JSON,
        enable_trace_correlation=True,
        console_output=True
    )
    
    # Create structured logger
    structured_logger = create_logger("demo.basic", config)
    
    # Set correlation context
    correlation_id = generate_correlation_id()
    request_id = f"req-{random.randint(1000, 9999)}"
    user_id = "user-demo-123"
    
    set_correlation_id(correlation_id)
    set_request_id(request_id)
    set_user_id(user_id)
    
    logger.info(f"Using correlation ID: {correlation_id}")
    
    # Demonstrate different log levels
    structured_logger.debug("Debug message with correlation", extra={
        'debug_info': 'This is debug information',
        'component': 'demo_component'
    })
    
    structured_logger.info("Info message with structured data", extra={
        'operation': 'user_login',
        'success': True,
        'duration_ms': 150.5
    })
    
    structured_logger.warning("Warning message", extra={
        'warning_type': 'rate_limit_approaching',
        'current_rate': 85,
        'limit': 100
    })
    
    # Demonstrate error logging with exception
    try:
        raise ValueError("Simulated error for demonstration")
    except ValueError as e:
        structured_logger.error("Error occurred during operation", exception=e, extra={
            'operation': 'data_processing',
            'input_size': 1000,
            'processed_items': 750
        })
    
    # Demonstrate critical logging
    structured_logger.critical("Critical system event", extra={
        'event_type': 'system_failure',
        'affected_services': ['auth', 'database'],
        'estimated_downtime': '5 minutes'
    })
    
    # Get logger metrics
    metrics = structured_logger.get_metrics()
    logger.info(f"Logger metrics: {metrics}")


async def demonstrate_event_types():
    """Demonstrate different event types."""
    logger.info("=== Event Types Demo ===")
    
    config = LoggingConfig(
        service_name="event-demo-service",
        log_format=LogFormat.STRUCTURED
    )
    
    structured_logger = create_logger("demo.events", config)
    
    # Set context
    set_correlation_id(generate_correlation_id())
    set_user_id("user-events-456")
    
    # Audit events
    structured_logger.audit("User login successful", extra={
        'user_id': 'user-events-456',
        'login_method': 'oauth2',
        'ip_address': '192.168.1.100',
        'user_agent': 'Mozilla/5.0...'
    })
    
    structured_logger.audit("Data access", extra={
        'resource_type': 'customer_data',
        'resource_id': 'cust-789',
        'access_type': 'read',
        'authorized': True
    })
    
    # Security events
    structured_logger.security("Suspicious activity detected", extra={
        'activity_type': 'multiple_failed_logins',
        'source_ip': '10.0.0.50',
        'attempt_count': 5,
        'time_window': '5 minutes'
    })
    
    structured_logger.security("Permission escalation attempt", extra={
        'user_id': 'user-suspicious-999',
        'requested_permission': 'admin',
        'current_permission': 'user',
        'blocked': True
    })
    
    # Performance events
    structured_logger.performance("Database query performance", 
                                duration_ms=250.7, extra={
        'query_type': 'SELECT',
        'table': 'users',
        'rows_returned': 150,
        'cache_hit': False
    })
    
    structured_logger.performance("API endpoint performance",
                                duration_ms=89.3, extra={
        'endpoint': '/api/v1/users',
        'method': 'GET',
        'status_code': 200,
        'response_size_bytes': 2048
    })
    
    # Business events
    structured_logger.business("Order completed", extra={
        'order_id': 'ord-12345',
        'customer_id': 'cust-789',
        'total_amount': 299.99,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'items_count': 3
    })
    
    structured_logger.business("Subscription upgraded", extra={
        'subscription_id': 'sub-456',
        'user_id': 'user-events-456',
        'old_plan': 'basic',
        'new_plan': 'premium',
        'effective_date': '2024-01-01'
    })


async def demonstrate_data_masking():
    """Demonstrate data masking and PII protection."""
    logger.info("=== Data Masking Demo ===")
    
    # Configure with data masking enabled
    security_config = SecurityConfig(
        enable_data_masking=True,
        enable_pii_protection=True,
        masking_patterns={
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
        },
        masking_replacement="***MASKED***",
        pii_replacement="***PII***"
    )
    
    config = LoggingConfig(
        service_name="masking-demo-service",
        log_format=LogFormat.JSON,
        security_config=security_config
    )
    
    structured_logger = create_logger("demo.masking", config)
    
    # Log messages with sensitive data
    structured_logger.info("User registration with sensitive data", extra={
        'user_email': 'user@example.com',  # Will be masked
        'phone_number': '555-123-4567',    # Will be masked
        'password': 'secret123',           # Will be masked as PII
        'credit_card': '4111-1111-1111-1111',  # Will be masked
        'user_name': 'John Doe',           # Will be masked as PII
        'registration_ip': '192.168.1.100'
    })
    
    structured_logger.info("Payment processing with card info: 4111-1111-1111-1111", extra={
        'amount': 99.99,
        'currency': 'USD',
        'merchant_id': 'merch-123'
    })
    
    structured_logger.warning("Failed login attempt for user@example.com from IP 10.0.0.1")


async def demonstrate_compliance_logging():
    """Demonstrate compliance logging features."""
    logger.info("=== Compliance Logging Demo ===")
    
    # Configure for compliance
    config = LoggingConfig(
        service_name="compliance-demo-service",
        log_format=LogFormat.COMPLIANCE,
        compliance_standards=[
            ComplianceStandard.GDPR,
            ComplianceStandard.HIPAA,
            ComplianceStandard.SOX
        ],
        enable_audit_logging=True
    )
    
    # Create compliance formatter
    formatter = ComplianceFormatter(config, config.compliance_standards)
    
    structured_logger = create_logger("demo.compliance", config)
    
    # Set compliance context
    set_correlation_id(generate_correlation_id())
    set_user_id("compliance-user-789")
    
    # GDPR compliance events
    structured_logger.audit("Data subject access request", extra={
        'request_type': 'data_access',
        'data_subject_id': 'ds-123',
        'requested_data_types': ['personal_info', 'transaction_history'],
        'compliance_standard': 'GDPR',
        'processing_lawful_basis': 'consent'
    })
    
    structured_logger.audit("Personal data deletion", extra={
        'request_type': 'data_deletion',
        'data_subject_id': 'ds-456',
        'deleted_data_types': ['profile', 'preferences'],
        'compliance_standard': 'GDPR',
        'retention_period_expired': True
    })
    
    # HIPAA compliance events
    structured_logger.audit("Medical record access", extra={
        'patient_id': 'patient-789',
        'healthcare_provider_id': 'hcp-123',
        'record_type': 'diagnosis',
        'access_purpose': 'treatment',
        'compliance_standard': 'HIPAA',
        'authorization_present': True
    })
    
    # SOX compliance events
    structured_logger.audit("Financial data modification", extra={
        'financial_record_id': 'fin-456',
        'modification_type': 'correction',
        'approver_id': 'approver-123',
        'compliance_standard': 'SOX',
        'audit_trail_preserved': True
    })


async def demonstrate_elk_integration():
    """Demonstrate ELK stack integration."""
    logger.info("=== ELK Integration Demo ===")
    
    # Configure ELK integration
    elk_config = ELKConfig(
        elasticsearch_hosts=["http://localhost:9200"],
        elasticsearch_index_pattern="logs-demo-{date}",
        logstash_host="localhost",
        logstash_port=5044,
        kibana_host="http://localhost:5601",
        pipeline_batch_size=50,
        pipeline_flush_interval=10.0
    )
    
    config = LoggingConfig(
        service_name="elk-demo-service",
        log_format=LogFormat.ELK,
        enable_elk=True,
        elk_config=elk_config
    )
    
    structured_logger = create_logger("demo.elk", config)
    
    # Set context for ELK
    set_correlation_id(generate_correlation_id())
    set_request_id(f"elk-req-{random.randint(1000, 9999)}")
    
    # Generate various log events for ELK
    for i in range(10):
        event_type = random.choice(['user_action', 'system_event', 'error', 'performance'])
        
        if event_type == 'user_action':
            structured_logger.business(f"User action {i}", extra={
                'action_type': random.choice(['login', 'logout', 'purchase', 'view']),
                'user_id': f'user-{random.randint(100, 999)}',
                'session_duration': random.randint(60, 3600),
                'page_views': random.randint(1, 20)
            })
        
        elif event_type == 'system_event':
            structured_logger.info(f"System event {i}", extra={
                'component': random.choice(['auth', 'database', 'cache', 'queue']),
                'status': random.choice(['healthy', 'degraded', 'recovering']),
                'cpu_usage': random.uniform(10, 90),
                'memory_usage': random.uniform(20, 80)
            })
        
        elif event_type == 'error':
            structured_logger.error(f"Error event {i}", extra={
                'error_code': f'ERR-{random.randint(1000, 9999)}',
                'error_category': random.choice(['validation', 'network', 'database', 'auth']),
                'retry_count': random.randint(0, 3),
                'user_impact': random.choice(['none', 'low', 'medium', 'high'])
            })
        
        elif event_type == 'performance':
            structured_logger.performance(f"Performance event {i}",
                                        duration_ms=random.uniform(10, 500), extra={
                'operation': random.choice(['db_query', 'api_call', 'file_io', 'computation']),
                'cache_hit_rate': random.uniform(0.7, 0.95),
                'throughput_rps': random.randint(100, 1000)
            })
        
        # Small delay to simulate real-world timing
        await asyncio.sleep(0.1)
    
    logger.info("ELK integration demo completed - check Kibana for visualizations")


async def demonstrate_advanced_handlers():
    """Demonstrate advanced handler configurations."""
    logger.info("=== Advanced Handlers Demo ===")
    
    config = LoggingConfig(
        service_name="handlers-demo-service",
        buffer_size=5,
        flush_interval=2.0
    )
    
    # Create different formatters
    json_formatter = JSONFormatter(config)
    structured_formatter = StructuredFormatter(config)
    
    # Create base handlers
    console_handler = ConsoleHandler(config, json_formatter)
    
    # Create file handler with rotation
    file_handler = FileHandler(config, structured_formatter, file_path="demo.log")
    
    # Create buffered handler
    buffered_handler = BufferedHandler(
        config, json_formatter, console_handler,
        buffer_size=3, flush_interval=1.0
    )
    
    # Create retry handler
    retry_handler = RetryHandler(
        config, json_formatter, file_handler,
        max_retries=3, retry_delay=0.5
    )
    
    # Create async handler
    async_handler = AsyncHandler(
        config, json_formatter, console_handler,
        queue_size=100, worker_count=2
    )
    
    logger.info("Testing different handlers...")
    
    # Create test records
    from fastapi_microservices_sdk.observability.logging.structured_logger import LogRecord
    
    test_records = []
    for i in range(10):
        record = LogRecord(
            timestamp=f"2024-01-01T12:00:{i:02d}Z",
            level="INFO",
            logger_name="demo.handlers",
            message=f"Test message {i}",
            service_name="handlers-demo-service",
            service_version="1.0.0",
            environment="demo",
            correlation_id=generate_correlation_id()
        )
        test_records.append(record)
    
    # Test console handler
    logger.info("Testing console handler...")
    for record in test_records[:3]:
        console_handler.emit(record)
    
    # Test buffered handler
    logger.info("Testing buffered handler...")
    for record in test_records[3:6]:
        buffered_handler.emit(record)
    
    # Wait for buffer flush
    await asyncio.sleep(1.5)
    
    # Test async handler
    logger.info("Testing async handler...")
    for record in test_records[6:]:
        async_handler.emit(record)
    
    # Flush all handlers
    buffered_handler.flush()
    async_handler.flush()
    
    # Get metrics
    logger.info("Handler Metrics:")
    for handler_name, handler in [
        ("Console", console_handler),
        ("Buffered", buffered_handler),
        ("Retry", retry_handler),
        ("Async", async_handler)
    ]:
        metrics = handler.get_metrics()
        logger.info(f"  {handler_name}: {metrics}")
    
    # Cleanup
    buffered_handler.close()
    retry_handler.close()
    async_handler.close()
    file_handler.close()


async def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring with structured logging."""
    logger.info("=== Performance Monitoring Demo ===")
    
    config = LoggingConfig(
        service_name="performance-demo-service",
        log_format=LogFormat.JSON,
        async_logging=True
    )
    
    structured_logger = create_logger("demo.performance", config)
    
    # Set context
    set_correlation_id(generate_correlation_id())
    
    # Simulate various operations with performance logging
    operations = [
        ("database_query", 0.05, 0.02),
        ("api_call", 0.1, 0.05),
        ("file_processing", 0.2, 0.1),
        ("cache_operation", 0.01, 0.005),
        ("computation", 0.15, 0.08)
    ]
    
    for operation_name, base_duration, variance in operations:
        for i in range(5):
            # Simulate operation
            duration = base_duration + random.uniform(-variance, variance)
            await asyncio.sleep(duration)
            
            # Log performance
            structured_logger.performance(
                f"{operation_name} completed",
                duration_ms=duration * 1000,
                extra={
                    'operation': operation_name,
                    'iteration': i + 1,
                    'success': random.choice([True, True, True, False]),  # 75% success rate
                    'cache_hit': random.choice([True, False]),
                    'resource_usage': {
                        'cpu_percent': random.uniform(10, 80),
                        'memory_mb': random.uniform(50, 200),
                        'io_operations': random.randint(1, 10)
                    }
                }
            )
    
    # Log performance summary
    structured_logger.info("Performance monitoring session completed", extra={
        'total_operations': len(operations) * 5,
        'session_duration_ms': sum(op[1] for op in operations) * 5 * 1000,
        'operations_tested': [op[0] for op in operations]
    })


async def main():
    """Main demonstration function."""
    logger.info("Starting Structured Logging with ELK Integration Example")
    logger.info("=" * 70)
    
    try:
        # Run all demonstrations
        await demonstrate_basic_structured_logging()
        await demonstrate_event_types()
        await demonstrate_data_masking()
        await demonstrate_compliance_logging()
        await demonstrate_elk_integration()
        await demonstrate_advanced_handlers()
        await demonstrate_performance_monitoring()
        
        logger.info("=" * 70)
        logger.info("Structured Logging Example completed successfully!")
        
        logger.info("\nKey Features Demonstrated:")
        logger.info("✅ JSON structured logging with schema validation")
        logger.info("✅ Trace correlation with OpenTelemetry integration")
        logger.info("✅ Data masking and PII protection")
        logger.info("✅ Compliance logging (GDPR, HIPAA, SOX)")
        logger.info("✅ ELK stack integration and formatting")
        logger.info("✅ Advanced handlers (buffered, retry, async)")
        logger.info("✅ Performance monitoring and metrics")
        logger.info("✅ Multiple event types (audit, security, business)")
        
        logger.info("\nTo integrate with ELK stack:")
        logger.info("1. Start Elasticsearch: docker run -p 9200:9200 elasticsearch:7.17.0")
        logger.info("2. Start Logstash: docker run -p 5044:5044 logstash:7.17.0")
        logger.info("3. Start Kibana: docker run -p 5601:5601 kibana:7.17.0")
        logger.info("4. Configure log shipping to Logstash endpoint")
        
    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
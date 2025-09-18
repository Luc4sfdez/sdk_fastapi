"""
Example usage of Event Service Template

This example demonstrates how to use the Event Service Template to generate
a complete event-driven microservice with Event Sourcing, CQRS, and Saga patterns.
"""

import asyncio
from pathlib import Path
from fastapi_microservices_sdk.templates.builtin_templates.event_service import EventServiceTemplate


async def main():
    """Main example function"""
    
    # Initialize the template
    template = EventServiceTemplate()
    
    # Define template variables
    variables = {
        "service_name": "order_service",
        "service_description": "Order management service with event sourcing",
        "service_version": "1.0.0",
        "service_port": 8001,
        "message_broker": "kafka",
        "event_store": "postgresql",
        "aggregates": [
            {
                "name": "Order",
                "events": ["OrderCreated", "OrderUpdated", "OrderCancelled", "OrderCompleted"],
                "commands": ["CreateOrder", "UpdateOrder", "CancelOrder", "CompleteOrder"]
            },
            {
                "name": "Payment",
                "events": ["PaymentInitiated", "PaymentCompleted", "PaymentFailed"],
                "commands": ["InitiatePayment", "CompletePayment", "RefundPayment"]
            }
        ],
        "events": [
            {
                "name": "OrderCreated",
                "version": "1.0",
                "schema": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "customer_id": {"type": "string"},
                        "items": {"type": "array"},
                        "total_amount": {"type": "number"}
                    }
                }
            }
        ],
        "sagas": [
            {
                "name": "OrderProcessingSaga",
                "steps": [
                    {"type": "command", "name": "ValidateOrder"},
                    {"type": "command", "name": "ReserveInventory"},
                    {"type": "command", "name": "ProcessPayment"},
                    {"type": "command", "name": "ShipOrder"}
                ],
                "timeout": 600
            }
        ],
        "enable_snapshots": True,
        "snapshot_frequency": 50,
        "enable_sagas": True,
        "enable_projections": True,
        "enable_monitoring": True,
        "enable_tracing": True,
        "enable_cqrs": True,
        "retention_days": 730,
        "batch_size": 500
    }
    
    # Validate variables
    print("🔍 Validating template variables...")
    validation_errors = template.validate_variables(variables)
    
    if validation_errors:
        print("❌ Validation errors found:")
        for error in validation_errors:
            print(f"  - {error}")
        return
    
    print("✅ Variables validated successfully!")
    
    # Generate the service
    output_dir = Path("./generated_services/order_service")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Generating event service at {output_dir}...")
    
    try:
        generated_files = template.generate_files(variables, output_dir)
        
        print(f"✅ Successfully generated {len(generated_files)} files!")
        print("\n📁 Generated files:")
        
        for file_path in sorted(generated_files):
            relative_path = file_path.relative_to(output_dir)
            print(f"  - {relative_path}")
        
        print(f"\n🎉 Event service '{variables['service_name']}' generated successfully!")
        print(f"📍 Location: {output_dir.absolute()}")
        
        # Display next steps
        print("\n🚀 Next steps:")
        print("1. Navigate to the generated directory:")
        print(f"   cd {output_dir}")
        print("\n2. Install dependencies:")
        print("   pip install -r requirements.txt")
        print("\n3. Copy and configure environment:")
        print("   cp .env.template .env")
        print("   # Edit .env with your configuration")
        print("\n4. Start dependencies:")
        print("   docker-compose up -d postgresql kafka")
        print("\n5. Run the service:")
        print("   python -m uvicorn app.main:app --reload")
        print("\n6. Access the service:")
        print(f"   - API: http://localhost:{variables['service_port']}")
        print(f"   - Docs: http://localhost:{variables['service_port']}/docs")
        print(f"   - Health: http://localhost:{variables['service_port']}/health")
        
    except Exception as e:
        print(f"❌ Error generating service: {e}")
        raise


def demonstrate_template_features():
    """Demonstrate template features"""
    
    print("🎯 Event Service Template Features:")
    print("\n📋 Core Features:")
    print("  ✅ Event Sourcing with event store")
    print("  ✅ CQRS (Command Query Responsibility Segregation)")
    print("  ✅ Saga pattern for distributed transactions")
    print("  ✅ Event streaming and message broker integration")
    print("  ✅ Snapshot management for performance")
    print("  ✅ Event versioning and migration support")
    print("  ✅ Distributed tracing and monitoring")
    print("  ✅ Replay and recovery mechanisms")
    
    print("\n🔧 Supported Technologies:")
    print("  📨 Message Brokers: Kafka, RabbitMQ, Redis, NATS")
    print("  🗄️  Event Stores: PostgreSQL, MongoDB, EventStore")
    print("  📊 Monitoring: Prometheus metrics, health checks")
    print("  🔍 Tracing: OpenTelemetry integration")
    
    print("\n🏗️ Generated Structure:")
    print("  📁 app/")
    print("    📁 events/          # Domain events")
    print("    📁 aggregates/      # Aggregate roots")
    print("    📁 commands/        # CQRS commands")
    print("    📁 queries/         # CQRS queries")
    print("    📁 projections/     # Read model projections")
    print("    📁 sagas/           # Saga orchestration")
    print("    📁 event_store/     # Event store implementation")
    print("    📁 message_broker/  # Message broker integration")
    print("    📁 api/             # REST API endpoints")
    print("    📁 monitoring/      # Metrics and health checks")
    print("  📁 tests/             # Comprehensive test suite")
    print("  📁 docker/            # Docker configuration")
    print("  📁 k8s/               # Kubernetes manifests")
    print("  📁 docs/              # Documentation")


def show_configuration_examples():
    """Show configuration examples"""
    
    print("\n⚙️ Configuration Examples:")
    
    print("\n1. 📦 E-commerce Order Service:")
    print("""
    {
        "service_name": "order_service",
        "message_broker": "kafka",
        "event_store": "postgresql",
        "aggregates": [
            {
                "name": "Order",
                "events": ["OrderCreated", "OrderShipped", "OrderDelivered"],
                "commands": ["CreateOrder", "ShipOrder", "DeliverOrder"]
            }
        ],
        "enable_sagas": true,
        "enable_projections": true
    }
    """)
    
    print("\n2. 🏦 Banking Account Service:")
    print("""
    {
        "service_name": "account_service",
        "message_broker": "rabbitmq",
        "event_store": "eventstore",
        "aggregates": [
            {
                "name": "Account",
                "events": ["AccountOpened", "MoneyDeposited", "MoneyWithdrawn"],
                "commands": ["OpenAccount", "DepositMoney", "WithdrawMoney"]
            }
        ],
        "enable_snapshots": true,
        "snapshot_frequency": 100
    }
    """)
    
    print("\n3. 📋 Task Management Service:")
    print("""
    {
        "service_name": "task_service",
        "message_broker": "nats",
        "event_store": "mongodb",
        "aggregates": [
            {
                "name": "Task",
                "events": ["TaskCreated", "TaskAssigned", "TaskCompleted"],
                "commands": ["CreateTask", "AssignTask", "CompleteTask"]
            }
        ],
        "enable_cqrs": true,
        "enable_monitoring": true
    }
    """)


if __name__ == "__main__":
    print("🎯 Event Service Template Example")
    print("=" * 50)
    
    # Show template features
    demonstrate_template_features()
    
    # Show configuration examples
    show_configuration_examples()
    
    # Run the main example
    print("\n🚀 Running Event Service Generation Example...")
    print("=" * 50)
    
    asyncio.run(main())
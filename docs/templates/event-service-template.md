# Event Service Template

## Overview

The Event Service Template generates production-ready event-driven microservices with comprehensive Event Sourcing, CQRS (Command Query Responsibility Segregation), and Saga pattern implementations.

## Features

### Core Capabilities
- **Event Sourcing**: Complete event sourcing implementation with event store and replay capabilities
- **CQRS Pattern**: Command Query Responsibility Segregation with separate read/write models
- **Saga Pattern**: Distributed transaction management with compensation
- **Event Streaming**: Integration with multiple message brokers
- **Snapshot Management**: Performance optimization with aggregate snapshots
- **Event Versioning**: Migration support between event versions
- **Distributed Tracing**: End-to-end request tracing
- **Monitoring**: Comprehensive metrics and health checks

### Supported Technologies

#### Message Brokers
- **Kafka**: Apache Kafka with high-throughput streaming
- **RabbitMQ**: AMQP-based reliable messaging
- **Redis**: Redis Pub/Sub for lightweight messaging
- **NATS**: Cloud-native messaging system

#### Event Stores
- **PostgreSQL**: Relational database with JSONB support
- **MongoDB**: Document-based event storage
- **EventStore**: Purpose-built event store database

## Usage

### Basic Usage

```python
from fastapi_microservices_sdk.templates.builtin_templates.event_service import EventServiceTemplate

# Initialize template
template = EventServiceTemplate()

# Define configuration
variables = {
    "service_name": "order_service",
    "service_description": "Order management with event sourcing",
    "message_broker": "kafka",
    "event_store": "postgresql",
    "aggregates": [
        {
            "name": "Order",
            "events": ["OrderCreated", "OrderUpdated", "OrderCompleted"],
            "commands": ["CreateOrder", "UpdateOrder", "CompleteOrder"]
        }
    ]
}

# Generate service
files = template.generate_files(variables, output_dir)
```

### CLI Usage

```bash
# Interactive creation
fastapi-ms create --template event_service

# Non-interactive
fastapi-ms create --name order-service --template event_service --no-interactive
```

## Configuration

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `service_name` | string | Name of the service |
| `service_description` | string | Service description |
| `message_broker` | string | Message broker type (kafka, rabbitmq, redis, nats) |
| `event_store` | string | Event store type (postgresql, mongodb, eventstore) |
| `aggregates` | array | List of domain aggregates |

### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `service_version` | string | "1.0.0" | Service version |
| `service_port` | integer | 8000 | Service port |
| `enable_snapshots` | boolean | true | Enable aggregate snapshots |
| `snapshot_frequency` | integer | 100 | Events between snapshots |
| `enable_sagas` | boolean | true | Enable saga pattern |
| `enable_projections` | boolean | true | Enable read model projections |
| `enable_monitoring` | boolean | true | Enable monitoring |
| `retention_days` | integer | 365 | Event retention period |

### Aggregate Configuration

```json
{
  "name": "Order",
  "events": ["OrderCreated", "OrderUpdated", "OrderCompleted"],
  "commands": ["CreateOrder", "UpdateOrder", "CompleteOrder"]
}
```

## Generated Structure

```
generated_service/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── events/                # Domain events
│   │   ├── base.py           # Base event classes
│   │   └── *.py              # Specific events
│   ├── aggregates/           # Aggregate roots
│   │   ├── base.py          # Base aggregate classes
│   │   └── *.py             # Specific aggregates
│   ├── commands/            # CQRS commands
│   ├── queries/             # CQRS queries
│   ├── projections/         # Read model projections
│   ├── sagas/               # Saga orchestration
│   ├── event_store/         # Event store implementation
│   ├── message_broker/      # Message broker integration
│   └── api/                 # REST API endpoints
├── tests/                   # Test suite
├── docker/                  # Docker configuration
├── k8s/                     # Kubernetes manifests
└── docs/                    # Documentation
```

## Architecture Patterns

### Event Sourcing

The template implements complete event sourcing with:

- **Event Store**: Persistent storage for all domain events
- **Event Replay**: Ability to rebuild aggregate state from events
- **Event Versioning**: Support for evolving event schemas
- **Snapshots**: Performance optimization for large event streams

### CQRS (Command Query Responsibility Segregation)

- **Commands**: Modify state through aggregates
- **Queries**: Read from optimized projections
- **Separation**: Clear separation of read and write models
- **Scalability**: Independent scaling of read and write sides

### Saga Pattern

- **Orchestration**: Coordinate distributed transactions
- **Compensation**: Automatic rollback on failures
- **Timeout Handling**: Handle long-running processes
- **State Management**: Track saga execution state

## Examples

### E-commerce Order Service

```python
variables = {
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
    "sagas": [
        {
            "name": "OrderProcessingSaga",
            "steps": [
                {"type": "command", "name": "ValidateOrder"},
                {"type": "command", "name": "ProcessPayment"},
                {"type": "command", "name": "ShipOrder"}
            ]
        }
    ]
}
```

### Banking Account Service

```python
variables = {
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
    "enable_snapshots": True,
    "snapshot_frequency": 50
}
```

## Best Practices

### Event Design
- Keep events immutable and append-only
- Include all necessary data in events
- Use meaningful event names
- Version events for schema evolution

### Aggregate Design
- Keep aggregates small and focused
- Ensure aggregate consistency boundaries
- Use domain-driven design principles
- Implement proper validation

### Performance
- Use snapshots for large event streams
- Implement proper indexing
- Consider event archiving strategies
- Monitor event store performance

## Monitoring and Observability

The generated service includes:

- **Metrics**: Prometheus metrics for events, commands, and sagas
- **Health Checks**: Comprehensive health monitoring
- **Tracing**: Distributed tracing with OpenTelemetry
- **Logging**: Structured logging with correlation IDs

## Deployment

### Docker

```bash
docker-compose up --build
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

## Testing

The template generates comprehensive tests:

- **Unit Tests**: Test aggregates, events, and commands
- **Integration Tests**: Test event store and message broker
- **Performance Tests**: Load testing for event processing
- **Security Tests**: Validate security measures

## Troubleshooting

### Common Issues

1. **Event Store Connection**: Check connection strings and credentials
2. **Message Broker**: Verify broker configuration and connectivity
3. **Event Replay**: Ensure proper event ordering and versioning
4. **Performance**: Monitor snapshot frequency and event store performance

### Debug Mode

Enable debug logging:

```bash
DEBUG=true LOG_LEVEL=DEBUG python -m uvicorn app.main:app
```

## References

- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Domain-Driven Design](https://domainlanguage.com/ddd/)
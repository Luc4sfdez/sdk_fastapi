# fs-user-service

FacturaScripts User Service - Gestión de usuarios y autenticación

## Features

- ⚡ **FastAPI**: Modern, fast web framework for building APIs

- 🗄️ **Database**: Postgresql integration with async support


- 🔄 **Redis**: Caching and session management


- 📊 **Observability**: Comprehensive monitoring and logging


- 🔒 **Security**: Built-in authentication and authorization

- 🐳 **Docker**: Containerized deployment
- 🧪 **Testing**: Comprehensive test suite
- 📚 **Documentation**: Auto-generated API documentation

## Quick Start

### Prerequisites

- Python 3.8+
- Docker (optional)

- PostgreSQL


- Redis


### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fs-user-service
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```


5. Set up the database:
```bash
# Create database and run migrations
alembic upgrade head
```


6. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Alternative Documentation: `http://localhost:8000/redoc`

### Docker Deployment

1. Build the image:
```bash
docker-compose build
```

2. Run the services:
```bash
docker-compose up -d
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - API documentation (ReDoc)

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Type Checking

```bash
mypy .
```

## Configuration

The application uses environment variables for configuration. See `.env.example` for available options.

Key configuration options:

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `ENVIRONMENT`: Environment (development/production)

- `DATABASE_URL`: Database connection URL


- `REDIS_URL`: Redis connection URL

- `SECRET_KEY`: Secret key for security features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Support

For support and questions, please open an issue in the repository.
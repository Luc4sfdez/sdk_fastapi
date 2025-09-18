# Auth Service

Dedicated JWT Authentication Service for FastAPI Microservices SDK.

## Features

- JWT token generation and validation
- Access and refresh token support
- Token blacklist for logout
- Integration with user service
- Health checks
- CORS support

## Endpoints

- `POST /login` - User authentication
- `POST /logout` - User logout (token blacklist)
- `POST /refresh` - Refresh access token
- `POST /validate` - Validate JWT token
- `GET /me` - Get current user info
- `GET /health` - Health check

## Configuration

Environment variables:
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration (default: 7)
- `USER_SERVICE_URL` - URL of user service (default: http://localhost:8002)

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Docker

```bash
# Build image
docker build -t auth-service .

# Run container
docker run -p 8001:8001 auth-service
```
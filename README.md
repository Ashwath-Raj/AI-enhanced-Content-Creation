# FastAPI PostgreSQL Template

A modern FastAPI project template with async SQLAlchemy, Alembic migrations, JWT authentication, and Dockerized PostgreSQL. Includes user registration, login, and secure endpoints.

## Features
- FastAPI (async)
- PostgreSQL (Docker)
- SQLAlchemy 2.x ORM
- Alembic migrations
- JWT authentication (register, login, protected endpoints)
- Password hashing (bcrypt)
- Environment variable configuration

## Requirements
- Python 3.12+
- Docker and Docker Compose

## Setup Instructions

### 1. Clone the repository

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start PostgreSQL with Docker
```bash
docker compose up -d postgres
```

### 5. Configure environment variables
Edit `.env` for database and JWT settings, you can visit my `JWT Secret Generator` at this url: [JWT Secret Generator](https://bngiahuy.github.io/jwt-secret-generator/)
```
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=postgres
PG_DB=db
SQLALCHEMY_ECHO=true
JWT_SECRET=supersecretkey
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
```



### 6. Run Alembic migrations
```bash
alembic upgrade head
```

### 7. Start the FastAPI server
```bash
python -m src.main
```

### 8. Access Swagger UI
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to explore and test the API endpoints.

## API Endpoints
- `POST /api/v1/register` — Register a new user
- `POST /api/v1/login` — Login and get JWT token
- `GET /api/v1/users/me` — Get current user info (JWT required)

## Notes
- All passwords are securely hashed using bcrypt.
- JWT tokens are required for protected endpoints. Use the "Authorize" button in Swagger UI.
- For development, you can change settings in `.env`.

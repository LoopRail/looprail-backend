# Looprail Backend

LoopRail's backend service.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.13+
- uv

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your_username/looprail-backend.git
   cd looprail-backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   uv sync
   ```

3. Create a `.env` file from the example and fill in the required environment variables:
   ```bash
   cp config/.env.example .env
   ```

### Running the Application

To run the application, use the following command:

```bash
uvicorn src.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

## API Endpoints

The following endpoints are available:

- `POST /api/auth/register`: Register a new user.
- `GET /api/users/{user_id}`: Get user details by user ID.

## Project Structure

The project is structured as follows:

```
├── alembic.ini
├── migrations
├── pyproject.toml
├── README.md
├── src
│   ├── api
│   ├── dtos
│   ├── infrastructure
│   ├── models
│   ├── types
│   ├── usecases
│   └── utils
└── tests
```

## Dependencies

The main dependencies are:

- [FastAPI](https://fastapi.tiangolo.com/): A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.
- [SQLModel](https://sqlmodel.tiangolo.com/): A library for interacting with SQL databases from Python code, with Python objects.
- [Alembic](https://alembic.sqlalchemy.org/en/latest/): A lightweight database migration tool for usage with the SQLAlchemy Database Toolkit for Python.
- [uv](https://github.com/astral-sh/uv): An extremely fast Python package installer and resolver, written in Rust.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

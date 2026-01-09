# Use the official Python image.
FROM python:3.13-slim

# Set the working directory in the container.
WORKDIR /app

ENV PYTHONPATH /app

# Install uv
RUN pip install uv

# Copy dependency definition files first for better caching.
COPY pyproject.toml uv.lock ./

# Install dependencies using uv.
RUN uv sync 

# Copy the rest of the project files into the container.
COPY . ./

# Expose the port the app runs on.
EXPOSE 8000

# Command to run the application.
# CMD ["uv", "run","-m", "src.main"]

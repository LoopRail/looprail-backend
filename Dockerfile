# Use the official Python image.
FROM python:3.13-slim

# Set the working directory in the container.
WORKDIR /app

# Install uv
RUN pip install uv

# Copy the project files into the container.
COPY . .

# Install dependencies using uv.
RUN uv pip install --system --no-cache -r pyproject.toml

# Expose the port the app runs on.
EXPOSE 8000

# Command to run the application.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

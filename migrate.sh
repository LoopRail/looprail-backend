#!/bin/bash
uv run alembic revision --autogenerate -m "$1"

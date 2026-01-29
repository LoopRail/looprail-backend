#!/bin/bash

ENVIRONMENT="dev" 

for i in "$@"; do
  case $i in
    --prod)
      ENVIRONMENT="prod"
      shift 
      ;;
    --staging)
      ENVIRONMENT="staging"
      shift 
      ;;
    --dev)
      ENVIRONMENT="dev"
      shift 
      ;;
    *)
      ;;
  esac
done

echo "Running migrations for environment: $ENVIRONMENT"
ENVIRONMENT=$ENVIRONMENT uv run alembic upgrade head


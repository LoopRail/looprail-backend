#!/bin/bash

# push.sh - Automates pushing current branch to dev/prod and switching to main.

TARGET=$1
CURRENT_BRANCH=$(git branch --show-current)

# 1. Push current changes to origin main
echo "Pushing $CURRENT_BRANCH to origin/main..."
git push origin "$CURRENT_BRANCH:main"

sync_env() {
    ENV=$1
    echo "Updating $ENV with latest from main..."
    git checkout "$ENV"
    git pull origin main
    git push origin "$ENV"
}

case $TARGET in
    dev)
        sync_env "dev"
        ;;
    prod)
        sync_env "prod"
        ;;
    *)
        sync_env "dev"
        sync_env "prod"
        ;;
esac

echo "Switching back to $CURRENT_BRANCH..."
git checkout "$CURRENT_BRANCH"

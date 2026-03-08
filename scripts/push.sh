#!/bin/bash

# push.sh - Automates pushing current branch to dev/prod and switching to main.

TARGET=$1
CURRENT_BRANCH=$(git branch --show-current)

if [ -z "$TARGET" ]; then
    echo "Usage: ./scripts/push.sh [dev|prod|all]"
    exit 1
fi

push_to_env() {
    ENV=$1
    echo "Pushing $CURRENT_BRANCH to $ENV..."
    git push origin "$CURRENT_BRANCH:$ENV"
}

case $TARGET in
    dev)
        push_to_env "dev"
        ;;
    prod)
        push_to_env "prod"
        ;;
    all)
        push_to_env "dev"
        push_to_env "prod"
        ;;
    *)
        echo "Invalid target: $TARGET. Use dev, prod, or all."
        exit 1
        ;;
esac

echo "Switching back to main..."
git checkout main

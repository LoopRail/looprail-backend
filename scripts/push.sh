#!/bin/bash

# push.sh - Automates pushing current branch to dev/prod and switching to main.

TARGET=$1
CURRENT_BRANCH=$(git branch --show-current)

if [ -z "$TARGET" ]; then
    echo "Usage: ./scripts/push.sh [dev|prod]"
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
    *)
        push_to_env "dev"
        push_to_env "prod"
        ;;
esac

echo "Switching back to main..."
git checkout main

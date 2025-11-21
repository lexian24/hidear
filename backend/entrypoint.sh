#!/bin/bash

# Configure git with HF token if available
if [ -n "$HF_TOKEN" ]; then
  echo "Configuring git credentials for HuggingFace..."
  git config --global credential.helper store
  echo "https://oauth2:${HF_TOKEN}@huggingface.co" > ~/.git-credentials
  git config --global user.email "worker@hidear.local"
  git config --global user.name "Hidear Worker"
fi

# Execute the command passed to the container
# If no command provided, start the default Celery worker
if [ $# -eq 0 ]; then
  exec celery -A celery_app worker --loglevel=info --concurrency=2
else
  exec "$@"
fi

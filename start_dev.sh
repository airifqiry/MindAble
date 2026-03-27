#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source "venv/bin/activate"

# Prevent local proxy config from blocking Anthropic/API calls.
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

python manage.py runserver

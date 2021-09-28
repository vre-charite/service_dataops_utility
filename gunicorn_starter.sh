#!/bin/sh

gunicorn -c gunicorn_config.py "app:app" -k uvicorn.workers.UvicornWorker --timeout 3000

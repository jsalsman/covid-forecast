#!/bin/bash
source .venv/bin/activate
python -u -m flask --app app run --host=0.0.0.0 -p ${PORT:-8080} --debug
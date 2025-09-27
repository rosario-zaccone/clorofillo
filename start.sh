#!/bin/bash
poetry run python src/clorofillo/app.py &
poetry run python src/clorofillo/io_app.py &
wait

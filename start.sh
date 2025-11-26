sudo pigpiod || true
sleep 1

poetry run python src/clorofillo/app.py &
poetry run python src/clorofillo/io_app.py &
wait

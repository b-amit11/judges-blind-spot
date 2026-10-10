.PHONY: data train test run lint format
data:
	python -m blindspot.data
train:
	python -m blindspot.train
test:
	python -m pytest -q
run:
	streamlit run app.py
lint:
	black --check blindspot app.py tests
	isort --check blindspot app.py tests
	ruff check blindspot app.py tests
	mypy blindspot app.py
format:
	black blindspot app.py tests
	isort blindspot app.py tests
	ruff check --fix blindspot app.py tests

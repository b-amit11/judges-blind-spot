.PHONY: data train test run
data:
	python -m blindspot.data
train:
	python -m blindspot.train
test:
	python -m pytest -q
run:
	streamlit run app.py

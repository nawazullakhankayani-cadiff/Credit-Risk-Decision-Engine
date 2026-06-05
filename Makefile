.PHONY: install install-core data clean-csv train test lint api app report docker
PYTHONPATH := src
export PYTHONPATH

install:        ; pip install -r requirements.txt
install-core:   ; pip install -r requirements-core.txt
data:           ; python -m credit_risk.data.generate 30000
clean-csv:      ; python -m credit_risk.data.clean $(IN) $(OUT)
train:          ; python -m credit_risk.train
test:           ; python -m pytest -q
lint:           ; ruff check src tests || true
api:            ; uvicorn credit_risk.api.main:app --host 0.0.0.0 --port 8000 --app-dir src
app:            ; streamlit run app/streamlit_app.py
web:            ; uvicorn credit_risk.web.app:app --host 0.0.0.0 --port 8080 --app-dir src
report:         ; python -m credit_risk.reporting.report $(CSV) -o $(OUT)
docker:         ; docker compose up --build

CSV ?= data/loans.csv
OUT ?= report.html

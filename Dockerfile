FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000 8501
# data is generated only when the database file does not exist yet (deterministic, no real personal data); a volume keeps it between restarts
CMD ["sh", "-c", "python scripts/generate_data.py --if-missing && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src/ src/
COPY config/ config/
COPY data/raw/ data/raw/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["python", "-m", "analytics_pipeline.cli"]
CMD ["run"]

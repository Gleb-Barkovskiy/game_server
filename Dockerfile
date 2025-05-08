FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        && \
    rm -rf /var/lib/apt/lists/*

# Install pip dependencies
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install --no-cache-dir "poetry==1.8.5"

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only main --no-interaction --no-ansi

# Copy the rest of the app
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
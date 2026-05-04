FROM python:3.11.5-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY /requirements.txt /app
RUN pip3 install --no-cache-dir -r requirements.txt

FROM python:3.11.5-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем проект
COPY src/predict.py /app/src/predict.py
COPY models/predict_future_sales_xgb.joblib /app/models/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# По умолчанию запускаем API
ENV PORT 8080

CMD ["python", "src/predict.py"]
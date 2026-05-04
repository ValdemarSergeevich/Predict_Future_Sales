import joblib
import pandas as pd
import uvicorn

import os

from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Sales Prediction API")

# ---------------------------------------------------------
# 1. Пути
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "predict_future_sales_xgb.joblib"
DATA_PATH = BASE_DIR / "data" / "df_final1.csv"

# ---------------------------------------------------------
# 2. Загрузка модели
# ---------------------------------------------------------
try:
    model = joblib.load(MODEL_PATH)
    print(f"Model loaded successfully from {MODEL_PATH}")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# ---------------------------------------------------------
# 3. Загрузка данных
# ---------------------------------------------------------
try:
    df = pd.read_csv(DATA_PATH).drop_duplicates(
        subset=["shop_id", "item_id", "date_block_num"], keep="first"
    )

    # Удаляем целевую переменную, если она есть
    df = df.drop(columns=["item_cnt_month"], errors="ignore")

    # Категориальные признаки
    cat_cols = ["city"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype("category").cat.codes

    print(f"Data loaded successfully. Shape: {df.shape}")

except Exception as e:
    print(f"Error loading data: {e}")
    df = pd.DataFrame()

# ---------------------------------------------------------
# 4. Pydantic модели
# ---------------------------------------------------------
class Form(BaseModel):
    date_block_num: int
    ID: int

class Prediction(BaseModel):
    ID: int
    shop_id: int
    item_id: int
    item_cnt_month: float

# ---------------------------------------------------------
# 5. Healthcheck
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "Welcome to Sales Prediction API. Use /status or /predict"}

@app.get("/status")
def status():
    # Добавим в статус проверку загрузки, чтобы видеть проблему в логах
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "data_loaded": not df.empty
    }

# ---------------------------------------------------------
# 6. Основной эндпоинт
# ---------------------------------------------------------
@app.post("/predict", response_model=Prediction)
def predict(form: Form):

    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    if df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")

    # Ищем строку в датасете
    row = df[
        (df["ID"] == form.ID)
        & (df["date_block_num"] == form.date_block_num)
    ]

    if row.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Не найдены признаки для ID={form.ID}, date_block_num={form.date_block_num}",
        )

    # Копируем строку
    X = row.copy()

    # Приводим порядок колонок к порядку модели
    try:
        X = X[model.feature_names_in_]
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Feature mismatch: модель ожидает другой набор признаков"
        )

    # Предсказание
    y = model.predict(X)
    y_pred = min(float(y[0]), 20.0)

    return {
        "ID": int(form.ID),
        "shop_id": int(row["shop_id"].iloc[0]),
        "item_id": int(row["item_id"].iloc[0]),
        "item_cnt_month": y_pred,
    }

# ---------------------------------------------------------
# 7. Запуск (без reload — важно для Docker)
# ---------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("src.predict:app", host="0.0.0.0", port=port)

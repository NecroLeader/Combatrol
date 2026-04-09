FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Inicializa la DB si no existe (respeta el volumen montado en prod)
CMD ["sh", "-c", "python scripts/init_db.py --seed-matrix outcome_matrix_seed.csv --seed-matrix outcome_matrix_seed_v2.csv && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

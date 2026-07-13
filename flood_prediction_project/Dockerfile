# Rising Waters - Flood Prediction Flask App
# Built for deployment to IBM Cloud Code Engine (container-based, serverless)

FROM python:3.11-slim

WORKDIR /app

# System deps needed by xgboost / scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train the model at build time so model.pkl/scaler.pkl always ship with the image.
# (Safe to skip if model/model.pkl is already committed - see note in README.)
RUN python train_model.py

# Code Engine injects $PORT; default to 8080 for local docker run
ENV PORT=8080
EXPOSE 8080

CMD gunicorn -w 2 -b 0.0.0.0:${PORT} app:app

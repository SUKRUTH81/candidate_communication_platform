FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY provider/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY provider/app.py .
EXPOSE 9000
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:9000", "--workers", "1", "--threads", "16"]

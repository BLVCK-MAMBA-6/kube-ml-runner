FROM python:3.11-slim

WORKDIR /app
COPY infer.py .

# No heavy deps for this toy example; add requirements.txt if needed
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "infer.py"]
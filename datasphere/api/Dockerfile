# UBI9 Python 3.11 — Red Hat Universal Base Image
# registry.access.redhat.com requires no auth and is public.
# Pin the tag for consistent vulnerability scan results across lab runs.
FROM registry.access.redhat.com/ubi9/python-311:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# UBI images already run as non-root (uid 1001) — no useradd needed

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM python:3.11-slim

WORKDIR /app

# gcc/build-essential needed for a couple of crewai's transitive deps that
# ship without prebuilt wheels for slim images; removed after install to
# keep the final image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

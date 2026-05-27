FROM python:3.11-slim

WORKDIR /josue_s_app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install poetry 

RUN poetry install --without dev

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt


# CMD ["python", "main.py"]

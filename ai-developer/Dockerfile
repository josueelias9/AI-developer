FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /josue_s_app

COPY . .

RUN pip install poetry 

# RUN poetry install --without dev

# CMD ["poetry","run","python", "main.py"]

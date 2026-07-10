FROM python:3.11-slim

RUN apt update
RUN apt install -y curl
RUN apt install -y tree

WORKDIR /josue_s_app

COPY . .

RUN pip install poetry 

# RUN poetry install --without dev

# CMD ["poetry","run","python", "main.py"]

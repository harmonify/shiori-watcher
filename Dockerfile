FROM python:3.11-slim

WORKDIR /app

COPY main.py /app/main.py
COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

CMD ["python", "main.py"]

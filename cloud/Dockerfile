FROM python:3.12-slim

WORKDIR /app

RUN pip install --nocache-dir \ 
    fastapi uvicorn[standard] psycopg[binary] boto3 pydantic 

COPY . /app/cloud/
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "cloud.main:app", "--host", "0.0.0.0", "--port", "8000"]

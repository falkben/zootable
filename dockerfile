FROM python:3.8

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN \
    pip install pip-tools &&\
    pip-sync

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "mysite.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

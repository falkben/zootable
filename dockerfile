FROM python:3.8

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY . /app
RUN pip install .

EXPOSE 8000
CMD ["uvicorn", "mysite.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

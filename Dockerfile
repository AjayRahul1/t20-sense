FROM python:3.12
WORKDIR /code
COPY requirements.txt /code
RUN pip install -r /code/requirements.txt
COPY . /code
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
# Stage 1: Build stage
FROM python:3.12-slim AS build
WORKDIR /code
COPY requirements.txt /code
RUN pip install -r requirements.txt
COPY . /code

# Stage 2: Final stage
FROM build
WORKDIR /app
COPY --from=build /code /app
EXPOSE 8000
CMD ["python", "main.py"]
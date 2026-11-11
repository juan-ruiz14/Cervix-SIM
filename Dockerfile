FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements-mongo.txt backend/
RUN pip install --no-cache-dir -r backend/requirements-mongo.txt
COPY backend backend
COPY frontend frontend
WORKDIR /app/backend
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["python", "-m", "cervix_sim"]

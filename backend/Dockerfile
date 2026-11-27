FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home arth
COPY backend /app/backend
USER arth
EXPOSE 8000
CMD ["python","-m","uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]

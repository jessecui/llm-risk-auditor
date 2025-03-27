FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Note: we expose both 8000 (FastAPI) and 8501 (Streamlit)
EXPOSE 8000 8501

# Run the combined app
CMD ["python", "app.py"]
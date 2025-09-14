# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
# Install project dependencies and ensure gunicorn is present in the final image
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Verify gunicorn is installed during build
RUN which gunicorn

# Copy project
COPY . .

# Collect static files during build
RUN python manage.py collectstatic --noinput --clear

# Run the application
CMD ["gunicorn", "financial_consolidator.wsgi:application", "--workers", "2", "--bind", "0.0.0.0:8080"]

# Use an official lightweight Python runtime as a parent image
FROM python:3.10-slim

# Set system environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for compiling cryptography and mysql drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application code into the container
COPY . .

# Expose port 5000 for Gunicorn
EXPOSE 5000

# Start Gunicorn running the Flask app
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:5000", "run:app"]

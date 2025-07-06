# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
# Prevents Python from writing pyc files to disc (equivalent to python -B option)
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

# Install OS-level dependencies for Chromium and ChromeDriver
# Based on common requirements for headless Chrome on Debian-based systems
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    # ---- For Chrome/Chromium ----
    chromium-browser \
    chromium-chromedriver \
    # ---- General dependencies often needed by headless browsers ----
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxi6 \
    libxrandr2 \
    libxfixes3 \
    libxcursor1 \
    libxdamage1 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    # ---- Clean up apt cache to reduce image size ----
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . /app/

# Expose the port Gunicorn will run on (matches Gunicorn command below)
EXPOSE 8000

# Define the command to run the application using Gunicorn
# Using a shell form to allow environment variable expansion if needed later
# Log to stdout/stderr for App Service to pick up
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

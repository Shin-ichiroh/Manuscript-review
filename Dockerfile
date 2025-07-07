# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
# Prevents Python from writing pyc files to disc (equivalent to python -B option)
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

# Install OS-level dependencies for Chromium and ChromeDriver
# Based on common requirements for headless Chrome on Debian-based systems
# Install OS-level dependencies for Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    # ---- Add Google Chrome's official PPA and install Chrome ----
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y \
    google-chrome-stable \
    # ---- General dependencies often needed by headless browsers ----
    # Some of these might be pulled in by google-chrome-stable, but explicit is safer
    libglib2.0-0 \
    libnss3 \
    # libgconf-2-4 \ # Often not needed with modern Chrome, can try removing if problematic
    libfontconfig1 \
    libxi6 \
    libxrandr2 \
    libxfixes3 \
    libxcursor1 \
    libxdamage1 \
    libpangocairo-1.0-0 \
    # libpango-1.0-0 \ # Usually part of libpangocairo
    libatk1.0-0 \
    # libatk-bridge2.0-0 \ # Often for accessibility, might not be strictly needed
    # libgtk-3-0 \ # For GUI, might not be needed for headless
    libgbm-dev \
 # Still can be useful for headless rendering
    # ---- Install ChromeDriver separately ----
    # We will download a specific version of ChromeDriver later, or rely on webdriver_manager
    # For now, let's assume webdriver_manager will handle ChromeDriver if google-chrome-stable is present.
    # If webdriver_manager fails, we might need to install chromedriver manually here matching the google-chrome-stable version.
    # Example for manual install (needs correct version):
    # && CHROME_VERSION=$(google-chrome-stable --version | cut -f 3 -d ' ' | cut -f 1 -d '.') \
    # && CD_VERSION=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}) \
    # && wget -qO /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CD_VERSION}/chromedriver_linux64.zip \
    # && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    # && rm /tmp/chromedriver.zip \
    # ---- Clean up apt cache ----
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
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "120", "app:app"]
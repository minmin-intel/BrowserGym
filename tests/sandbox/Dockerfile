# Use the official Playwright Docker image that already has browsers installed
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

# Set up working directory
WORKDIR /app

# Install Python and pip if not already in the base image
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose port for API
EXPOSE 8000

# Environment variable to run headless by default
ENV PLAYWRIGHT_HEADLESS=true

# Command to run the server
CMD ["python3", "server.py"]
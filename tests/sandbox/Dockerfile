FROM python:3.10-slim

# Install dependencies for Playwright and Chrome
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    git \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    fonts-noto-color-emoji \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright && playwright install chromium

# Copy the application code
COPY . .

# Expose port for API
EXPOSE 8000

# Environment variable to run headless by default
ENV PLAYWRIGHT_HEADLESS=true

# Command to run the server
CMD ["python", "server.py"]
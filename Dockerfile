# Multi-stage optimized Dockerfile for WM-MEGA
FROM ubuntu:22.04 as base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DISPLAY=:99

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y \
    # Python and pip
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    # System tools
    curl \
    wget \
    git \
    lsof \
    sudo \
    # X11 and display dependencies
    xvfb \
    x11-utils \
    x11-xserver-utils \
    # Chrome/Chromium dependencies
    libxss1 \
    libgconf-2-4 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libnss3 \
    libxss1 \
    libappindicator1 \
    libindicator7 \
    libayatana-appindicator3-1 \
    libayatana-ido3-0.4-0 \
    libayatana-indicator3-7 \
    libdbusmenu-gtk3-4 \
    # Package extraction
    dpkg \
    # Network tools
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 appuser && \
    echo "appuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER appuser

# Copy requirements first for better caching
COPY --chown=appuser:appuser requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . /app/

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/multilogin/extracted

# Set permissions
RUN chmod +x /app/entrypoint.sh 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Expose port
EXPOSE 5000

# Use custom entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

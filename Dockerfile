# Multi-stage build for optimal size and security
FROM ubuntu:22.04 AS base

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Python and build tools
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    # Browser dependencies
    wget \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxss1 \
    xdg-utils \
    # Display and VNC
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    supervisor \
    # Utilities
    git \
    vim \
    htop \
    net-tools \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -s /bin/bash browserbot && \
    mkdir -p /home/browserbot/app && \
    chown -R browserbot:browserbot /home/browserbot && \
    echo "browserbot ALL=(ALL) NOPASSWD: /usr/bin/supervisord, /usr/bin/pkill" >> /etc/sudoers

# Install Chrome (latest stable)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Configure VNC and display
RUN mkdir -p /home/browserbot/.vnc && \
    x11vnc -storepasswd browserbot /home/browserbot/.vnc/passwd && \
    chown -R browserbot:browserbot /home/browserbot/.vnc

# Switch to non-root user
USER browserbot
WORKDIR /home/browserbot/app

# Copy requirements first for better caching
COPY --chown=browserbot:browserbot pyproject.toml .python-version ./

# Upgrade pip and install dependencies
RUN python3.11 -m pip install --upgrade pip setuptools wheel && \
    python3.11 -m pip install -e . && \
    python3.11 -m playwright install chromium && \
    python3.11 -m playwright install-deps

# Copy application code
COPY --chown=browserbot:browserbot . .

# Create necessary directories
RUN mkdir -p logs data config

# Copy scripts and configuration
USER root
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/interactive-entrypoint.sh /usr/local/bin/interactive-entrypoint.sh
RUN chmod 644 /etc/supervisor/conf.d/supervisord.conf && \
    chmod +x /usr/local/bin/interactive-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 5900 8000 8080

# Switch back to non-root user
USER browserbot

# Entry point
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
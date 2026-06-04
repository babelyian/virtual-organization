FROM odoo:19

USER root

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    python3-dev \
    libffi-dev \
    libssl-dev \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (required for latest npm)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# Install rtlcss (compatible version for Node.js 20)
RUN npm install -g npm@10.8.1 && \
    npm install -g rtlcss


COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir \
    --break-system-packages \
    --ignore-installed \
    -r /tmp/requirements.txt

USER odoo
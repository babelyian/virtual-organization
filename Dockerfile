FROM odoo:19

USER root

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir \
    --break-system-packages \
    --ignore-installed \
    -r /tmp/requirements.txt

USER odoo

FROM odoo:19

USER root

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir \
    --break-system-packages \
    --ignore-installed \
    -r /tmp/requirements.txt

USER odoo

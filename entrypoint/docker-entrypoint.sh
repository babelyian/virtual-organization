#!/bin/bash
set -e

ODOO_CONF="/etc/odoo/odoo.conf"
ODOO_BIN=$(which odoo)

echo "Waiting for PostgreSQL..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"; do
  sleep 2
done

echo "Creating database if not exists..."
$ODOO_BIN -c "$ODOO_CONF" --stop-after-init -d "$DB_NAME" --without-demo=all || true

echo "🔄 Running module update..."
$ODOO_BIN -c "$ODOO_CONF" -d "$DB_NAME" -u agno_user --stop-after-init || true


echo "Creating or updating admin user..."
$ODOO_BIN shell -c "$ODOO_CONF" -d "$DB_NAME" <<EOF
env = env(context=dict(env.context, active_test=False))
User = env['res.users']

# Try to find existing user
user = User.search([('login', '=', '$ODOO_ADMIN_EMAIL')], limit=1)

if not user:
    user = User.create({
        'name': '$ODOO_ADMIN_NAME',
        'login': '$ODOO_ADMIN_EMAIL',
        'email': '$ODOO_ADMIN_EMAIL',
        'password': '$ODOO_ADMIN_PASSWORD',
    })
else:
    user.password = '$ODOO_ADMIN_PASSWORD'
    user.write({'password': '$ODOO_ADMIN_PASSWORD'})

# Assign administration group safely
admin_group = env.ref('base.group_system')
if admin_group not in user.group_ids:
    user.write({'group_ids': [(4, admin_group.id)]})

env.cr.commit()
EOF

echo "Starting Odoo..."
exec $ODOO_BIN -c "$ODOO_CONF"

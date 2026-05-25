docker compose down
docker compose rm -f          # remove stopped containers
docker system prune -f        # optional: clean dangling resources
docker compose up -d

 docker cp tests/test_employee_agent.py odoo_app:tmp/
docker exec -it odoo_app ls ./tmp
docker exec -it odoo_app python3 ./tmp/test_employee_agent.py

docker exec -it odoo_app python3 ./tmp/test_employee_agent.py 13

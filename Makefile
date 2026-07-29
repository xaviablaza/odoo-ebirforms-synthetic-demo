.PHONY: check generate-orders refresh-catalog render-1601c start stop logs reset

check:
	python3 -m unittest discover -s tests -v
	python3 -m compileall -q addons scripts tests
	python3 scripts/validate_dataset.py

generate-orders:
	python3 scripts/generate_orders.py

refresh-catalog:
	python3 scripts/refresh_catalog.py

render-1601c:
	./scripts/render_1601c.sh

start:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f odoo

reset:
	docker compose down -v

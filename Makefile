.PHONY: help install dev-install migrate runserver test lint format check

help:
	@echo "Доступные команды:"
	@echo "  make install        - Установить зависимости"
	@echo "  make dev-install    - Установить зависимости для разработки"
	@echo "  make migrate        - Применить миграции"
	@echo "  make runserver      - Запустить сервер разработки"
	@echo "  make lint           - Проверить код линтерами"
	@echo "  make format         - Отформатировать код"
	@echo "  make check          - Проверить форматирование без изменений"
	@echo "  make test           - Запустить тесты"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

runserver:
	python manage.py runserver

lint:
	flake8 .
	mypy .

format:
	black .
	isort .

check:
	black --check .
	isort --check-only .

test:
	pytest

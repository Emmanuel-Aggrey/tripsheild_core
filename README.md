# SET UP

1. Create a virtual environment (python3.12+)
2. `$ pip install -r requirements.txt`
3. `$ pre-commit install`
4. create .env file
5. copy .env.example to .env and update the values
6. `$ alembic upgrade head`
7. `$ fastapi dev` or `$ fastapi dev --port port_number`

# Init Alembic

```bash
$ alembic init alembic
```

# Creating migration

```bash
$ alembic revision --autogenerate -m "first migrations"
$ alembic upgrade head

# To downgrade
$ alembic downgrade -1

```

# RUN TEST

```bash
pytest -v app or pytest -v app/module

```

# RUN KAFKA

```bash
brew services start kafka
brew services start zookeeper
```

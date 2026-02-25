import os

from dotenv import load_dotenv


def create_database(database_name, user_name, password):
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # <-- ADD THIS LINE

    con = psycopg2.connect(
        dbname="postgres", user=user_name, host="", password=password
    )

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # <-- ADD THIS LINE

    cur = con.cursor()

    # Use the psycopg2.sql module instead of string concatenation
    # in order to avoid sql injection attacks.

    # drop database if exists
    cur.execute(
        sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
    )
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    # Close the connection
    cur.close()
    con.close()


def pytest_sessionstart(session):
    # set change DATABASE_NAME env variable to test_DATABASE_NAME
    load_dotenv()
    is_ci = os.getenv("IS_CI") == "True"
    os.environ["IS_TESTING"] = "True"

    if is_ci:
        return
    test_database_name = "test_" + os.getenv("DATABASE_NAME")
    os.environ["DATABASE_NAME"] = test_database_name

    # create test database
    print("creating test database")
    create_database(
        test_database_name, os.getenv("DATABASE_USER"), os.getenv("DATABASE_PASSWORD")
    )

    from app.test.base import engine
    from app.database import Base

    Base.metadata.drop_all(bind=engine)
    os.system("alembic upgrade head")


def pytest_sessionfinish(session, exitstatus):
    print("done testing")

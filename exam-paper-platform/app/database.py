import os

from neo4j import Driver, GraphDatabase


_driver: Driver | None = None


def get_database() -> Driver:
	global _driver
	if _driver is None:
		uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
		user = os.getenv("NEO4J_USER", "neo4j")
		password = os.getenv("NEO4J_PASSWORD", "YORICHI007#")
		_driver = GraphDatabase.driver(uri, auth=(user, password))
	return _driver


def close_database() -> None:
	global _driver
	if _driver is not None:
		_driver.close()
		_driver = None
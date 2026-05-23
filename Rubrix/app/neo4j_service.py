from neo4j import Driver


class Neo4jService:
	def __init__(self, driver: Driver):
		self.driver = driver

	def list_subjects(self) -> list[str]:
		query = """
		MATCH (s:Subject)
		RETURN s.name AS subject
		ORDER BY s.name
		"""
		with self.driver.session() as session:
			rows = session.run(query)
			return [record["subject"] for record in rows if record.get("subject")]

	def list_topics(self, subject: str) -> list[str]:
		query = """
		MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)
		RETURN t.name AS topic
		ORDER BY t.name
		"""
		with self.driver.session() as session:
			rows = session.run(query, subject=subject)
			return [record["topic"] for record in rows if record.get("topic")]

	def get_questions(self, subject: str, topics: list[str], cutoff_year: int) -> list[dict[str, object]]:
		query = """
		MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)-[:HAS_QUESTION]->(q:Question)
		WHERE t.name IN $topics
		  AND (q.year IS NULL OR q.year <= $cutoff_year)
		RETURN
		  coalesce(q.question, q.text, q.content) AS question,
		  t.name AS topic,
		  q.year AS year
		"""
		with self.driver.session() as session:
			rows = session.run(query, subject=subject, topics=topics, cutoff_year=cutoff_year)
			return [dict(record) for record in rows]
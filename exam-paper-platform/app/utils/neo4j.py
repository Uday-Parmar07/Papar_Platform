"""Shared Neo4j helpers."""

import os
from urllib.parse import unquote, urlparse


def resolve_neo4j_url() -> str:
    """Build the Neo4j connection URL from environment variables."""
    authority_url = (
        os.getenv("NEO4J_BOLT_URL")
        or os.getenv("NEOMODEL_NEO4J_BOLT_URL")
    )

    if authority_url:
        authority_url = unquote(authority_url)
        parsed = urlparse(authority_url)

        scheme_map = {
            "neo4j": "bolt",
            "neo4j+s": "bolt+s",
            "neo4j+ssc": "bolt+ssc",
        }
        scheme = scheme_map.get(parsed.scheme, parsed.scheme)

        username = parsed.username or os.getenv("NEO4J_USER")
        password = parsed.password or os.getenv("NEO4J_PASSWORD")
        host = parsed.hostname or os.getenv("NEO4J_HOST", "localhost")
        port = parsed.port or os.getenv("NEO4J_PORT", "7687")

        if username and password and host:
            return f"{scheme}://{username}:{password}@{host}:{port}"

        if parsed.username and parsed.password and parsed.scheme.startswith("bolt"):
            return authority_url

        raise ValueError(
            "Neo4j connection details incomplete. Ensure NEO4J_USER and "
            "NEO4J_PASSWORD are set when using Aura URIs."
        )

    username = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    host = os.getenv("NEO4J_HOST", "localhost")
    port = os.getenv("NEO4J_PORT", "7687")
    return f"bolt://{username}:{password}@{host}:{port}"

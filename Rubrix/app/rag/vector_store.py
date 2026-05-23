import os
from typing import Dict, Iterable, List, Optional, Tuple

from pinecone import Pinecone, ServerlessSpec
from pinecone.core.client.exceptions import PineconeApiException


DEFAULT_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "exam-books")
DEFAULT_DIMENSION = int(os.getenv("PINECONE_INDEX_DIMENSION", "384"))


def _list_available_regions(client: Pinecone) -> List[Dict[str, str]]:
	try:
		project = client.describe_serverless_project()
		regions = project.get("available_regions", []) if isinstance(project, dict) else getattr(project, "available_regions", [])
		normalized: List[Dict[str, str]] = []
		for entry in regions:
			cloud = entry.get("cloud") if isinstance(entry, dict) else getattr(entry, "cloud", None)
			region = entry.get("region") if isinstance(entry, dict) else getattr(entry, "region", None)
			if cloud and region:
				normalized.append({"cloud": cloud, "region": region})
		return normalized
	except Exception:
		return []


def _match_available(
	available: List[Dict[str, str]],
	cloud: Optional[str],
	region: Optional[str],
) -> Optional[Dict[str, str]]:
	if not available:
		return None
	for entry in available:
		if cloud and entry["cloud"] != cloud:
			continue
		if region and entry["region"] != region:
			continue
		return entry
	return None


def _parse_candidate(value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
	if not value:
		return None, None
	candidate = value.strip().lower()
	cloud = None
	region = None
	if candidate.count("-") >= 2:
		segments = candidate.split("-")
		cloud = segments[-1]
		region = "-".join(segments[:-1])
	else:
		region = candidate
	return cloud, region


def _resolve_serverless_spec(client: Pinecone) -> Dict[str, str]:
	available = _list_available_regions(client)

	cloud_override = os.getenv("PINECONE_CLOUD")
	region_override = os.getenv("PINECONE_REGION")
	if cloud_override and region_override:
		match = _match_available(available, cloud_override, region_override)
		if match:
			return match
		print(
			f"[pinecone] Requested cloud={cloud_override} region={region_override} not available; falling back to defaults."
		)

	env_value = os.getenv("PINECONE_ENVIRONMENT")
	parsed_cloud, parsed_region = _parse_candidate(env_value)
	if parsed_cloud or parsed_region:
		match = _match_available(available, parsed_cloud, parsed_region)
		if match:
			return match
		if parsed_region and available:
			for entry in available:
				if entry["region"] == parsed_region:
					return entry
		print(
			f"[pinecone] Environment '{env_value}' unsupported; falling back to defaults."
		)

	if available:
		return available[0]

	default_spec = {"cloud": "aws", "region": "us-east-1"}
	print("[pinecone] Using fallback spec aws/us-east-1; unable to determine available regions.")
	return default_spec


class PineconeVectorStore:
	def __init__(self, index_name: str | None = None, dimension: int | None = None, metric: str = "cosine") -> None:
		api_key = os.getenv("PINECONE_API_KEY")
		if not api_key:
			raise RuntimeError("PINECONE_API_KEY is required to connect to Pinecone")
		self.client = Pinecone(api_key=api_key)
		self.index_name = index_name or DEFAULT_INDEX_NAME
		self.dimension = dimension or DEFAULT_DIMENSION
		self.metric = metric
		self.spec = _resolve_serverless_spec(self.client)
		self._ensure_index()
		self.index = self.client.Index(self.index_name)

	def _ensure_index(self) -> None:
		response = self.client.list_indexes()
		existing: set[str] = set()
		if isinstance(response, dict):
			entries = response.get("indexes", [])
			for entry in entries:
				if isinstance(entry, dict) and entry.get("name"):
					existing.add(entry["name"])
		elif isinstance(response, list):
			existing.update(str(item) for item in response)
		else:
			entries = getattr(response, "indexes", [])
			for entry in entries:
				name = getattr(entry, "name", None)
				if name:
					existing.add(name)
		if self.index_name in existing:
			description = self.client.describe_index(self.index_name)
			current_dim = None
			if isinstance(description, dict):
				current_dim = description.get("dimension")
			else:
				current_dim = getattr(description, "dimension", None)
			if current_dim and current_dim != self.dimension:
				print(
					f"[pinecone] Existing index '{self.index_name}' has dimension {current_dim}, "
					f"expected {self.dimension}. Recreating index."
				)
				self.client.delete_index(self.index_name)
			else:
				return
		try:
			self.client.create_index(
				name=self.index_name,
				dimension=self.dimension,
				metric=self.metric,
				spec=ServerlessSpec(**self.spec),
			)
		except PineconeApiException as exc:
			status = getattr(exc, "status", None)
			message = getattr(exc, "body", "")
			if status == 409 or "ALREADY_EXISTS" in str(message).upper():
				return
			raise
		return

	def upsert(self, namespace: str, vectors: Iterable[Dict]) -> None:
		items = [vector for vector in vectors if vector.get("values")]
		if not items:
			return
		batch_size = 100
		for start in range(0, len(items), batch_size):
			chunk = items[start : start + batch_size]
			self.index.upsert(vectors=chunk, namespace=namespace)

	def query(
		self,
		vector: List[float],
		top_k: int = 5,
		namespace: str = "Electrical Engineering",
		include_metadata: bool = True,
	) -> Dict:
		"""
		Query the index for similar vectors.
		
		Args:
			vector: Query vector (embedding)
			top_k: Number of top results to return
			namespace: Pinecone namespace to search in
			include_metadata: Whether to include metadata in results
			
		Returns:
			Dictionary with 'matches' containing similar vectors and metadata
		"""
		try:
			results = self.index.query(
				vector=vector,
				top_k=top_k,
				namespace=namespace,
				include_metadata=include_metadata,
			)
			return results if results else {"matches": []}
		except Exception as e:
			print(f"Error querying index: {e}")
			return {"matches": []}

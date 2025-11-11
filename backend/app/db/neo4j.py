"""Neo4j graph database connection and operations."""
from neo4j import GraphDatabase, AsyncGraphDatabase
import os
from typing import Optional, Dict, List

class Neo4jConnection:
    """Neo4j database connection manager."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "testpass")
        self.driver = None

    def connect(self):
        """Establish connection to Neo4j."""
        if not self.driver:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self.driver

    def close(self):
        """Close connection to Neo4j."""
        if self.driver:
            self.driver.close()
            self.driver = None

# Global connection instance
_neo4j_conn = Neo4jConnection()

def get_driver():
    """Get Neo4j driver instance."""
    return _neo4j_conn.connect()

async def link_domain(domain: str, metadata: Optional[Dict] = None) -> None:
    """
    Create or update a domain node in the graph.

    Args:
        domain: Domain name
        metadata: Optional metadata to attach to the node
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Domain {name: $domain})
            ON CREATE SET d.created = timestamp(), d.metadata = $metadata
            ON MATCH SET d.last_seen = timestamp(), d.metadata = $metadata
            RETURN d
            """,
            domain=domain,
            metadata=metadata or {}
        )

async def link_domain_to_ip(domain: str, ip: str, resolution_type: str = "A") -> None:
    """
    Create relationship between domain and IP address.

    Args:
        domain: Domain name
        ip: IP address
        resolution_type: DNS record type (A, AAAA, etc.)
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Domain {name: $domain})
            MERGE (i:IP {address: $ip})
            MERGE (d)-[r:RESOLVES_TO {type: $resolution_type}]->(i)
            ON CREATE SET r.created = timestamp(), r.count = 1
            ON MATCH SET r.last_seen = timestamp(), r.count = r.count + 1
            """,
            domain=domain,
            ip=ip,
            resolution_type=resolution_type
        )

async def link_domain_to_certificate(domain: str, cert_fingerprint: str,
                                     cert_data: Optional[Dict] = None) -> None:
    """
    Create relationship between domain and SSL certificate.

    Args:
        domain: Domain name
        cert_fingerprint: Certificate fingerprint/hash
        cert_data: Optional certificate metadata
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Domain {name: $domain})
            MERGE (c:Certificate {fingerprint: $fingerprint})
            ON CREATE SET c.data = $cert_data, c.created = timestamp()
            MERGE (d)-[r:HAS_CERTIFICATE]->(c)
            ON CREATE SET r.created = timestamp()
            ON MATCH SET r.last_seen = timestamp()
            """,
            domain=domain,
            fingerprint=cert_fingerprint,
            cert_data=cert_data or {}
        )

async def link_domain_to_organization(domain: str, org_name: str) -> None:
    """
    Create relationship between domain and organization.

    Args:
        domain: Domain name
        org_name: Organization name
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Domain {name: $domain})
            MERGE (o:Organization {name: $org_name})
            MERGE (d)-[r:OWNED_BY]->(o)
            ON CREATE SET r.created = timestamp()
            ON MATCH SET r.last_seen = timestamp()
            """,
            domain=domain,
            org_name=org_name
        )

async def add_threat_intel_tag(domain: str, tag: str, source: str,
                               confidence: float = 0.5) -> None:
    """
    Add a threat intelligence tag to a domain.

    Args:
        domain: Domain name
        tag: Threat intelligence tag (e.g., 'malicious', 'suspicious', 'phishing')
        source: Source of the intelligence
        confidence: Confidence score (0.0 to 1.0)
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (d:Domain {name: $domain})
            MERGE (t:ThreatTag {name: $tag})
            MERGE (d)-[r:TAGGED_AS]->(t)
            ON CREATE SET r.source = $source, r.confidence = $confidence,
                         r.created = timestamp()
            ON MATCH SET r.last_seen = timestamp(), r.confidence = $confidence
            """,
            domain=domain,
            tag=tag,
            source=source,
            confidence=confidence
        )

async def get_domain_graph(domain: str, depth: int = 2) -> Dict:
    """
    Retrieve graph neighborhood for a domain.

    Args:
        domain: Domain name
        depth: Traversal depth

    Returns:
        Dictionary containing nodes and relationships
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH path = (d:Domain {name: $domain})-[*0..$depth]-(n)
            RETURN path
            LIMIT 100
            """,
            domain=domain,
            depth=depth
        )

        nodes = []
        relationships = []

        for record in result:
            path = record["path"]
            for node in path.nodes:
                nodes.append({
                    "id": node.id,
                    "labels": list(node.labels),
                    "properties": dict(node)
                })
            for rel in path.relationships:
                relationships.append({
                    "id": rel.id,
                    "type": rel.type,
                    "start": rel.start_node.id,
                    "end": rel.end_node.id,
                    "properties": dict(rel)
                })

        return {
            "nodes": nodes,
            "relationships": relationships
        }

async def find_related_domains(domain: str, min_connections: int = 2) -> List[str]:
    """
    Find domains related through shared infrastructure.

    Args:
        domain: Domain name
        min_connections: Minimum number of shared connections

    Returns:
        List of related domain names
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (d1:Domain {name: $domain})-[]->(shared)<-[]-(d2:Domain)
            WHERE d1 <> d2
            WITH d2.name as related_domain, count(shared) as connections
            WHERE connections >= $min_connections
            RETURN related_domain, connections
            ORDER BY connections DESC
            LIMIT 50
            """,
            domain=domain,
            min_connections=min_connections
        )

        return [record["related_domain"] for record in result]

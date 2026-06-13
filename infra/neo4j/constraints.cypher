// ResearchOS Neo4j Constraints & Indexes
// ============================================================

// Node constraints
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT session_id IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE;

// Indexes
CREATE INDEX claim_text IF NOT EXISTS FOR (c:Claim) ON (c.text);
CREATE INDEX source_url IF NOT EXISTS FOR (s:Source) ON (s.url);
CREATE INDEX concept_domain IF NOT EXISTS FOR (c:Concept) ON (c.domain);

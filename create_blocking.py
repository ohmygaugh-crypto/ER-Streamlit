import os
import logging
import argparse
import uuid
import random
import requests
from dotenv import load_dotenv
from neo4j_handler import Neo4jHandler

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from the .env file.
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
    raise ValueError("Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in your .env file")

# You can set a default database name if needed; otherwise, sessions without 'database' parameter are used.
# For example, if using Neo4j 5 you might need to specify a database; here we'll leave it out.
# db_name = "neo4j"  

def create_similarity(driver, property, similarity_threshold: float = 0.90) -> None:
    """
    Creates SIMILAR relationships based on the similarity of a given property (e.g. phone_number or email_address).
    Uses APOC's Levenshtein similarity and ensures that pairs are processed only once.
    Reports the number of new SIMILAR relationships created.
    """
    # Get the current count of SIMILAR relationships for this property.
    pre_count_query = f"""
    MATCH ()-[r:SIMILAR {{ comparedProperty: '{property}' }}]->()
    RETURN count(r) AS count
    """
    with driver.session() as session:
        pre_count = session.run(pre_count_query).single()["count"]

    # Run the similarity creation query using APOC periodic iterate.
    query = f"""
    CALL apoc.periodic.iterate(
      "MATCH (c:Identity) WHERE c.{property} IS NOT NULL RETURN c",
      "MATCH (c2:Identity) 
         WHERE c2.{property} IS NOT NULL 
         AND id(c) < id(c2)
         AND NOT EXISTS((c)-[:SIMILAR {{ comparedProperty: '{property}' }}]->(c2))
         AND NOT EXISTS((c)<-[:contains_identity]-()-[:contains_identity]->(c2))
         WITH c, c2,
              apoc.text.levenshteinSimilarity(toString(c.{property}), toString(c2.{property})) AS sim
         WHERE sim >= {similarity_threshold}
         CREATE (c)-[:SIMILAR {{
           comparedProperty: '{property}',
           similarity: sim
         }}]->(c2)",
      {{batchSize:100, parallel:true}}
    )
    """
    with driver.session() as session:
        session.run(query)

    # Get the count after processing.
    post_count_query = f"""
    MATCH ()-[r:SIMILAR {{ comparedProperty: '{property}' }}]->()
    RETURN count(r) AS count
    """
    with driver.session() as session:
        post_count = session.run(post_count_query).single()["count"]

    new_relationships = post_count - pre_count
    print(f"New SIMILAR relationships created for {property}: {new_relationships}")

def run_wcc(driver) -> None:
    """
    Runs the Weakly Connected Components (WCC) algorithm using Neo4j Graph Data Science (GDS)
    to cluster similar Identity nodes.
    """
    # Step 0: Drop the existing graph if it exists.
    drop_query = """
    CALL gds.graph.exists('limitedIdentityProfileGraph') YIELD exists
    WITH exists
    WHERE exists
    CALL gds.graph.drop('limitedIdentityProfileGraph') YIELD graphName
    RETURN graphName
    """
    with driver.session() as session:
        session.run(drop_query)

    # Step 1: Project a subgraph from the nodes and SIMILAR/contains_Identity relationships.
    # We limit to a set of Identity node IDs (here, we limit to 10,000 nodes for demonstration).
    projection_query = """
    MATCH (n:Identity)
    WITH n LIMIT 10000
    WITH collect(id(n)) AS limitedIdentityIds
    CALL gds.graph.project.cypher(
      'limitedIdentityProfileGraph',
      "MATCH (n) 
       WHERE id(n) IN $limitedIdentityIds 
          OR (n:Profile AND EXISTS { 
               MATCH (n)-[:contains_identity]-(i:Identity) 
               WHERE id(i) IN $limitedIdentityIds 
             })
       RETURN id(n) AS id, labels(n) AS labels",
      "MATCH (a:Identity)-[r:SIMILAR]-(b:Identity)
       WHERE id(a) IN $limitedIdentityIds AND id(b) IN $limitedIdentityIds
       RETURN id(a) AS source, id(b) AS target, type(r) AS type
       UNION
       MATCH (a:Identity)-[r:contains_identity]-(b:Profile)
       WHERE id(a) IN $limitedIdentityIds
       RETURN id(a) AS source, id(b) AS target, type(r) AS type",
      {parameters: {limitedIdentityIds: limitedIdentityIds}}
    ) YIELD graphName, nodeCount, relationshipCount
    RETURN graphName, nodeCount, relationshipCount
    """
    with driver.session() as session:
        projection_result = session.run(projection_query).single()
        if projection_result is None:
            print("Graph projection failed.")
            return
        print("Graph projected:", dict(projection_result))

    # Step 2: Run WCC on the projected graph.
    wcc_query = """
    CALL gds.wcc.stream('limitedIdentityProfileGraph')
    YIELD nodeId, componentId
    RETURN nodeId, componentId
    ORDER BY componentId, nodeId
    """
    with driver.session() as session:
        wcc_results = session.run(wcc_query)
        results = [record.data() for record in wcc_results]
        print("WCC results (sample):")
        for r in results[:10]:
            print(r)

    # Step 3: write the WCC results back to the nodes.
    writeback_query = """
    CALL gds.wcc.write('limitedIdentityProfileGraph', {
      writeProperty: 'wcc_component'
    })"""
    with driver.session() as session:
        session.run(writeback_query)

    # Step 4: Count the number of components.
    count_query = """
    CALL gds.wcc.stats('limitedIdentityProfileGraph')
    """
    with driver.session() as session:
        count_result = session.run(count_query).single()
        print("Component count:", dict(count_result))



def main():
    # Initialize the Neo4j handler.
    handler = Neo4jHandler(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Optionally delete existing nodes/relationships.
    # handler.delete_nodes()  # Uncomment if you wish to clear the DB first.
    
    # Calculate similarities on phone_number and email_address.
    create_similarity(handler.driver, "phone_number", similarity_threshold=0.80)
    create_similarity(handler.driver, "email_address", similarity_threshold=0.80)
    
    # Run WCC to cluster similar nodes.
    run_wcc(handler.driver)
    
    handler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate similarities for phone_number and email_address, then run WCC using Neo4j."
    )
    args = parser.parse_args()
    main()

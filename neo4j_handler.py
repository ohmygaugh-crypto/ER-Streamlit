import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Neo4jHandler:
    def __init__(self, uri, user, password):
        """Initialize the Neo4j driver."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Connected to Neo4j at {uri} as user {user}")

    def close(self):
        """Close the Neo4j driver connection."""
        self.driver.close()
        logger.info("Closed Neo4j connection")

    def execute_write(self, query, parameters=None):
        """Execute a write query with optional parameters."""
        with self.driver.session() as session:
            result = session.execute_write(lambda tx: tx.run(query, **(parameters or {})))
            return result

    def execute_read(self, query, parameters=None):
        """Execute a read query with optional parameters."""
        with self.driver.session() as session:
            return session.execute_read(lambda tx: list(tx.run(query, **(parameters or {}))))

    def delete_nodes(self, label=None):
        """
        Delete nodes and their relationships.

        If a label is provided, only nodes with that label will be deleted.
        Without a label, all nodes in the database will be deleted.
        """
        if label:
            query = f"MATCH (n:{label}) DETACH DELETE n"
        else:
            query = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.execute_write(lambda tx: tx.run(query))
        logger.info(f"Deleted nodes{' with label ' + label if label else ' from the database'}.")

    def merge_node(self, label, match_key, match_value, properties):
        """
        Merge a node by a given label and matching key.

        If a node with the provided key/value pair exists, it is updated with the given properties.
        Otherwise, a new node is created.

        Parameters:
            label (str): The label for the node.
            match_key (str): The property name to match on.
            match_value (any): The value of the property to match.
            properties (dict): A dictionary of properties to set on the node.
        """
        query = f"""
        MERGE (n:{label} {{{match_key}: $match_value}})
        SET n += $properties
        RETURN n
        """
        # Define a helper function that executes the query and returns the record within the transaction.
        def _merge_node(tx, query, match_value, properties):
            result = tx.run(query, match_value=match_value, properties=properties)
            return result.single()  # Consuming the result inside the transaction

        with self.driver.session() as session:
            record = session.execute_write(_merge_node, query, match_value, properties)
            if record:
                logger.debug(f"Node merged for label '{label}' with {match_key} = {match_value}.")
            return record


    def create_relationship(self, source_label, source_key, source_value,
                            target_label, target_key, target_value,
                            relationship_type, rel_properties=None):
        """
        Create a relationship between two existing nodes if they both exist.

        Parameters:
            source_label (str): Label of the source node.
            source_key (str): Property name to match the source node.
            source_value (any): Property value to match the source node.
            target_label (str): Label of the target node.
            target_key (str): Property name to match the target node.
            target_value (any): Property value to match the target node.
            relationship_type (str): Type of the relationship to create.
            rel_properties (dict, optional): Additional properties to set on the relationship.
        """
        query = f"""
        MATCH (a:{source_label} {{{source_key}: $source_value}})
        MATCH (b:{target_label} {{{target_key}: $target_value}})
        MERGE (a)-[r:{relationship_type}]->(b)
        SET r += $rel_properties
        RETURN a, b, r
        """
        
        def _create_relationship(tx, query, source_value, target_value, rel_properties):
            result = tx.run(query,
                            source_value=source_value,
                            target_value=target_value,
                            rel_properties=rel_properties)
            # Consume the result within the transaction.
            return result.single()
        
        with self.driver.session() as session:
            record = session.execute_write(_create_relationship, query, source_value, target_value, rel_properties or {})
            if not record:
                logger.warning(
                    f"Failed to create relationship '{relationship_type}' between nodes "
                    f"({source_label}:{source_key}={source_value}) and ({target_label}:{target_key}={target_value})."
                )
            else:
                logger.debug(
                    f"Created relationship '{relationship_type}' between nodes "
                    f"({source_label}:{source_key}={source_value}) and ({target_label}:{target_key}={target_value})."
                )
            return record

   



# Test code to run this module standalone.
if __name__ == "__main__":
    # Configure logging to output to the console.
    logging.basicConfig(level=logging.INFO)
    
    # Replace with your actual Neo4j connection details.
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password"
    
    handler = Neo4jHandler(uri, user, password)
    
    # Example: Merge a node.
    handler.merge_node("Person", "id", "123", {"name": "Alice", "age": 30})
    
    # Example: Create a relationship between two nodes.
    handler.create_relationship(
        source_label="Person", source_key="id", source_value="123",
        target_label="Company", target_key="name", target_value="OpenAI",
        relationship_type="WORKS_AT",
        rel_properties={"since": 2020}
    )
    
    # Example: Delete all nodes with a specific label.
    handler.delete_nodes(label="Person")
    
    handler.close()

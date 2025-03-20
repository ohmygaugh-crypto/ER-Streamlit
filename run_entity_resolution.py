import os
import logging
import argparse
import pandas as pd
from dotenv import load_dotenv
from neo4j_handler import Neo4jHandler

# Import Splink components using the confirmed syntax
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on, splink_datasets

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

def fetch_identities(handler):
    """
    Fetch all Identity nodes from the Neo4j database and return them as a list of dictionaries.
    Expected columns: id, full_name, email_address, zip_code, phone_number.
    """
    query = """
    MATCH (i:Identity)
    RETURN i.id AS id,
           i.id as unique_id,
           i.full_name AS full_name,
           i.email_address AS email_address,
           i.zip_code AS zip_code,
           i.phone_number AS phone_number,
           i.wcc_component as   wcc_component
    """
    result = handler.execute_read(query)
    # Consume the result within the transaction scope.
    records = [record.data() for record in result]
    return records

def run_entity_resolution(handler):
    """
    Extract Identity nodes from Neo4j, run entity resolution using Splink 4.0.7 with DuckDB,
    and return the resulting clusters as a Pandas DataFrame.
    """
    logger.info("Fetching Identity nodes from Neo4j...")
    identities = fetch_identities(handler)
    if not identities:
        logger.info("No Identity nodes found.")
        return None

    # Convert the list of identity records into a Pandas DataFrame.
    df = pd.DataFrame(identities)

    # Add a source_dataset column to the DataFrame.
    df["source_dataset"] = "dataset_1"  # Assign a default value for all records.

    logger.info(f"Fetched {len(df)} identity records.")

    # Create Splink settings using the new syntax.
    # Here we use our existing columns:
    # - NameComparison on full_name
    # - EmailComparison on email_address
    # - ExactMatch on zip_code and phone_number (with term frequency adjustments for zip_code)
    settings = SettingsCreator(
        link_type="dedupe_only",
        comparisons=[
            cl.NameComparison("full_name"),
            cl.EmailComparison("email_address"),
            cl.PostcodeComparison("zip_code").configure(term_frequency_adjustments=True),
            cl.LevenshteinAtThresholds("phone_number"),
        ],
        blocking_rules_to_generate_predictions=[
            block_on("wcc_component"),  
        ]
    )

    logger.info("Initializing DuckDB backend for Splink...")
    db_api = DuckDBAPI()  # Create a DuckDB backend instance

 
    logger.info("Initializing Splink Linker...")
    # Initialize the generic Linker with the DataFrame, settings, and DuckDB backend.
    linker = Linker(df, settings, db_api=db_api)

    # -------------------------
    # Training steps:
    # Estimate the probability that two random records match.
    linker.training.estimate_probability_two_random_records_match(
        [block_on("wcc_component")],
        recall=0.7,
    )

    # Estimate u probabilities using random sampling.
    linker.training.estimate_u_using_random_sampling(max_pairs=1e6)

    # Estimate m probabilities (true match likelihoods) using expectation maximisation.
    for property in settings.get_comparison_properties():
        linker.training.estimate_parameters_using_expectation_maximisation(property)

    # -------------------------
    # Prediction and Clustering:
    # Predict pairwise match scores.
    pairwise_predictions = linker.inference.predict(threshold_match_weight=-5)
    # Cluster the predictions at a given threshold (e.g. 0.95)
    clusters = linker.clustering.cluster_pairwise_predictions_at_threshold(
        pairwise_predictions, 0.95
    )
    # Convert the clusters to a Pandas DataFrame.
    df_clusters = clusters.as_pandas_dataframe()
    return df_clusters

def main():
    # Initialize the Neo4j handler.
    handler = Neo4jHandler(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Run the entity resolution process.
    clusters = run_entity_resolution(handler)
    if clusters is not None:
        logger.info("Entity resolution complete. Sample clusters:")
        print(clusters.head())
    else:
        logger.info("No clusters returned from entity resolution.")
    
    handler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run entity resolution on Identity nodes from Neo4j using Splink 4.0.7 with DuckDB."
    )
    args = parser.parse_args()
    main()

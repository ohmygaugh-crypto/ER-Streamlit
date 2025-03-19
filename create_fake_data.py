import os
import uuid
import random
import logging
import argparse
import requests
from dotenv import load_dotenv
from neo4j_handler import Neo4jHandler

# Load environment variables from the .env file.
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
    raise ValueError("Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in your .env file")

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_random_users(num_profiles):
    """Fetch random user data from the randomuser.me API."""
    url = f"https://randomuser.me/api/?results={num_profiles}&nat=us"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if the request fails.
    data = response.json()
    return data.get("results", [])

def apply_random_typo(text):
    """Introduce a random typo into the given text."""
    if len(text) < 2:
        return text
    option = random.choice(["delete", "swap", "insert", "replace"])
    index = random.randint(0, len(text) - 1)
    if option == "delete":
        # Remove the character at the chosen index.
        return text[:index] + text[index+1:]
    elif option == "swap":
        if len(text) < 2:
            return text
        # Swap the character at the chosen index with the next one.
        if index == len(text) - 1:
            index -= 1
        lst = list(text)
        lst[index], lst[index+1] = lst[index+1], lst[index]
        return "".join(lst)
    elif option == "insert":
        # Insert a random letter at the chosen index.
        letter = random.choice("abcdefghijklmnopqrstuvwxyz")
        return text[:index] + letter + text[index:]
    elif option == "replace":
        # Replace the character at the chosen index with a random letter.
        letter = random.choice("abcdefghijklmnopqrstuvwxyz")
        return text[:index] + letter + text[index+1:]
    else:
        return text

def main(num_profiles, typo_percentage, detached_percentage, delete_all):
    # Initialize the Neo4j handler.
    handler = Neo4jHandler(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if delete_all:
        logger.info("Deleting all nodes and relationships before proceeding.")
        handler.delete_nodes()
    
    # Fetch random users from the API.
    users = fetch_random_users(num_profiles)
    
    for user in users:
        # Extract the user's full name.
        name_data = user.get("name", {})
        first_name = name_data.get("first", "Unknown")
        last_name = name_data.get("last", "Unknown")
        full_name = f"{first_name} {last_name}"
        
        # Extract additional properties from the API result.
        email = user.get("email", "")
        phone = user.get("phone", "")
        location = user.get("location", {})
        postcode = location.get("postcode", "")
        if isinstance(postcode, int):
            postcode = str(postcode)
        
        # Create a Profile node for this person WITHOUT full_name property.
        profile_id = str(uuid.uuid4())
        handler.merge_node("Profile", "id", profile_id, {})  # No properties for Profile
        logger.debug(f"Created Profile node with id {profile_id}")
        
        # Determine a random number (1-10) of Identity nodes for this Profile.
        num_identities = random.randint(1, 10)
        for _ in range(num_identities):
            identity_id = str(uuid.uuid4())
            # Each Identity node always has the full_name.
            identity_props = {"full_name": full_name}
            
            # Prepare available extra properties.
            available_props = {
                "email_address": email,
                "zip_code": postcode,
                "phone_number": phone
            }
            # Randomly choose 2 or 3 properties to include.
            num_extra_props = random.choice([2, 3])
            selected_keys = random.sample(list(available_props.keys()), num_extra_props)
            for key in selected_keys:
                identity_props[key] = available_props[key]
            
            # Apply random typo/variation to a given percentage of identities.
            if random.random() < (typo_percentage / 100.0):
                # Choose one random property (if available) that is a non-empty string.
                keys = [k for k, v in identity_props.items() if isinstance(v, str) and v]
                if keys:
                    key_to_modify = random.choice(keys)
                    original_value = identity_props[key_to_modify]
                    identity_props[key_to_modify] = apply_random_typo(original_value)
                    logger.info(f"Applied typo to property '{key_to_modify}' for Identity {identity_id}")
            
            # Create the Identity node.
            handler.merge_node("Identity", "id", identity_id, identity_props)
            logger.debug(f"Created Identity node with id {identity_id}")
            
            # Randomly decide whether to attach the Identity to the Profile.
            if random.random() >= (detached_percentage / 100.0):
                # Create the CONTAINS_IDENTITY relationship.
                handler.create_relationship(
                    source_label="Profile", source_key="id", source_value=profile_id,
                    target_label="Identity", target_key="id", target_value=identity_id,
                    relationship_type="CONTAINS_IDENTITY"
                )
                logger.debug(f"Attached Identity {identity_id} to Profile {profile_id}")
            else:
                logger.info(f"Detached Identity {identity_id} (not attached to Profile {profile_id})")
    
    handler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load a specified number of Profile nodes (with associated Identity nodes) into Neo4j using randomuser.me API."
    )
    parser.add_argument(
        "--num_profiles", type=int, default=5,
        help="Number of Profile nodes (each with 1-10 Identity nodes) to create."
    )
    parser.add_argument(
        "--typo_percentage", type=float, default=10,
        help="Percentage of Identity nodes to apply random typos/variations (default 10%)."
    )
    parser.add_argument(
        "--detached_percentage", type=float, default=10,
        help="Percentage of Identity nodes to leave unattached to the Profile node (default 10%)."
    )
    parser.add_argument(
        "--delete_all", action="store_true",
        help="Delete all existing nodes and relationships before running."
    )
    args = parser.parse_args()
    main(args.num_profiles, args.typo_percentage, args.detached_percentage, args.delete_all)

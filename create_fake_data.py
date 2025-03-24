import os
import uuid
import random
import logging
import argparse
import requests
from dotenv import load_dotenv
from neo4j_handler import Neo4jHandler
import numpy as np
from nicknames import NickNamer

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

# using numpy, create a random number generator with gaussian distribution with integers between 1 and 20 with a mean of 7 and a standard deviation of 3

    

def fetch_random_users(num_profiles):
    """Fetch random user data from the randomuser.me API."""
    url = f"https://randomuser.me/api/?results={num_profiles}&nat=us"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if the request fails.
    data = response.json()
    return data.get("results", [])



class User:
    def __init__(self, user_data):
        self.data = user_data

        # Extract additional properties from the API result.
        self.name_data = user_data.get("name", {})
        self.first_name = self.name_data.get("first", "Unknown")
        self.last_name = self.name_data.get("last", "Unknown")
        self.nickname = self.set_nickname()

        self.birth_year = user_data.get("dob", {}).get("date", "")[:4]
        self.email_address = self.set_email()
        
        self.phone_number = str("".join(filter(str.isdigit, user_data.get("phone", ""))))

        location = user_data.get("location", {})
        self.street_number = str(location.get("street", {}).get("number", ""))
        self.street_name = location.get("street", {}).get("name", "")
        self.city = location.get("city", "")
        self.state = location.get("state", "")
        self.country = location.get("country", "")
        self.zip_code = str(location.get("postcode", ""))

    @property
    def full_address(self):
        return f"{self.street_number} {self.street_name}, {self.city}, {self.state} {self.zip_code}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


    def set_nickname(self):
        nn = NickNamer()
        names = nn.nicknames_of(self.first_name)
        if len(names) == 0:
            return self.first_name
        else:
            return random.choice([*names])
    
    def set_email(self):
        domain = random.choice(["gmail", "yahoo", "hotmail", "outlook"])
        first = random.choice([self.first_name, self.nickname, self.first_name[:1]])
        last = random.choice([self.last_name])
        optional = random.choice(["", self.birth_year,str(random.randint(1, 100))])

        return f"{first}.{last}{optional}@{domain}.com"
    
    
    
    def add_typo(self, property_name):
        """Introduce a random typo into the given property"""
        if property_name == "full_address":
            property_name = random.choice(["street_number", "street_name", "city", "state", "zip_code"])
        
        #get property value
        prop_value = getattr(self, property_name)

        # update property
        
        setattr(self, property_name, self._apply_random_typo(prop_value))

    def _apply_random_typo(self, text):
        """Introduce a random typo into the given text."""
        option = random.choice(["delete", "swap", "insert", "replace"])
        index = random.randint(0, len(str(text)) - 1)

        if text.isnumeric():
            number = random.randint(0, 9)
            return str(text)[:index] + str(number) + str(text)[index:]
        elif "@" in text :
            email = text.split("@")
            rand = random.random()
            if rand < 0.3:
                #change the username
                return self._apply_random_typo(email[0]) + "@" + email[1]
            elif rand < 0.6:
                #change first name to nickname
                name = email[0].split(".")

                return f"""{self.nickname}.{name[1]}@{email[1]}"""
            else:
            #change the domain
                return email[0] + "@" + random.choice(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"])
        
        elif option == "delete":
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

def main(num_profiles, typo_percentage, delete_all):
    # Initialize the Neo4j handler.
    handler = Neo4jHandler(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    if delete_all:
        handler.delete_nodes()
        logger.info("Deleting all nodes and relationships before proceeding.")

    
    # Fetch random users from the API.
    api_data = fetch_random_users(num_profiles)


    def make_profile_node(handler, name):
        profile_id = str(uuid.uuid4())
        handler.merge_node("Profile", "id", profile_id, {"name": name})
        return profile_id

    
    for data in api_data:
        user = User(data)
        num_ids = abs(int(np.random.normal(8, 5)) )

        if num_ids > 4:
            num_profiles = random.choice([1,1,1,1,1,1,2,2,2,2,3])
        else:
            if num_ids == 0:
                num_ids = 1
            num_profiles = 1
        
        profiles = [make_profile_node(handler, user.full_name) for i in range(num_profiles)]
        
        # Determine a random number (1-10) of Identity nodes for this Profile.
        profile_idx = 0
        for i in range(num_ids):
            # select profile id based on the number of profiles (if there are 4 profiles, the first 1/4th will be assigned to the first profile)
            # print(i, num_ids, profile_idx, num_profiles, i/num_ids, (profile_idx+1)/num_profiles)
            
            if i/num_ids > (profile_idx + 1)/num_profiles:
                profile_idx += 1
           
            profile_id = profiles[profile_idx]

            identity_id = str(uuid.uuid4())

            properties = ["first_name", "last_name"]
            
            # Prepare available extra properties.
            available_props = ["email_address", "zip_code", "phone_number", "full_address"]
            # Randomly choose 2 or 3 properties to include.
            num_extra_props = random.choice([2,3,3,3,4])
            selected_keys = random.sample(available_props, num_extra_props)
            for key in selected_keys:
                properties.append(key)

            # Apply random typo/variation to a given percentage of identities.
            if i > 0 and random.random() < (typo_percentage / 100.0):
                # Choose one random property (if available) that is a non-empty string.
                user.add_typo(random.choice(selected_keys))
            
            # create a dictionary based on the properties
            identity_props = {key: getattr(user, key) for key in properties}

            # Create the Identity node.

            handler.merge_node("Identity", "id", identity_id, identity_props)
            logger.debug(f"Created Identity node with id {identity_id}")
            

            # Attach the Identity node to the Profile node.
            handler.create_relationship(
                source_label="Profile", source_key="id", source_value=profile_id,
                target_label="Identity", target_key="id", target_value=identity_id,
                relationship_type="contains_identity"
            )
            logger.debug(f"Attached Identity {identity_id} to Profile {profile_id}")
        
        # if len(profiles) > 1 and profile_idx < len(profiles) - 1:
        #     print("***",profile_idx+1, len(profiles), user.full_name, "\n")
        # else:
        #     print("*", profile_idx+1, len(profiles), user.full_name, "\n")
            # for i in range(profile_idx + 1, len(profiles)):
            #     handler.delete_node("Profile", "id", profiles[i])
    
    handler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load a specified number of Profile nodes (with associated Identity nodes) into Neo4j using randomuser.me API."
    )
    parser.add_argument(
        "--num_profiles", type=int, default=100,
        help="Number of Profile nodes (each with 1-10 Identity nodes) to create."
    )
    parser.add_argument(
        "--typo_percentage", type=float, default=10,
        help="Percentage of Identity nodes to apply random typos/variations (default 10%)."
    )
    parser.add_argument(
        "--delete_all", action="store_true",
        help="Delete all existing nodes and relationships before running."
    )
    args = parser.parse_args()
    main(args.num_profiles, args.typo_percentage, args.delete_all)

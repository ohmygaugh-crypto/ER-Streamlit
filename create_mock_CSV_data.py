#!/usr/bin/env python3

"""
create_mock_data_csv.py

Fetches random user data from randomuser.me (or a similar service) and creates
mock data in CSV format that imitates having multiple 'Profiles' and multiple
'Identity' rows. Each row in the CSV represents an Identity and includes:
- a parent Profile ID and Profile name,
- first_name, last_name, birth_year, etc.,
- and possibly random typos in selected fields (based on a user-defined percentage).

Usage example:
    python create_mock_data_csv.py --num_profiles=100 --typo_percentage=10 --output_file="mock_data.csv"
"""

import requests
import random
import logging
import argparse
import csv
import uuid
import numpy as np
# If you use the nicknames library: pip install nicknames
# from nicknames import NickNamer
# For demonstration, let's fallback gracefully if not installed.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from nicknames import NickNamer
    NICKNAMES_AVAILABLE = True
except ImportError:
    NICKNAMES_AVAILABLE = False
    logger.warning("nicknames library is not installed. Nickname feature will be limited.")


def fetch_random_users(num_profiles):
    """
    Fetch random user data from the randomuser.me API.
    Returns a list of user dicts with relevant attributes.
    """
    url = f"https://randomuser.me/api/?results={num_profiles}&nat=us"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


class User:
    """
    Simple container for user data fetched from randomuser.me,
    plus logic for generating nicknames, emails, phone numbers,
    and introducing random typos.
    """
    def __init__(self, user_data):
        self.user_data = user_data

        # Extract basic info
        self.name_data = user_data.get("name", {})
        self.first_name = self.name_data.get("first", "Unknown")
        self.last_name = self.name_data.get("last", "Unknown")
        self.nickname = self._choose_nickname()

        dob = user_data.get("dob", {})
        self.birth_year = str(dob.get("date", "")[:4])  # 'YYYY-MM-DD...' -> 'YYYY'

        # Email address: random combination of first, last, year, etc.
        self.email_address = self._generate_email()

        # Phone number: just digits from the API phone.
        phone_raw = user_data.get("phone", "")
        self.phone_number = "".join(filter(str.isdigit, phone_raw))

        # Address fields
        location = user_data.get("location", {})
        self.street_number = str(location.get("street", {}).get("number", ""))
        self.street_name = location.get("street", {}).get("name", "")
        self.city = location.get("city", "")
        self.state = location.get("state", "")
        self.country = location.get("country", "")
        self.zip_code = str(location.get("postcode", ""))

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_address(self):
        return f"{self.street_number} {self.street_name}, {self.city}, {self.state} {self.zip_code}"

    def _choose_nickname(self):
        """
        Uses the nicknames library if available, otherwise falls back to the first name.
        """
        if NICKNAMES_AVAILABLE:
            nn = NickNamer()
            possible_nicknames = nn.nicknames_of(self.first_name)
            if possible_nicknames:
                return random.choice(list(possible_nicknames))
        return self.first_name

    def _generate_email(self):
        domain = random.choice(["gmail", "yahoo", "hotmail", "outlook"])
        first_part = random.choice([self.first_name, self.nickname, self.first_name[:1]])
        last_part = random.choice([self.last_name, self.last_name[:1]])
        optional = random.choice(["", self.birth_year, self.birth_year[-2:], str(random.randint(1, 100))])
        return f"{first_part}{last_part}{optional}@{domain}.com".lower()

    def add_typo(self, property_name):
        """
        Introduce a random typo into the specified property (e.g. 'first_name').
        If property_name == 'full_address', we randomly pick an address field to modify.
        """
        if property_name == "full_address":
            property_name = random.choice(
                ["street_number", "street_name", "city", "state", "zip_code"]
            )

        current_value = getattr(self, property_name, None)
        if not current_value or not isinstance(current_value, str):
            return  # If it's empty or not a string, skip

        original_value = current_value
        new_value = self._apply_random_typo(current_value)
        setattr(self, property_name, new_value)
        logger.debug(f"Applying typo: {property_name}: '{original_value}' -> '{new_value}'")

    def _apply_random_typo(self, text):
        """
        Introduce a random single-character error (delete, swap, insert, replace)
        or regenerate an email.
        """
        if not text:
            return text

        option = random.choice(["delete", "swap", "insert", "replace"])

        # If email, sometimes just regenerate the entire email.
        if "@" in text:
            # 1 in 3 chance we fully regenerate the email.
            if random.random() < 0.33:
                return self._generate_email()

        if len(text) == 1:
            # If we have only one character, we can only do replace or insert.
            option = random.choice(["insert", "replace"])

        index = random.randint(0, len(text) - 1)

        if option == "delete":
            # Remove 1 char
            return text[:index] + text[index+1:]

        elif option == "swap":
            # Swap with the next char if possible
            if index < len(text) - 1:
                # swap
                lst = list(text)
                lst[index], lst[index+1] = lst[index+1], lst[index]
                return "".join(lst)
            else:
                # fallback to replace if we can't swap
                letter = random.choice("abcdefghijklmnopqrstuvwxyz")
                return text[:index] + letter + text[index+1:]

        elif option == "insert":
            # Insert a random letter at index
            letter = random.choice("abcdefghijklmnopqrstuvwxyz")
            return text[:index] + letter + text[index:]

        elif option == "replace":
            letter = random.choice("abcdefghijklmnopqrstuvwxyz")
            return text[:index] + letter + text[index+1:]

        # Fallback: no change
        return text


def main(num_profiles, typo_percentage, output_file):
    """
    1) Fetch random user data from randomuser.me
    2) For each user, create 1..N 'Profile' nodes
    3) For each 'Profile', create 1..M 'Identities'
    4) Introduce random typos in selected fields
    5) Write all Identity rows to CSV, including their associated Profile info
    """
    logger.info(f"Generating mock data for {num_profiles} profiles...")
    api_data = fetch_random_users(num_profiles)

    rows_to_write = []

    # The number of identity nodes depends on random gaussian logic or your own preference
    # e.g. a normal distribution around 8 with std=5, clipped to positives
    # We'll keep the same approach from the original script.
    for data in api_data:
        user = User(data)

        # random number of Identities
        num_ids = abs(int(np.random.normal(8, 5)))  # e.g. mean=8, std=5

        # pick how many distinct "Profile" nodes each user might produce
        # (in the original code, we used some logic to decide 1 or 2 or 3 profiles)
        if num_ids > 4:
            num_profiles_for_user = random.choice([1, 1, 1, 2, 2, 3])
        else:
            num_profiles_for_user = 1

        # Create the Profile IDs and store them
        profile_ids = [str(uuid.uuid4()) for _ in range(num_profiles_for_user)]
        profile_name = user.full_name  # in the original script, we used the same name for each 'Profile'

        # We'll distribute the Identity rows across these profiles
        profile_idx = 0

        for i in range(num_ids):
            # If the fraction i/num_ids > fraction dividing the profiles,
            # move to next profile. (just a simple distribution approach)
            if num_profiles_for_user > 1:
                if i / num_ids > (profile_idx + 1) / num_profiles_for_user:
                    profile_idx += 1

            current_profile_id = profile_ids[profile_idx]

            # Possibly apply a typo
            # For each new identity row (beyond the first?), there's a chance to add a typo
            if i > 0 and random.random() < (typo_percentage / 100.0):
                # choose a random field
                possible_fields = ["first_name", "last_name", "email_address",
                                   "phone_number", "full_address", "birth_year"]
                chosen_field = random.choice(possible_fields)
                user.add_typo(chosen_field)

            # Create a row for the Identity
            identity_id = str(uuid.uuid4())
            row = {
                "profile_id": current_profile_id,
                "profile_name": profile_name,
                "identity_id": identity_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "nickname": user.nickname,
                "birth_year": user.birth_year,
                "email_address": user.email_address,
                "phone_number": user.phone_number,
                "street_number": user.street_number,
                "street_name": user.street_name,
                "city": user.city,
                "state": user.state,
                "country": user.country,
                "zip_code": user.zip_code
            }
            rows_to_write.append(row)

    # Now write the CSV
    fieldnames = [
        "profile_id",
        "profile_name",
        "identity_id",
        "first_name",
        "last_name",
        "nickname",
        "birth_year",
        "email_address",
        "phone_number",
        "street_number",
        "street_name",
        "city",
        "state",
        "country",
        "zip_code"
    ]

    logger.info(f"Writing {len(rows_to_write)} rows to {output_file}...")

    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_write)

    logger.info("Finished writing CSV mock data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate mock entity-resolution data in CSV format."
    )
    parser.add_argument("--num_profiles", type=int, default=10,
                        help="Number of random 'users' to fetch from randomuser.me (default 10).")
    parser.add_argument("--typo_percentage", type=float, default=10.0,
                        help="Chance (0..100) that each new Identity row (beyond the first) has a random typo (default 10%).")
    parser.add_argument("--output_file", type=str, default="mock_data.csv",
                        help="Output CSV filename (default 'mock_data.csv').")

    args = parser.parse_args()
    main(args.num_profiles, args.typo_percentage, args.output_file)

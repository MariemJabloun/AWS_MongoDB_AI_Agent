import csv
import logging
import certifi
import dns.resolver

from pymongo import MongoClient
import boto3
from botocore.exceptions import ClientError

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["169.254.169.253", "8.8.8.8"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mdb_import")


def get_secret(secret_name):
    """
    Retrieve secret from AWS Secrets Manager
    """
    client_in = boto3.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client_in.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error("Error retrieving secret %s: %s", secret_name, e)
        raise e

    if "SecretString" in get_secret_value_response:
        logger.info("Successfully retrieved secret %s", secret_name)
        return get_secret_value_response["SecretString"]

    # Explicitly satisfy R1710 by handling the missing key case
    logger.warning("Secret %s did not contain a SecretString.", secret_name)
    return None


# Get the MongoDB connection string from Secrets Manager
logger.info("Retrieving MongoDB connection string from Secrets Manager")
mongodb_uri = get_secret("workshop/atlas_secret5")  # Replace with your secret name

# MongoDB connection
logger.info("Connecting to MongoDB Atlas")
client = MongoClient(mongodb_uri, tlsCAFile=certifi.where())

db = client["travel"]
collection = db["asia"]

# CSV file path
CSV_FILE_PATH = "./anthropic-travel-agency.trip_recommendations.csv"

logger.info("Starting data import from CSV to MongoDB")

index = 1
with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        row["index"] = index
        index += 1
        # loop over columns and accumulate all detail_embedding into an array
        detail_embedding = []
        new_row = {}
        for column in row.keys():
            if column.startswith("details_embedding"):
                detail_embedding.append(float(row[column]))
            else:
                new_row[column] = row[column]

        new_row["details_embedding"] = detail_embedding

        collection.insert_one(new_row)
        if index % 25 == 0:
            logger.info("Inserted %s rows", index)

logger.info("Finished import successfully")

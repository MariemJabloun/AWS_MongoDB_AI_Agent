import pymongo
from langchain_aws import BedrockEmbeddings
from utils import bedrock, aws_utils

# define the bedrock client
boto3_bedrock = bedrock.get_bedrock_client()
mongo_uri = aws_utils.get_secret("workshop/atlas_secret")
# Connect to the MongoDB database
client = pymongo.MongoClient(mongo_uri)
db = client["sample_mflix"]
collection = db["movies"]

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"

# Initiate the embedding
embeddings = BedrockEmbeddings(model_id=EMBEDDING_MODEL_ID, client=boto3_bedrock)


# Get the required documents in the collection
documents = collection.find({"year": {"$gt": 2014}})
VECTOR_FIELD_NAME = "eg_vector"
FIELD_NAME_TO_BE_VECTORIZED = "fullplot"
print("started processing...")
i = 0
j = 0
# Loop over all documents and vectorize the collections for the selected field
for document in documents:

    query = {"_id": document["_id"]}
    j += 1
    doc_num = i + j
    if FIELD_NAME_TO_BE_VECTORIZED in document and VECTOR_FIELD_NAME not in document:
        i += 1
        # generate embedding
        text_as_embeddings = embeddings.embed_documents(
            [document["title"] + " " + document[FIELD_NAME_TO_BE_VECTORIZED]]
        )
        # update the document in MongoDB Atlas
        update = {"$set": {VECTOR_FIELD_NAME: text_as_embeddings[0]}}
        collection.update_one(query, update)

        print(f"collection updated at document {doc_num}")

    if i % 5 == 0:
        print("processed: " + str(i) + " records")
    if i > 200:
        break

print("finished processing: " + str(i) + " records")

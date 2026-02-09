import pymongo
from langchain_aws import BedrockEmbeddings
from utils import aws_utils, bedrock

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
boto3_bedrock = bedrock.get_bedrock_client()

# Initiate the embedding
embeddings = BedrockEmbeddings(model_id=EMBEDDING_MODEL_ID, client=boto3_bedrock)
FIELD_NAME_TO_BE_VECTORIZED = "fullplot"

# filter the data using the criteria and do a schematic search
def mdb_query(query):
    text_as_embeddings = embeddings.embed_documents([query])
    embedding_value = text_as_embeddings[0]
    print("embedding size: " + str(len(embedding_value)))

    # get the vector search results based on the filter conditions.
    response = collection.aggregate(
        [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "eg_vector",
                    "queryVector": text_as_embeddings[0],
                    "numCandidates": 200,
                    "limit": 4,
                }
            },
            {
                "$project": {
                    "score": {"$meta": "searchScore"},
                    FIELD_NAME_TO_BE_VECTORIZED: 1,
                    "title": 1,
                    "claim_id": 1,
                    "_id": 0,
                }
            },
        ]
    )

    # Result is a list of docs with the array fields
    docs = list(response)

    # Extract an array field from the docs
    array_field = [
        doc["title"] + ": " + doc[FIELD_NAME_TO_BE_VECTORIZED] for doc in docs
    ]

    # Join array elements into a string
    llm_input_text = "\n \n".join(str(elem) for elem in array_field)

    # utility
    newline, bold, unbold = "\n", "\033[1m", "\033[0m"
    print(
        newline + bold + "Given Input : " + unbold + newline + llm_input_text + newline
    )


print("started...")
mongo_uri = aws_utils.get_secret("workshop/atlas_secret")
print("got credentials...")
# Connect to the MongoDB database
client = pymongo.MongoClient(mongo_uri)
print("connected to mongoDB...")
db = client["sample_mflix"]
collection = db["movies"]

# Another query string = "traveling romantic story"
QUERY_STRING = "traveling stars manual"

print("\n" + "Searching for: " + QUERY_STRING + "\n")

mdb_query(QUERY_STRING)

print("finished search...")

print("Done!")

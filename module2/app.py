import json
import time
import streamlit as st
import pymongo
from langchain_aws import BedrockEmbeddings
from utils import aws_utils, bedrock

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
TEXTGEN_MODEL_ID = "mistral.mistral-large-2402-v1:0"

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
    response_in = collection.aggregate(
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
    docs = list(response_in)

    # Extract an array field from the docs
    array_field = [doc[FIELD_NAME_TO_BE_VECTORIZED] for doc in docs]

    # Join array elements into a string
    llm_input_text = "\n \n".join(str(elem) for elem in array_field)

    # utility
    newline, bold, unbold = "\n", "\033[1m", "\033[0m"
    print(
        newline + bold + "Given Input : " + unbold + newline + llm_input_text + newline
    )

    return llm_input_text


print("started...")
mongo_uri = aws_utils.get_secret("workshop/atlas_secret")
print("got credentials...")

# Connect to the MongoDB database
client = pymongo.MongoClient(mongo_uri)
print("connected to mongoDB...")
db = client["sample_mflix"]
collection = db["movies"]


# Streamed response emulator
def response_generator(query_string):
    res = mdb_query(query_string)

    print("finished search...")

    prompt = f"""Human: Create a mashup script based on the descriptions below.
    Create a single paragraph description.
    {res}
    \n\nBot: Let me create the script for you...
    """
    print(f"constructed prompt: {prompt}")

    body = json.dumps({
        "prompt": prompt
    })

    # invoke text generation model
    response = boto3_bedrock.invoke_model(modelId=TEXTGEN_MODEL_ID, body=body)

    response_body = json.loads(response["body"].read())
    output_text = response_body["outputs"][0]["text"]
    print(output_text)

    for word in output_text.split():
        yield word + " "
        time.sleep(0.05)


st.title("Simple chat")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if user_prompt := st.chat_input("Let's create a movie description:"):
    # Add user message to chat history
    st.session_state.messages.append(
        {"role": "user", "content": "Let me create the script for you about: " + user_prompt}
    )
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response_str = st.write_stream(response_generator(user_prompt))
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_str})

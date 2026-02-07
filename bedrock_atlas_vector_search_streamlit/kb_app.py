import time
import json
import os
import boto3
import streamlit as st
from langchain_aws import AmazonKnowledgeBasesRetriever

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

print("started...")

# initialize AmazonKnowledgeBaseRetriever
retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=os.environ.get("BEDROCK_KB_ID"),
    region_name=AWS_REGION,
    retrieval_config={
        "vectorSearchConfiguration": {
            "numberOfResults": 5,
            "overrideSearchType": "SEMANTIC",
        }
    },
)

# Streamed response emulator
def response_generator(query_string):
    res = retriever.invoke(query_string, region_name=AWS_REGION)

    print("finished search...")

    bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)

    prompt = f"""Human: You are expert on best practices for managing MongoDB clusters.
    {res}
    \n\nBot: Let me answer your question ...
    """
    print(f"constructed prompt: {prompt}")

    body = json.dumps({
        "prompt": prompt
    })

    # invoke text generation model
    response_in = bedrock.invoke_model(
        modelId="mistral.mistral-large-2402-v1:0",
        body=body
    )

    response_body = json.loads(response_in['body'].read())
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
if user_prompt := st.chat_input("Type your query:"):
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user", 
        "content": "Let me create the script for you about: " + user_prompt,
    })
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(user_prompt))
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

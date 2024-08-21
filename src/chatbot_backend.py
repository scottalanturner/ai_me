from langchain_aws import ChatBedrock, AmazonKnowledgeBasesRetriever
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
import boto3
import os
import json
from botocore.exceptions import ClientError
from config import config

def chatbot():
    '''
    Instantiate the chatbot

    We have different cases as to where our credentials are coming from
    1. Running in an AWS environment (e.g., ECS, Lambda). Check the ENV for AWS_EXECUTION_ENV.
    In this case the docker container is running with an IAM role that has access to the secret. Check the Policy config for the IAM user.
    
    2. Running locally in a Docker container
    In this case the AWS credentials are passed in as environment variables from the command line (if you're running from the command line)

    3. Running locally on a developer's machine from the command line
    In this case the boto3 client will use the AWS CLI credentials stored in the ~/.aws/credentials file
    '''

    region_name = config.get('region_name')
    aws_access_key_id = None
    aws_secret_access_key = None
    session = None

    # When running in a container on AWS, we use the secret manager to get the credentials
    # Create a Secrets Manager client
    if os.environ.get('AWS_EXECUTION_ENV') is not None:
        secret_name = "prod/ai-me/ecs_image"

        # Running in an AWS environment (e.g., ECS, Lambda)
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e
        
        secret_dict = json.loads(get_secret_value_response['SecretString'])

        aws_access_key_id = secret_dict.get('aws_access_key_id')
        aws_secret_access_key = secret_dict.get('aws_secret_access_key')
    
    # loading from Docker
    elif os.environ.get('aws_access_key_id') is not None:
       # Running locally (e.g., Docker or from command line)
        aws_access_key_id=os.environ.get('aws_access_key_id')
        aws_secret_access_key=os.environ.get('aws_secret_access_key')
        if (aws_access_key_id is None or aws_secret_access_key is None):
            raise ValueError("AWS credentials not found")
        
        session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
    # Running on local machine without docker, pull from ~/.aws/credentials file
    else:
        session = boto3.session.Session()

    # bedrock client, using the session credential for the region
    client = session.client(
        service_name='bedrock-runtime',
        region_name=region_name
    )

    # Change this to experiment with different models
    model_id = config.get('model_id')

    chat_bedrock = ChatBedrock(
        #credentials_profile_name=os.environ.get("AWS_PROFILE"),
        region_name=region_name,
        model_id=model_id,
        client=client
        #temperature=config.get('temperature'),
        #max_tokens_to_sample=config.get('max_tokens_to_sample')
    )
    # Create a Bedrock Knowledge Base Retriever instance
    knowledge_base_id = None#config.get('knowledge_base_id')
    retriever = None

    if (knowledge_base_id is not None):
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=knowledge_base_id,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
            client=client
        )
    return chat_bedrock, retriever


def chat_memory():
    '''
    Create a function to store the chat history
    '''
    chat_bedrock, retriever = chatbot()
    memory = ConversationBufferMemory(
        llm=chat_bedrock,
        memory_key="history",
        return_messages=True,
        max_tokens=200
    )
    return memory

def conversation(input_text: str, memory):
    '''
    Create a function to create a chat chain
    '''
    chat_bedrock, retriever = chatbot()

    chat_chain = ConversationChain(
        llm=chat_bedrock,
        memory=memory,
        #retriever=retriever,
        verbose=True
    )
    chat_reply = chat_chain.predict(input=input_text)
    return chat_reply
from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock, AmazonKnowledgeBasesRetriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableParallel
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from botocore.exceptions import ClientError
import boto3
import streamlit as st
from config import config
import os
import json
from operator import itemgetter

class ChatBot:
    @staticmethod
    @st.cache_resource
    def get_bedrock_client():
        aws_access_key_id = None
        aws_secret_access_key = None
        boto_session = None

        # When running in a container on AWS, we use the secret manager to get the credentials
        # Create a Secrets Manager client
        if os.environ.get('AWS_EXECUTION_ENV') is not None:
            secret_name = "prod/ai-me/ecs_image"

            # Running in an AWS environment (e.g., ECS, Lambda)
            boto_session = boto3.session.Session()

            client = boto_session.client(
                service_name='secretsmanager',
                region_name=config.get('region_name')
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
            
            boto_session = boto3.session.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=config.get('region_name')
            )
        # Running on local machine without docker, pull from ~/.aws/credentials file
        else:
            boto_session = boto3.session.Session()

        # bedrock client, using the session credential for the region
        bedrock_client = boto_session.client(
            service_name='bedrock-runtime',
            region_name=config.get('region_name')
        )
        print('ChatBot initialized')
        return bedrock_client
    
    @staticmethod
    def get_prompt_template():    
        template = '''Answer the question using the following context along with your existing knowledge. If you don't know the answer, please say so.

        Your response should:
        - Reflect the tone of voice (casual, friendly) of the content writer.
        - Incorporate specific phrases, idioms, or jargon that are characteristic of the content writer.
        - Match the pacing and rhythm of the content writer, using short, punchy sentences.
        - Use sentence structures and complexity that mirror the content writer's style.
        - Convey the same emotional undertone (enthusiasm, skepticism, calmness, etc.) found in the context.
        - Maintain the same point of view as the content writer, whether it's first person, third person, etc.
        - Include cultural or contextual references that align with those found in the context.
        - Incorporate humor or sarcasm if it matches the style of the content writer.

        Context:
        {context}

        Question: {question}'''

        prompt = ChatPromptTemplate.from_template(template)

        return prompt
    
    @staticmethod
    def init_model(bedrock_client):
        prompt = ChatBot.get_prompt_template()

        # Amazon Bedrock - KnowledgeBase Retriever 
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=config.get('knowledge_base_id'),
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
            client=bedrock_client,
        )

        model_kwargs =  { 
            "max_tokens": 2048,
            "temperature": 0.0,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman"],
        }
        model = ChatBedrock(
            client=bedrock_client,
            model_id=config.get('model_id'),
            model_kwargs=model_kwargs,
        )       

        chain = (
            RunnableParallel({
                "context": itemgetter("question") | retriever,
                "question": itemgetter("question"),
                "history": itemgetter("history"),
            })
            .assign(response = prompt | model | StrOutputParser())
        )
        # Streamlit Chat Message History
        history = StreamlitChatMessageHistory(key="chat_messages")

        # Chain with History
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: history,
            input_messages_key="question",
            history_messages_key="history",
            output_messages_key="response",
        )

        return history, chain_with_history

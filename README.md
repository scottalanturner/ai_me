This is roughly how I did it for the Streamlit app, integrating with Bedrock and ElevenLabs. If I had to run the Docker image again locally it probably wouldn't work, because of the changes I made for the EC2 instance (the ENTRYPOINT line vs. what was there before)

# Write code 
- Start incrementally, build+test+run each step for each small feature

## AWS Session access
We have three cases for accessing AWS resources from the boto session. You can see the coding examples in `chatbot_backend.py`
1. Locally using the AWS CLI default profile 
This `access_key_id` and `secret_access_key` are in the local cli properties file.

2. Locally from a Docker image
Docker doesn't have access to the env, so the access creds are passed on the command line when running docker. Note this was for a streamlit app so the ports are mapped.

`docker run -d -e aws_access_key_id=<replace> -e aws_secret_access_key=<replace> -p 8501:8501 <image_name>:<version>`

3. Running in an AWS env
No idea. In the EC2 instance shell, ec2 is added to the docker group. I think this skipped having to use secrets. Secrets were for AppRunner, but that blew up and we switched to ec2 because it allows websockets (AppRunner does not).

Old way?
This one is the most challenging. The key/vals are in AWS secrets manager.
So - without valid authentication to get the authentication credentials, an IAM user/role had to have permissions to access the secret. This is the same user/role that is running the instance.

# Run locally
- Run from a shell/debugger

# Source control
Put the code in a private/public GitHub repo.

# Dockerize
- Build a docker image
- Run from a container

Woohoo! It runs locally. Which means nothing.



# Build image on AWS
CodeCommit is dead, so we must use a GitHub integration (assuming the code is in a private repo on git)

### CodeBuild
CodeBuild is going to create our Docker image on AWS, and store it in ECR.

First, create an empty ECR repository. I don't recall what I did for this step.

Then:

- Create the config on codebuild through the AWS console.
- It will need GitHub access.
- Do this with a fine-grained token giving just the necessary permissions to pull from a single repo (read, pull)

CodeBuild needs a buildspec.yml file to pull everything together and build the Docker image. This file is in the github repo.

Set your constants in buildspec.yml and push them to the repo. That's the quick and dirty way.

The steps roughly are:

1. Set your ECR repository id in the file (or pull it from the ENV). I didn't pull mine from the ENV, it's hardcoded.
2. Install Git
3. Connect to ECR (permissions are going to be needed to be set here)
4. Clone the repo
5. Build the docker image
6. Push the image to ECR
7. Tag the image

That's what's going on in the yaml file.

From the CodeBuild console, build the image. Check the logs for errors. If there are issues:

Fix the code/yaml locally.
Commit the code and push it to github
Try the build again (it will pull latest code, or whatever version you tell it)

Hooray! Now you have a docker image. Which probably has problems and won't run, but at least you have the steps to rebuild the image

# Start EC2 instance

Just watch this video, the 2nd half. Note he is pulling a docker image from docker hub, while we are pulling it from ECR. So many of his steps aren't relevant.

https://www.youtube.com/watch?v=DflWqmppOAg

Look at ec2-connect-commands file for the shell commands.


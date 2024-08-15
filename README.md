This is roughly how I did it for the Streamlit app, integrating with Bedrock and ElevenLabs. If I had to run the Docker image again locally it probably wouldn't work, because of the changes I made for the EC2 instance (the ENTRYPOINT line vs. what was there before)

# Write code 
- Start incrementally, build+test+run each step for each small feature

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


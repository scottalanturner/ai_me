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

**NOTE** You must set the regions in the code properly, for many of the libraries. If you don't, you could get meaningless errors related to permissions/policies. The langchain_aws code is a good example with accessing a kb. I left out the region, pushed to EC2, and spent hours trying to figure out why the IAM role EC2 was using didn't have the proper policy permissions. In the end - I added the region to the code call and it fixed it.

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

## CodeBuild
CodeBuild is going to create our Docker image on AWS, and store it in ECR.

- Create an empty ECR repository. I don't recall what I did for this step.

Then:

- Create the config on codebuild through the AWS console.
- It will need GitHub access.
- Do this with a fine-grained token giving just the necessary permissions to pull from a single repo (read, pull)

CodeBuild needs a `buildspec.yml` file to pull everything together and build the Docker image. This file is in the github repo.

*TODO*: REPLACE ECR constant in buildspec with an ENV variable that gets set in CodeBuild/Build/Build Projects/**Your Project**/Project Details/Environment

Here's what's going on in the build (`buildspec.yml`)
The steps roughly are:

1. Set your ECR repository id in the ENV (or hard code in buildfile)
2. Install Git
3. Connect to ECR (permissions are going to be needed to be set here)
4. Clone the repo
5. Build the docker image
6. Push the image to ECR
7. Tag the image

### Build the Docker image in CodeBuild

From the CodeBuild console, build the image with *Start Build*. 

Check the logs for errors. If there are issues:

- Fix the code/yaml locally.
- Commit the code and push it to github
- Try the build again (it will pull latest code, or whatever version you tell it)

Hooray! Now you have a docker image. Which probably has problems and won't run, but at least you have the steps to rebuild the image

# Start EC2 instance

## Instance creation
This video in the 2nd half has a good overview. Note he is pulling a docker image from docker hub, while we are pulling it from ECR. So many of his steps aren't relevant. HOWEVER, I didn't document how to create the instance. One already exists from when I did it.

https://www.youtube.com/watch?v=DflWqmppOAg

--> I don't have the steps for creating a new instance, since the one I created is done.

- The Role used for the instance needs to have access to the knowledge base, otherwise the chat won't execute when it tries to load the kb.

## Steps

- Open the EC2 service

- Click the instance ID for aime

- A new window opens with the instance details. 

- Under Instance state (upper left) click the triangle and select Start instance

- Go back to the main screen and wait fo the the instance state to change to Running

- From the main screen (or from the detail screen) click the Connect button

- The Connect to instance screen appears. Click Connect.

- You should be at an EC2 terminal window.

You need to be in an EC2 terminal to do the following:

```sh
sudo yum update -y
```

Install docker

```sh
sudo yum install -y docker
```

Then with the running EC2 instance (or before running it), attach it to an IAM role with the `AmazonEC2ContainerRegistryFullAccess` policy

```sh
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ECR_repository_URI:image_version>
```
Start docker:

```sh
sudo systemctl start docker
```

Add the ec2 user to the docker group:

```sh
sudo usermod -a -G docker ec2-user
```

Close/reopen the session for new group to take effect

Restart docker:
```sh
sudo systemctl restart docker
```
Pull the image:
```sh
docker pull <ECR_repository_URI:image_version>
```
Run it in the background. To see errors quickly, remove the -d option.

```sh
docker run -d -p 8501:8501 <ECR_repository_URI:image_version>
```

## Streamlit access

Once the container is running, access the Streamlit app by visiting 
```sh
http://<ec2-public-ip>:8501
```

in your web browser, replacing 
`<ec2-public-ip>`
with the public IP address of your EC2 instance. 

**NOTE! its HTTP not HTTPS**

## Test the chat
It will likely generate some type of error

- Add additional permissions: This probably will happen throughout the process. In this case the EC2 Role needed access to Bedrock. Copy the browser error into Q and it will tell you what permissions to add and where

Check if it's running
```sh
docker ps
```
## Stop the container
If you do not stop the container, charges will continue to accrue on AWS!!!
```sh
docker stop <container_id>
```


# AWS Setup

Notes.
The docker container exposes port 8501. This is what Streamlit runs on. It's expecting traffic on 8501 from the EC2 instance. If all you use is EC2 (no LB), then you add :8501 to the browser request. We aren't using Apache/Nginx to listen on 80 and port forward to 8501. We're accomplishing that with the LB. The LB takes the requests on 443 (because we're not supporting unencrypted traffic on 80) and sends that to 8501 on EC2. Then EC2 takes the 8501 traffic and gives it to Streamlit on 8501. So we don't need any 443/80 configuration within EC2/docker.

--------
When setting up the traffic flow (browser -> app) it's easier to work backwards from the EC2 instance and see what loads/doesn't load in a browser. As each piece is added, check to make sure things work.

For example: First, get the instance running and trying loading the app from an unsecure browser connection to the ip/port: http://ec2port:8501

Does it load and work? Great. Now add the load balancer.

When the load balancer is set, try loading the LB DNS into a browser.

Does that work? Great. Now setup the hosted zone in Route53 and point the A record to the LB.

Configuring the LB and getting the ports forwarded properly to EC2, along with the health check ports, the target group ports, target, ssl cert, is a lot of steps. It's a lot of screens, and a lot of creating things. It's basically a rabbit hole where lots can go wrong. I found prompting Q to what settings I should do based on what I was trying to accomplish fixed a lot of the issues I ran into (after the fact). Here's a couple I wanted to save for the future.

Overall the steps should be:

EC2
Security Certificate
LB
- LB Target
- LB Target Group
- LB Security Group (not the default, you can add up to 5)
Route 53

Q: Explain what my target group settings should be. My load balancer should listen for https requests. It needs to send the request to the ec2 instance. The ec2 instance application is expecting traffic on port 8501.

Based on your requirements, here's how you should configure your target group and load balancer: [1]

1. Target Group Settings:

- Target type: Instance

- Protocol: HTTP (not HTTPS, as the load balancer will handle SSL termination)

- Port: 8501 (this is the port your application is listening on)

- VPC: Select the VPC where your EC2 instance is located

- Health check protocol: HTTP

- Health check port: 8501 [2]

- Health check path: / (or the appropriate path that returns a 200 OK)

- Healthy threshold: 2 (default, adjust if needed)

- Unhealthy threshold: 2 (default, adjust if needed)

- Timeout: 5 seconds (default, adjust if needed)

- Interval: 30 seconds (default, adjust if needed)

- Success codes: 200 (or the appropriate success code for your application)

2. Load Balancer Listener:

- Protocol: HTTPS [3]

- Port: 443 (standard HTTPS port)

- Default action: Forward to your target group

3. SSL/TLS Certificate:

- You'll need to attach a valid SSL/TLS certificate to your HTTPS listener

4. EC2 Instance Configuration:

- Ensure your application is listening on port 8501

- The security group should allow inbound traffic on port 8501 from the load balancer's security group [4]

5. Load Balancer Security Group:

- Inbound rule: Allow HTTPS (port 443) from anywhere (0.0.0.0/0)

- Outbound rule: Allow traffic to your EC2 instance on port 8501

This setup allows the load balancer to receive HTTPS traffic on port 443, terminate SSL, and then forward the decrypted HTTP traffic to your EC2 instance on port 8501. The EC2 instance doesn't need to handle HTTPS itself in this configuration.

Remember to register your EC2 instance with this target group and ensure it passes the health checks. If you're still experiencing issues, double-check these settings and review your application logs for any errors.

Q: how to set this outbound rule: Outbound rule: Allow traffic to your EC2 instance on port 8501.

To set the outbound rule allowing traffic from your load balancer to your EC2 instance on port 8501, follow these steps: [1]

1. Open the EC2 console in AWS.

2. In the navigation pane, click on "Security Groups".

3. Find and select the security group associated with your load balancer.

4. Click on the "Outbound rules" tab. [2]

5. Click "Edit outbound rules".

6. Click "Add rule".

7. Configure the new rule as follows:

- Type: Custom TCP

- Protocol: TCP

- Port range: 8501

- Destination: Select "Custom" and enter the security group ID of your EC2 instance (This is more secure than using the EC2's IP address or CIDR block)

- Description: (Optional) Add a description like "Allow traffic to EC2 on port 8501"

8. Click "Save rules".

This configuration allows the load balancer to send traffic only to your EC2 instance's security group on port 8501, which is more secure than opening it to all destinations.

Remember to also ensure that the inbound rules on your EC2 instance's security group allow traffic from the load balancer's security group on port 8501.

By using security group IDs for the source (in EC2's inbound rules) and destination (in load balancer's outbound rules), you create a more secure and flexible setup that doesn't rely on specific IP addresses.
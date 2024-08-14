# Use a smaller base image from AWS Public ECR
FROM public.ecr.aws/docker/library/python:3.12-slim-bullseye

# Install Git
RUN apt-get update && apt-get install -y git

# Set the working directory in the container
WORKDIR /app

# Clone the repository
RUN git clone https://github.com/scottalanturner/ai_me .

# Copy only the requirements file first to leverage Docker's layer caching
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Remove unnecessary files (e.g., cached files) to further reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Expose the port that Streamlit will run on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "main.py"]

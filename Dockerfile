# Use a smaller base image from AWS Public ECR
FROM public.ecr.aws/docker/library/python:3.12-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Remove unnecessary files (e.g., cached files) to further reduce image size
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Expose the port that Streamlit will run on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "main.py"]

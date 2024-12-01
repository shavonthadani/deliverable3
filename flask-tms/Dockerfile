# Use an official Python runtime as a base image
FROM python:3.9-slim

# Install git to clone the repository
RUN apt-get update && apt-get install -y git && apt-get clean

# Set the working directory inside the container
WORKDIR /app

# Clone your GitHub repository
RUN git clone https://github.com/shavonthadani/deliverable3.git .

# Install dependencies from the repository
RUN pip install --no-cache-dir -r /app/flask-tms/requirements.txt

# Set new working directory
WORKDIR /app/flask-tms

# Expose the application port
EXPOSE 5000

# Command to run the application
CMD ["python", "run.py"]


# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install Stockfish and other system dependencies
RUN apt-get update && apt-get install -y stockfish && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for Stockfish path
ENV STOCKFISH_PATH=/usr/games/stockfish

# Run the app. Uvicorn is a production-ready server.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
# Use an official python runtime
#FROM ubuntu:latest
#RUN apt-get update -y
#RUN apt-get install -y python-pip python-dev build-essential
FROM python:latest

# Copy the current directory contents into the container at /app
COPY . /app

# Change working directory
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Run app.py when the container launches
CMD ["gunicorn","-b", " :15003",  "grid_server:server"]
#CMD ["python","grid_server.py"]



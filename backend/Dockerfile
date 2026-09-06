FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install the dependencies first, so this (slow) layer is cached and only re-built when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the serialized model into the container's working directory
COPY . .

# Define the command to start the application using Gunicorn with 4 worker processes
# - `-w 4`: Uses 4 worker processes for handling requests
# - `-b 0.0.0.0:7860`: Binds the server to port 7860 on all network interfaces
# - `app:superkart_api`: Runs the Flask app (assuming `app.py` contains the Flask instance named `superkart_api`)
# - `--preload`: loads the model once in the master process and forks the workers (less memory, faster start)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7860", "--preload", "app:superkart_api"]

# Use a minimal base image with Python 3.9 installed
FROM python:3.9-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Install Python dependencies first so the layer is cached when only app.py changes
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code into the container's /app directory
COPY . .

# Define the command to run the Streamlit app on port 8501 and make it accessible externally
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableXsrfProtection=false"]

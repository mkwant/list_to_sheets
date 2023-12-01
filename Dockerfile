FROM python:3.12

# Set the Python path
ENV PYTHONPATH /app

# Upgrade pip
RUN pip install --upgrade pip

# Set the working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the source code
COPY src/ src/

# Set the entrypoint and default command
ENTRYPOINT ["python", "src/to_sheets.py"]

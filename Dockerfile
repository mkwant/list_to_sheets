FROM python:3.12

# Set the Python path
ENV PYTHONPATH /app

# Set timezone
ENV TZ Europe/Amsterdam

# Upgrade pip
RUN pip install --upgrade pip

# Set the working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the source code
COPY src/ src/

WORKDIR /app/src

# Set the entrypoint and default command
ENTRYPOINT ["python", "to_sheets.py"]
#ENTRYPOINT ["bash"]
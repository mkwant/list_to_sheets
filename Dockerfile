FROM python:3.12-slim

# Set the Python path
ENV PYTHONPATH /app

# Set terminal to support colour output
ENV TERM xterm-256color

# Set timezone
ENV TZ Europe/Amsterdam

# Ignore pip root error warnings
ENV PIP_ROOT_USER_ACTION=ignore

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
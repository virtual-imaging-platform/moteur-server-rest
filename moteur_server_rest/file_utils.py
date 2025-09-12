import logging
import os

logger = logging.getLogger(__name__)

def create_directory(path):
    """Create a directory at the specified path."""
    os.makedirs(path, exist_ok=True)
    logger.info(f"Directory {path} created.")

def write_file(file_path, content):
    """Write content to a file."""
    with open(file_path, "wb") as file:
        file.write(content)
    logger.info(f"File {file_path} successfully written.")

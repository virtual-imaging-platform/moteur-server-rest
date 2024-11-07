import os

def create_directory(path):
    """Create a directory at the specified path."""
    os.makedirs(path, exist_ok=True)
    print(f"Directory {path} created.")

def write_file(file_path, content):
    """Write content to a file."""
    with open(file_path, "wb") as file:
        file.write(content)
    print(f"File {file_path} successfully written.")

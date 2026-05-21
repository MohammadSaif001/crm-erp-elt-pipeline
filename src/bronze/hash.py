import hashlib
def generate_file_hash(file_path: str):
    sha256 = hashlib.sha256()
    with open (file_path,"rb") as HashFile:
        for chunk in iter(lambda: HashFile.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


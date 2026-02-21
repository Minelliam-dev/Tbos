import os

def _resolve_path(relative_path: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

def create(path, extension):
    path2 = _resolve_path(path) + extension
    
    
    with open(path2, "w") as f:
        f.write("Hello, world!")
 
def write(file_path, content):
    path2 = _resolve_path(file_path)
    
    
    with open(path2, "w") as f:
        f.write(content)
 
def read(file_path, amount_of_chars):
    path2 = _resolve_path(file_path)
    
    
    with open(path2, "r") as f:
        content = f.read()
    return content

 
def createFolder(name):
    try:
        path2 = _resolve_path(name)
        
        os.mkdir(path2)
    except Exception as e:
        print(e)
 
def getFolderExists(path):
    try:
        path2 = _resolve_path(path)
        
        if os.path.exists(path2):
            return True
        else:
            return False
    except Exception as e:
        print(e)
 
def getFileExists(path):
    try:
        path2 = _resolve_path(path)
        
        if os.path.exists(path2):
            return True
        else:
            return False
    except:
        return

 
def readLine(file_path, line):
    path2 = _resolve_path(file_path)
    
    
    with open(path2, "r") as f:
        content = f.read()
    return content

def delete_file(file_path):
    if getFileExists(file_path):
        file_path.unlink()
    else:
        print("Cannot delete file. File not found")
        return
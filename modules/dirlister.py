import os

def run(**args):

    print "[*] in dirlister modules."
    files = os.listdir (".")
    return str(files)

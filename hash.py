from Crypto.Hash import SHA512 #pip3 install pycryptodome
import sys
import os
from dotenv import load_dotenv
load_dotenv()
def hash(input_str, salt=None):
    h = SHA512.new(truncate="256")
    if salt is None:
        salt = os.environ.get('VACUUMSALT')
    b = bytes(input_str + salt, 'utf-8')
    h.update(b)
    return h.hexdigest()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        input_str = input("Enter the value you wish to hash: ")
        out = hash(input_str)
        print(out)
    else:
        input_str = sys.argv[1]
        salt = sys.argv[2]
        out = hash(input_str, salt)
        print(out)



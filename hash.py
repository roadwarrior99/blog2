from Crypto.Hash import SHA512 #pip3 install pycryptodome
import sys
import os
#from dotenv import load_dotenv
#load_dotenv()
def hash(input_str):
    h = SHA512.new(truncate="256")
    b = bytes(input_str + os.environ.get('VACUUMSALT'), 'utf-8')
    h.update(b)
    return h.hexdigest()

if __name__ == '__main__':
        input_str = input("Enter the value you wish to hash: ")
        out = hash(input_str)
        print(out)


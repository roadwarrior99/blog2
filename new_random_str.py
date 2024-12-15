import secrets
import string
def so_random():
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(128))
    return password

if __name__ == '__main__':
    password = so_random()
    print(password)
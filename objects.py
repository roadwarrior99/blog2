import os

import hash
import datetime
class User:
    __authed = False
    __active = False
    __anonymous = False
    __userID = ""
    __apikey = ""
    __apikeyexpiration = datetime.datetime.now() + datetime.timedelta(hours=1)
    def is_authenticated(self):
        return self.__authed
    def is_active(self):
        return self.__active
    def is_anonymous(self):
        return self.__anonymous
    def get_id(self):
        return self.__userID
    def get_apikey_expiration(self):
        return self.__apikeyexpiration
    def get_apikey(self):
        return self.__apikey
    def __init__(self, userID):
        #VACUUMAPIKEYSALT
        self.__userID = userID
        self.__authed = True
        self.__active = True
        self.__anonymous = False
        apikeyGen = (os.environ.get("VACUUMAPIKEYSALT") + userID
            + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")) \
            + os.environ.get("VACUUMAPIKEYSALT")
        self.__apikey = hash.hash(apikeyGen)
        self.__apikeyexpiration = datetime.datetime.now() + datetime.timedelta(hours=1)

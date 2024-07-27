import os
import sqlite3
import hash
import datetime
import html
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

class blog_post:
    id = 0
    old_id = ""
    date = datetime.datetime.now()
    rss = ""
    seo = ""
    body = ""
    dbfile = ""


    @classmethod
    def load_from_array(self, values_array:[]):
        self.id = values_array[0]
        self.old_id = values_array[1]
        self.date = values_array[2]
        self.rss = values_array[3]
        self.seo = values_array[4]
        self.body = values_array[5]
        self.subject = values_array[6]

    @classmethod
    def load_from_values(self, id:int, oldid, date, subject, rss, seo, body):
        self.id = id
        self.old_id = oldid
        self.date = date
        self.subject = subject
        self.rss = rss
        self.seo = seo
        self.body = html.unescape(body)

    def save(self):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            cur = conn.cursor()
            if self.id > 0:
                sql = """insert into post(subject,date,rss_description,seo_keywords,body)
                    values(?,?,?,?,?);"""

                post_date_obj = datetime.strptime(self.date, "%m/%d/%Y")
                cur.execute(sql, [self.subject, int(post_date_obj.timestamp())
                    ,self.rss, self.seo
                    ,self.body])
            else:
                sql = "update post set subject=?, date=?, rss_description=?, seo_keywords=?, body=? where id=?"
                cur.execute(sql,[self.subject, self.date, self.rss, self.seo, self.body, self.id])
            conn.commit()
            conn.close()
        else:
            print("DB file not set")

    def load(self, id):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            sql = "SELECT * FROM post WHERE id = ?"
            cur = conn.cursor()
            #post_id = request.args.get('number', type=int)
            cur.execute(sql, [id])
            results = cur.fetchall()
            post = {
                'id': results[0][0],
                'subject': results[0][1],
                'date': results[0][2],
                'rss_description': results[0][3],
                'seo_keywords': results[0][4],
                'body': results[0][5]
            }
            cur.close()
        else:
            print("DB file not set")
    def load_oldid(self, old_id):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            sql = "SELECT * FROM post WHERE old_id = ?"
            cur = conn.cursor()
            #post_id = request.args.get('number', type=int)
            cur.execute(sql, [old_id])
            results = cur.fetchall()
            post = {
                'id': results[0][0],
                'subject': results[0][1],
                'date': results[0][2],
                'rss_description': results[0][3],
                'seo_keywords': results[0][4],
                'body': results[0][5]
            }
            cur.close()
        else:
            print("DB file not set")
    def serialize(self):
        return {"id": self.id, "subject": self.subject, "date": self.date
            , "rss": self.rss, "seo": self.seo, "body": self.body}


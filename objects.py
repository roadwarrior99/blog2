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
    subject = ""

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
            if self.id == 0:
                sql = """insert into post(subject,date,rss_description,seo_keywords,body)
                    values(?,?,?,?,?);"""


                cur.execute(sql, [self.subject, self.date
                    ,self.rss, self.seo
                    ,self.body])
                cur.execute("SELECT max(id) FROM post;")
                last_id_result = cur.fetchone()
                if last_id_result:
                    self.id = last_id_result[0]
            else:
                sql = "update post set subject=?, date=?, rss_description=?, seo_keywords=?, body=? where id=?"
                cur.execute(sql,[self.subject, self.date, self.rss, self.seo, self.body, self.id])
            conn.commit()

            conn.close()
            self.save_seo_terms(self.seo, self.id)
            return True
        else:
            print("DB file not set")
            return False
    def save_seo_terms(self, seo_raw, post_id):
        if os.path.exists(self.dbfile):
            tag_ids = dict()
            conn = sqlite3.connect(self.dbfile)
            cur = conn.cursor()
            tagsql = """
            select id, name
            from tags
            where enabled = 1
            """
            cur.execute(tagsql)
            tag_result = cur.fetchall()
            for result in tag_result:
                tag_ids[result[1]] = result[0]  # name, id

            seo_terms = seo_raw.split(",")
            tag_ids_in_use = []
            for term in seo_terms:
                new_tag = tag_obj()
                new_tag.dbfile = self.dbfile
                if term.lower().strip() not in tag_ids:
                    # Add term
                    new_tag.name = term.lower().strip()
                    new_tag.save()
                    getidsql = "select max(id) from tags"
                    cur.execute(getidsql)
                    idresult = cur.fetchall()
                    new_tag.id = idresult[0][0]
                    tag_ids_in_use.append(new_tag.id)
                else:
                    new_tag = tag_obj()
                    new_tag.dbfile = self.dbfile
                    new_tag.load_by_name(term.lower().strip())
                    tag_ids_in_use.append(new_tag.id)
                # Does Post Tag exist?
                post_tag_sql = """
                select id 
                from post_tags pt 
                where pt.post_id=? and pt.tag_id=?
                """
                cur.execute(post_tag_sql, (post_id, new_tag.id))
                existing_post_tag_records = cur.fetchall()
                if not existing_post_tag_records:
                    new_post_tag = post_tags_obj()
                    new_post_tag.dbfile = self.dbfile
                    new_post_tag.post_id = post_id
                    new_post_tag.tag_id = new_tag.id
                    new_post_tag.save()
            #look for any post_tags to clean up.
            post_tags_to_remove_Sql = """
            delete from post_tags
            where post_id=? and tag_id not in ({0})
            """.format(','.join(map(str, tag_ids_in_use)))
            cur.execute(post_tags_to_remove_Sql, [post_id])
            conn.commit()
            conn.close()


    def remove(self, id):
        if os.path.exists(self.dbfile):
            if id:
                conn = sqlite3.connect(self.dbfile)
                cur = conn.cursor()
                sql = "delete from post_tags where post_id=?"
                cur.execute(sql, [id])
                sql = "delete from post where id=?"
                cur.execute(sql, [id])
                conn.commit()
                conn.close()
            else:
                print("ID not set.")
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
            cur.close()
            conn.close()
            self.id = results[0][0]
            self.subject = results[0][1]
            self.date = results[0][2]
            self.rss = results[0][3]
            self.seo = results[0][4]
            self.body = results[0][5]
            return True
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
            cur.close()
            conn.close()
            self.id = results[0][0]
            self.subject = results[0][1]
            self.date = results[0][2]
            self.rss = results[0][3]
            self.seo = results[0][4]
            self.body = results[0][5]
        else:
            print("DB file not set")
    def serialize(self):
        return {"id": self.id, "subject": self.subject, "date": self.date
            , "rss": self.rss, "seo": self.seo, "body": self.body}


class tag_obj:
    id = 0
    name = ""
    enabled = 1
    dbfile = ""

    def save(self):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            cur = conn.cursor()
            if self.id == 0:
                sql = """insert into tags(name)
                          values(?);"""

                cur.execute(sql, [self.name.lower().strip()])
            else:
                sql = "update tags set name=?, enabled=? where id=?"
                cur.execute(sql, [self.name, self.enabled, self.id])
            conn.commit()
            conn.close()
            return True
        else:
            print("DB file not set")
            return False

    def load(self, tag_id):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            sql = "SELECT * FROM tag WHERE id = ?"
            cur = conn.cursor()
            #post_id = request.args.get('number', type=int)
            cur.execute(sql, [tag_id])
            results = cur.fetchall()
            cur.close()
            conn.close()
            self.id = results[0][0]
            self.name = results[0][1]
            self.enabled = results[0][2]
            return True
        else:
            print("DB file not set")
    def load_by_name(self, tag_name):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            sql = "SELECT * FROM tags WHERE name = ?"
            cur = conn.cursor()
            #post_id = request.args.get('number', type=int)
            cur.execute(sql, [tag_name])
            results = cur.fetchall()
            cur.close()
            conn.close()
            self.id = results[0][0]
            self.name = results[0][1]
            self.enabled = results[0][2]
            return True
        else:
            print("DB file not set")
    def remove(self, tag_id):
        if os.path.exists(self.dbfile):
            if id:
                conn = sqlite3.connect(self.dbfile)
                cur = conn.cursor()
                sql = "delete from post_tags where tag_id=?"
                cur.execute(sql, [tag_id])
                sql = "delete from tag where id=?"
                cur.execute(sql, [tag_id])
                conn.commit()
                conn.close()
            else:
                print("ID not set.")
        else:
            print("DB file not set")

class post_tags_obj:
    post_tag_id = 0
    post_id = 0
    tag_id = 0
    virtual_tag_name = ""
    virtual_post_name = ""
    dbfile=""

    def load(self, post_tag_id):
        if os.path.exists(self.dbfile):
            if post_tag_id:
                conn = sqlite3.connect(self.dbfile)
                cur = conn.cursor()
                sql = """
                select pt.id,pt.post_id,pt.tag_id, t.name, p.subject
                from post_tags pt
                inner join post p on p.id=pt.post_id
                inner join tags t on t.id=pt.tag_id
                where pt.id=?
                """
                cur.execute(sql, [post_tag_id])
                results = cur.fetchall()
                conn.commit()
                conn.close()
                self.post_tag_id = post_tag_id
                self.post_id = results[0][1]
                self.tag_id = results[0][2]
                self.virtual_tag_name = results[0][3]
                self.virtual_post_name = results[0][4]
                return True
            else:
                print("ID not set.")
        else:
            print("DB file not set")
    def save(self):
        if os.path.exists(self.dbfile):
            conn = sqlite3.connect(self.dbfile)
            cur = conn.cursor()
            if self.post_tag_id == 0:
                sql = """insert into post_tags(post_id,tag_id)
                    values(?,?);"""
                cur.execute(sql, [self.post_id, self.tag_id])
            else:
                sql = "update post_tags set post_id=?, tag_id=? where id=?"
                cur.execute(sql,[self.post_id, self.tag_id, self.post_tag_id])
            conn.commit()
            conn.close()
            return True
        else:
            print("DB file not set")
            return False
    def remove(self, post_tag_id):
        if os.path.exists(self.dbfile):
            if id:
                conn = sqlite3.connect(self.dbfile)
                cur = conn.cursor()
                sql = "delete from post_tags where id=?"
                cur.execute(sql, [post_tag_id])
                conn.commit()
                conn.close()
            else:
                print("ID not set.")
        else:
            print("DB file not set")



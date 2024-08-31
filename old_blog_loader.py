import os.path
import sys

import yaml
import sqlite3

def read_old_blog(main_yaml, destination_db):
    if os.path.exists(main_yaml) and os.path.exists(destination_db):
        with open(main_yaml, 'r') as ymlf:
            ymlobj = yaml.safe_load_all(ymlf)
            conn = sqlite3.connect(destination_db)
            cur = conn.cursor()
            for blog_obj in reversed(ymlobj):
                sql = """insert into post(subject,date,rss_description,seo_keywords,
                    body, old_id)
                    values(?,?,?,?,?,?);"""
                path =  os.path.dirname(os.path.abspath(main_yaml))
                with open(os.path.join(path, blog_obj['bodyFile']), 'r') as bf:
                    body = bf.read()
                cur.execute(sql, [blog_obj['subject'], blog_obj['date'], blog_obj['description'], blog_obj['keywords'],
                            body, blog_obj['id']])
            conn.commit()

def copy_blog_posts(main_yaml, destination_db, old_post_id):
    if os.path.exists(main_yaml) and os.path.exists(destination_db):
        with open(main_yaml, 'r') as ymlf:
            ymlobj = yaml.safe_load_all(ymlf)
            conn = sqlite3.connect(destination_db)
            cur = conn.cursor()
            for blog_obj in ymlobj:
                if blog_obj["id"] == old_post_id:
                    path =  os.path.dirname(os.path.abspath(main_yaml))
                    with open(os.path.join(path, blog_obj['bodyFile']), 'r') as bf:
                        body = bf.read()
                    sql = """insert into post(subject,date,rss_description,seo_keywords,
                    body, old_id)
                    values(?,?,?,?,?,?);"""
                    cur.execute(sql, [blog_obj['subject'], blog_obj['date'], blog_obj['description'], blog_obj['keywords'],
                                body, blog_obj['id']])
                    conn.commit()
    else:
        if not os.path.exists(main_yaml):
            print("The specified file does not exist:" + main_yaml)
        if not os.path.exists(destination_db):
            print("The specified file does not exist:" + destination_db)


if __name__ == '__main__':
    if len(sys.argv) == 3:
        read_old_blog(sys.argv[1], sys.argv[2])
    if len(sys.argv) == 4:
        print("copying blog post " + sys.argv[3])
        copy_blog_posts(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("help:")
        print("main yaml file, sqlite3 destination db file")

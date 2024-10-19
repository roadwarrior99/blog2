import sqlite3
import os
import sys
import objects

def convert_seo_to_tag(dbfile):
    if os.path.exists(dbfile):
        tag_ids = dict()
        conn = sqlite3.connect(dbfile)
        cur = conn.cursor()
        tagsql = """
        select id, name
        from tags
        where enabled = 1
        """
        cur.execute(tagsql)
        tag_result = cur.fetchall()
        for result in tag_result:
            tag_ids[result[1]] = result[0] #name, id

        sql = """
        select id, seo_keywords
        from post
        order by id asc
        """
        cur.execute(sql)
        post_result = cur.fetchall()
        for result in post_result:
            post_id = result[0]
            seo_raw = result[1]
            seo_terms = seo_raw.split(",")
            for term in seo_terms:
                new_tag = objects.tag_obj()
                new_tag.dbfile = dbfile
                if term not in tag_ids:
                    #Add term
                    new_tag.name = term
                    new_tag.save()
                    getidsql = "select max(id) from tags"
                    cur.execute(getidsql)
                    idresult = cur.fetchall()
                    new_tag.id = idresult[0][0]
                else:
                    new_tag = objects.tag_obj()
                    new_tag.dbfile = dbfile
                    new_tag.load_by_name(term)
                # Does Post Tag exist?
                post_tag_sql = """
                select id 
                from post_tags pt 
                where pt.post_id=? and pt.tag_id=?
                """
                cur.execute(post_tag_sql, (post_id,new_tag.id))
                existing_post_tag_records = cur.fetchall()
                if not existing_post_tag_records:
                    new_post_tag = objects.post_tags_obj()
                    new_post_tag.dbfile = dbfile
                    new_post_tag.post_id = post_id
                    new_post_tag.tag_id = new_tag.id
                    new_post_tag.save()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        convert_seo_to_tag("data/vacuumflask.db")
    else:
        convert_seo_to_tag(sys.argv[1])
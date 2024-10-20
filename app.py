from crypt import methods

import flask
from flask import Flask, request, Blueprint, render_template, make_response
import sqlite3
import yaml
from flask_login import login_required, current_user
import json
from datetime import datetime
import hash
import logging
import datetime
import redis
from flask_session import Session
import os
import flask_login
import objects
from flask_ipban import IpBan
from s3_management import list_files
from s3_management import mv_file
from s3_management import s3_upload_file
from s3_management import s3_remove_file
from dotenv import load_dotenv
import image_processing

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("VACUUMSESSIONKEY")
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url(os.environ.get('REDIS_SERVER'))
auth = Blueprint('auth', __name__)
login_manager = flask_login.LoginManager(app)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
db_path = "data/vacuumflask.db"
ip_ban = IpBan(ban_seconds=604800) # 7 day ban for f'ing around.
good_list = "data/goodlist.txt"
#s3_content = list_files()
logger = logging.getLogger(__name__)
timeobj = datetime.datetime.now()
server_session = Session(app)

@login_manager.user_loader
def load_user(user_id):
    user = objects.User(user_id)
    return user

@app.route('/login', methods=['GET'])
def login_get():
    return flask.render_template('login.html')
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    if username and password:
        pwdHashed = hash.hash(password)
        #logger.warning("User: {0} with password:'{1}'".format(username, pwdHashed))
        #logger.warning("root user: {0} with hash:{1}".format(os.environ.get('VACUUMROOTUSER'), os.environ.get('VACUUMROOTHASH')))
        if pwdHashed == os.environ.get('VACUUMROOTHASH')  \
            and username == os.environ.get('VACUUMROOTUSER'):
            my_user = objects.User(username)
            flask_login.login_user(my_user)
            return render_template("loginmenu.html")
        else:
            logger.warning("User or Password hash didn't match")
            ip_ban.add()
            logger.warning("Failed login with headers: {0}".format(request.headers))
            return render_template("authissue.html", code=401)
    else:
        logger.warning ("User name and password not sent")
        return render_template("authissue.html", code=402)

@app.route('/brat/<int:number>')
def get_brat_no(number):
    return f'Brat number {number} reporting in for duity'

@app.route('/edit/<int:number>', methods=['GET'])
@flask_login.login_required
def edit_blog_posts(number):
    blog = objects.blog_post()
    blog.dbfile = db_path
    blog.load(number)
    return render_template("edit.html", blog=blog.serialize())

@app.route('/edit/<int:number>', methods=['POST'])
@flask_login.login_required
def edit_blog_posts_save(number):
    return create_blogpost(number)

@app.route('/post/<int:number>')
def blogpost(number):
    post = objects.blog_post()
    post.dbfile = db_path
    post.load(number)
    return render_template("post.html",blog=post)

@app.route("/menu")
@flask_login.login_required
def show_menu():
    return render_template("loginmenu.html")

@app.route("/remove/<int:postid>",methods=['GET'])
@flask_login.login_required
def remove_blog_post(postid):
    post = objects.blog_post()
    post.dbfile = db_path
    post.remove(postid)
    return render_template("loginmenu.html")

@app.route('/post/<old_id>')
def oldblogpost(old_id):
    post = objects.blog_post()
    post.dbfile = db_path
    post.load_oldid(old_id=old_id)
    return render_template("post.html", blog=post)

@app.route('/post', methods=['GET'])
def blogposts():
    conn = sqlite3.connect(db_path)
    sql = "SELECT * FROM post order by id desc"
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    posts = []
    for result in results:
        post = {
            'id': result[0],
            'subject': result[1],
            'date': result[2],
            'rss_description': result[3],
            'seo_keywords': result[4],
            'body': result[5]
        }
        posts.append(post)
    cur.close()
    conn.close()
    return render_template("postlist.html", posts=posts)


@app.route('/post', methods=['POST'])
@flask_login.login_required
def create_blogpost(number=0):
    required_parms = ['subject', 'date', 'rss_description','seo_keywords', 'body' ]
    data = dict()
    for parm in required_parms:
        data[parm] = request.form.get(parm)
    post = objects.blog_post()
    id = number
    old_id = ""
    if request.form.get('id'):
        id = request.form.get('id')
    if request.form.get('old_id'):
        old_id = request.form.get('old_id')
    post.load_from_values(id=id, oldid=old_id, date=data['date'], subject=data['subject'],
                          rss=data['rss_description'], seo=data['seo_keywords'], body=data['body'])
    post.dbfile = db_path
    post.save()
    #Make this smarter depending on how we are posting.
    return render_template("save.html")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
###
### This is for on server file uploads and won't freaking work from a docker container unless the
### destionation path is a write directory from outside of the container
###
@app.route('/upload', methods=['POST'])
@flask_login.login_required
def upload_file():
    if 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        else:
            return (json.dumps({'success': False, 'message': 'file ext is not on approved list.'})
                    , 200, {'ContentType': 'application/json'})
    else:
        return json.dumps({'success': False, 'message': 'file was not provided'}), 200, {'ContentType': 'application/json'}

@app.route('/public_content', methods=['POST'])
@flask_login.login_required
def public_content_file_upload():
    if 'file' in request.files:
        file = request.files['file']
        #if file and allowed_file(file.filename):
        new_img = []
        if request.form.get('Mobile'):
            logger.info("Mobile image processing.")
            #this doesn't work
            #the file is in a stream object and the image thing is expecting something else
            new_img.append(image_processing.mobile_size_image(file.stream, file.filename))
        if request.form.get("Discord"):
            logger.info("Discord image processing.")
            new_img.append(image_processing.discord_size_image(file.stream, file.filename))
        if request.form.get("Metadata"):
            logger.info("Metadata removal image processing.")
            new_img.append(image_processing.remove_metadata_image(file.stream, file.filename))
        if request.form.get("ReMuxMovToMP4"):
            new_img.append(image_processing.convert_mov_to_mp4(file.stream, file.filename))
        if len(new_img) > 0:
            for img_file,filename in new_img:
                if img_file:
                    s3_upload_file(img_file, filename)
                else:
                    print("No file to save.")
        else:
            s3_upload_file(file,file.filename)
        logger.info("S3 file uploaded: {0}".format(file.filename))
        return render_template("save.html")
        #else:
        #    return render_template("file_error.html")

@app.route('/public_content', methods=['GET'])
@flask_login.login_required
def public_content():
    #if s3_content and len(s3_content) == 0:
    s3_content = list_files()
    return render_template("public_content.html", contents=s3_content)

@app.route('/public_content/gallery', methods=['GET'])
@flask_login.login_required
def public_content_gallery():
    s3_content = list_files()
    notvideofiles = dict()
    for key,obj in s3_content.items():
        file_typ = key.split('.')[-1]
        if file_typ != "mp4" and file_typ != "mov":
            notvideofiles[key] = True
        else:
            notvideofiles[key] = False

    return render_template("public_gallery.html", contents=s3_content, filetypes=notvideofiles)

@app.route("/public_content/content/<string:Key>", methods=['GET'])
@flask_login.login_required
def public_content_content(Key):
    s3_content = list_files()
    if Key in s3_content.keys():
        return render_template("public_content_item.html", item=s3_content[Key])
    else:
        return render_template("public_content.html", contents=s3_content, filenotfound=True)

@app.route('/public_content/content/move/<string:Key>', methods=['POST'])
@flask_login.login_required
def public_content_move(Key):
    #Need to know the old file name and the new file name.
    old_file_name = request.form.get("old_file")
    new_file_name = request.form.get("new_file")
    mv_file(old_file_name, new_file_name)
    logger.info("Renamed S3 File from: {0} to {1}".format(old_file_name, new_file_name))
    s3_content = list_files()
    return render_template("public_content_item.html", item=s3_content[new_file_name])

@app.route('/public_content/content/remove/<string:Key>', methods=["GET"])
@flask_login.login_required
def public_content_remove(Key):
    s3_content = list_files()
    if Key in s3_content:
        s3_remove_file(Key)
        logger.info("Removed from S3: {0}".format(Key))
        s3_content = list_files()
        return render_template("save.html")
    else:
        return render_template("file_error.html")

@app.route('/')
def index():
    conn = sqlite3.connect(db_path)
    sql = """select id, old_id, date,post.rss_description, seo_keywords, body, subject
            from post 
            order by id desc;"""
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    conn.close()
    posts = []
    bottom_posts = []
    topCount = 0
    for post in results:
        topCount = topCount + 1
        blog = objects.blog_post()
        blog.load_from_array(post)
        if topCount < 8:
            posts.append(blog.serialize())
        else:
            bottom_posts.append(blog.serialize())
    resp = get_tags()
    tag_render = json.loads(resp[0])
    tags = tag_render["tags"]
    max_font_size = tag_render["max_font_size"]
    min_font_size = tag_render["min_font_size"]
    max_count = tag_render["max_count"]
    min_count = tag_render["min_count"]
    return render_template('index.html', posts=posts, debug=app.debug, bottom_posts=bottom_posts,
                           tags=tags, max_font_size=max_font_size, min_font_size=min_font_size, min_count=min_count,
                           max_count=max_count)

@app.route('/tag/<string:name>', methods=['GET'])
def get_tag(name):
    conn = sqlite3.connect(db_path)
    sql = """select p.id, p.old_id, p.date,p.rss_description, p.seo_keywords, p.body, p.subject
                from post p
                inner join post_tags pt on pt.post_id=p.id
                inner join tags t on t.id=pt.tag_id
                where t.name like ? and t.enabled=1
                order by p.id desc;"""
    cur = conn.cursor()
    cur.execute(sql, [name])
    results = cur.fetchall()
    conn.close()
    posts = []
    bottom_posts = []
    topCount = 0
    for post in results:
        topCount = topCount + 1
        blog = objects.blog_post()
        blog.load_from_array(post)
        posts.append(blog.serialize())

    resp = get_tags()
    tag_render = json.loads(resp[0])
    tags = tag_render["tags"]
    max_font_size = tag_render["max_font_size"]
    min_font_size = tag_render["min_font_size"]
    max_count = tag_render["max_count"]
    min_count = tag_render["min_count"]
    return render_template('tag.html', posts=posts, debug=app.debug, bottom_posts=bottom_posts,
                           tags=tags, max_font_size=max_font_size, min_font_size=min_font_size, min_count=min_count,
                           max_count=max_count)
@app.route("/api/tags", methods=['GET'])
def get_tags():
    conn = sqlite3.connect(db_path)
    sql = """
    select t.name, count(pt.id)
    from tags t
    left join post_tags pt on pt.tag_id=t.id
    group by t.name
    having t.enabled=1
    """
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    tags = dict()
    for tag_obj in results:
        tags[tag_obj[0]] = tag_obj[1]
    max_font_size = 50
    min_font_size = 10
    max_count = max(tags.values())
    min_count = min(tags.values())
    tags_obj = {"tags": tags, "max_font_size": max_font_size, "min_count": min_count, "min_font_size": min_font_size,
                "max_count": max_count}

    return json.dumps(tags_obj), 200, {'ContentType': 'application/json'}
@app.route('/new', methods=['GET'])
@flask_login.login_required
def get_new_post():
    return render_template('new.html')

def read_and_apply_good_list(goodlist):
    if os.path.exists(good_list):
        with open(good_list, 'r') as f:
            for line in f:
                ip_ban.ip_whitelist_add(line)

if __name__ == '__main__':
    logFileName = "data/blog2_" + timeobj.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
    logging.basicConfig(filename=logFileName, level=logging.INFO)
    login_manager.init_app(app)
    ip_ban.init_app(app)
    read_and_apply_good_list(good_list)
    logger.info("Starting")

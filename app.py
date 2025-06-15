from crypt import methods

import flask
import flask_session
from flask import Flask, request, Blueprint, render_template, make_response,redirect,session
#from flask import session as login_session
import sqlite3
import yaml
from flask_login import login_required, current_user
import pyotp
import json
from datetime import datetime

from werkzeug.utils import secure_filename

import hash
import logging
import datetime
import redis
#from flask_session import Session
import os
import flask_login
import objects
from flask_ipban import IpBan
from s3_management import list_files
from s3_management import mv_file
from s3_management import s3_upload_file
import boto3
from s3_management import s3_remove_file
from dotenv import load_dotenv
import image_processing
from watchtower import CloudWatchLogHandler
import platform
import datetime

#okta related
import hashlib
import base64
import requests
import secrets


load_dotenv()
secrets_dict=dict()

app = Flask(__name__)
timeobj = datetime.datetime.now()
# Configure the Flask logger
logger = logging.getLogger(__name__)
cloud_watch_stream_name = "vacuum_flask_log_{0}_{1}".format(platform.node(),timeobj.strftime("%Y%m%d%H%M%S"))
if os.environ.get("AWS_PROFILE_NAME"):
    boto3.setup_default_session(profile_name=os.environ.get("AWS_PROFILE_NAME"), region_name=os.environ.get("AWS_REGION_NAME"))
    logger.info("AWS_PROFILE set to {0}".format(os.environ.get("AWS_PROFILE_NAME")))
    cloudwatch_handler = CloudWatchLogHandler(
        log_group_name='vacuum_flask',  # Replace with your desired log group name
        stream_name=cloud_watch_stream_name,
        boto3_profile_name=os.environ.get("AWS_PROFILE_NAME"),
    )
else:
    cloudwatch_handler = CloudWatchLogHandler(
        log_group_name='vacuum_flask',  # Replace with your desired log group name
        stream_name=cloud_watch_stream_name,  # Replace with a stream name
    )
app.logger.addHandler(cloudwatch_handler)
app.logger.setLevel(logging.INFO)

secmgrclient = boto3.client('secretsmanager', region_name=os.environ.get("AWS_REGION"))
secResponse = secmgrclient.get_secret_value(SecretId=os.environ.get("AWS_SECRET_ID"))
logger.info("AWS Secrets manager response: {0}".format(secResponse["ResponseMetadata"]["HTTPStatusCode"]))
if secResponse['SecretString']:
    secrets_dict = json.loads(secResponse['SecretString'])
    logger.info("AWS Secrets manager secrets have been loaded.")

ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'mov', 'webm', 'mp4', 'zip']

if os.environ.get("VACUUMSESSIONKEY"):
    app.secret_key = os.environ.get("VACUUMSESSIONKEY")
else:
    app.secret_key = secrets_dict['VACUUMSESSIONKEY']

sec_keys = ["OTS_SECRET", "VACUUMROOTUSER", "VACUUMROOTHASH", "VACUUMSALT", "VACUUMAPIKEYSALT"]
for key in sec_keys:
    if os.environ.get(key):
        secrets_dict[key] = os.environ.get(key)
        logger.info(f"Local environment variable {key} found, overriding secrets manager value.")

internal_bucket = os.environ.get("INTERNAL_BUCKET_NAME")
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB in bytes
app.config['SESSION_REDIS'] = redis.from_url(os.environ.get('REDIS_SERVER'))
auth = Blueprint('auth', __name__)
login_manager = flask_login.LoginManager(app)
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
db_path = "data/vacuumflask.db"
ip_ban = IpBan(ban_seconds=604800) # 7 day ban for f'ing around.
good_list = "data/goodlist.txt"
#s3_content = list_files()

#server_session = session(app)




@login_manager.user_loader
def load_user(user_id):
    user = objects.User(user_id, secrets_dict['VACUUMAPIKEYSALT'], secrets_dict['VACUUMSALT'])
    return user

@app.route('/login', methods=['GET'])
def login_get():
    return flask.render_template('login.html')
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')




    otpin = request.form.get('otp')
    logger.info("User:{0} tries to log in.".format(username))
    if username and password and otpin:
        pwdHashed = hash.hash(password, secrets_dict["VACUUMSALT"])
        totp = pyotp.TOTP(secrets_dict['OTS_SECRET'])
        otpValid = totp.verify(otpin)
        #logger.warning("User: {0} with password:'{1}'".format(username, pwdHashed))
        #logger.warning("root user: {0} with hash:{1}".format(os.environ.get('VACUUMROOTUSER'), os.environ.get('VACUUMROOTHASH')))
        if pwdHashed == secrets_dict['VACUUMROOTHASH']  \
            and username == secrets_dict['VACUUMROOTUSER'] \
            and otpValid:
            my_user = objects.User(username)
            flask_login.login_user(my_user)
            logger.info("Admin User Logged In.")
            return render_template("loginmenu.html")
        else:
            if username == secrets_dict['VACUUMROOTUSER']:
                logger.info("Admin username matched")
            if pwdHashed == secrets_dict['VACUUMROOTHASH']:
                logger.info("pwd matched")
            if otpValid:
                logger.info("OTP provided is Valid")
            logger.warning("User or Password or OTP didn't match")
            ip_ban.add()
            logger.warning("Failed login with headers: {0}".format(request.headers))
            return render_template("authissue.html", code=401)
    else:
        logger.warning ("User name and password not sent")
        return render_template("authissue.html", code=402)

@app.route('/brat/<int:number>')
def get_brat_no(number):
    return f'Brat number {number} reporting in for duty'

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

@app.route('/public_content_large', methods=['GET'])
@flask_login.login_required
def public_content_large():
    return render_template("public_content_large_upload.html")

@app.route('/public_content_large', methods=['POST'])
@flask_login.login_required
def public_content_large_upload():
    if 'file' in request.files:
        file = request.files['file']
        save_path = os.path.join(os.environ.get("LARGE_FILE_TMP_PATH"), secure_filename(file.filename))
        current_chunk = int(request.form['dzchunkindex'])
        # If the file already exists it's ok if we are appending to it,
        # but not if it's new file that would overwrite the existing one
        if os.path.exists(save_path) and current_chunk == 0:
            # 400 and 500s will tell dropzone that an error occurred and show an error
            return make_response(('File already exists', 400))

        try:
            with open(save_path, 'ab') as f:
                f.seek(int(request.form['dzchunkbyteoffset']))
                f.write(file.stream.read())
        except OSError:
            # log.exception will include the traceback so we can see what's wrong
            logger.exception('Could not write to file')
            return make_response(("Not sure why,"
                                  " but we couldn't write the file to disk", 500))

        total_chunks = int(request.form['dztotalchunkcount'])

        if current_chunk + 1 == total_chunks:
            # This was the last chunk, the file should be complete and the size we expect
            if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
                logger.error(f"File {file.filename} was completed, "
                          f"but has a size mismatch."
                          f"Was {os.path.getsize(save_path)} but we"
                          f" expected {request.form['dztotalfilesize']} ")
                return make_response(('Size mismatch', 500))
            else:
                logger.info(f'File {file.filename} has been uploaded to the container successfully')
                #
                #CMH My code picks up here
                #This function borrowed from stack overflow https://stackoverflow.com/questions/44727052/handling-large-file-uploads-with-flask
                #
                with open(save_path,'rb') as complete_file_obj:
                    if request.form.get("ReMuxMovToMP4"):
                        # new_img.append(image_processing.convert_mov_to_mp4(file.stream, file.filename))
                        logger.info(f"S3 Start Transfer to internal bucket {internal_bucket} of file {file.filename}")
                        s3_upload_file(complete_file_obj, file.filename, internal_bucket)
                        return render_template("save.html")
                    else:
                        s3_upload_file(complete_file_obj, file.filename)
                        logger.info(f"File {file.filename} has been uploaded to the pubilc bucket successfully")
                os.remove(save_path)#clean up local chunked file
                return render_template("save.html")
        else:
            logger.debug(f'Chunk {current_chunk + 1} of {total_chunks} '
                      f'for file {file.filename} complete')

        return make_response(("Chunk upload successful", 200))
    else:
        logger.error("Upload hit without a sending a file.")

@app.route('/public_content', methods=['POST'])
@flask_login.login_required
def public_content_file_upload():
    if 'file' in request.files:
        file = request.files['file']
        #if file and allowed_file(file.filename):
        #TODO: There is a bug with rename, when you rename and remux at the same time, it keeps the old filename
        if file.filename != request.form.get('new_filename')\
               and request.form.get('new_filename')\
                and request.form.get('new_filename') != "":
            file.filename = request.form.get('new_filename')
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
            #new_img.append(image_processing.convert_mov_to_mp4(file.stream, file.filename))
            logger.info(f"S3 Start Transfer to internal bucket {internal_bucket} of file {file.filename}")
            s3_upload_file(file,file.filename,internal_bucket)
            return render_template("save.html")
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
    else:
        logger.error("Upload hit without a sending a file.")
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
    having t.enabled=1 and count(pt.id) > 0
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


@app.route('/login/oauth2/code/okta')
def okta_auth_callback():
    logger.info("OKTA called back.")
    code = request.args.get('code')
    state = request.args.get('state')
    logger.info(f"Code from okta: {code} and state {state}")
    if state == session['app_state']:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        code = request.args.get("code")
        app_state = request.args.get("state")
        if app_state != session['app_state']:
            logger.error( "The app state does not match")
            return render_template("authissue.html", code=402)
        if not code:
            logger.error("The code was not returned or is not accessible")
            return render_template("authissue.html", code=402)
        query_params = {'grant_type': 'authorization_code',
                        'code': code,
                        'redirect_uri': request.base_url,
                        'code_verifier': session['code_verifier'],
                        }
        query_params = requests.compat.urlencode(query_params)
        exchange = requests.post(
            os.environ['OKTA_AUTH_REDIRECT_URL'] + "oauth2/default/v1/token",
            headers=headers,
            data=query_params,
            auth=(os.environ['OKTA_CLIENT_ID'], os.environ['OKTA_CLIENT_SECRET']),
        ).json()

        # Get tokens and validate
        if not exchange.get("token_type"):
            return "Unsupported token type. Should be 'Bearer'.", 403
        access_token = exchange["access_token"]
        id_token = exchange["id_token"]

        # Authorization flow successful, get userinfo and login user
        userinfo_response = requests.get(os.environ['OKTA_AUTH_REDIRECT_URL'] + "oauth2/default/v1/userinfo",
                                         headers={'Authorization': f'Bearer {access_token}'}).json()

        unique_id = userinfo_response["sub"]
        #user_email = userinfo_response["email"]
        #user_name = userinfo_response["given_name"]

        my_user = objects.User(unique_id)
        flask_login.login_user(my_user)
        logger.info("Admin User Logged In.")
        return render_template("loginmenu.html")
    else:
        logger.error("The state does not match")
        logger.info(f"State vs State okta state: {state} and session state {session['app_state']}")
        return render_template("authissue.html", code=402)


@app.route('/login-okta', methods=['GET'])
def okta_auth_redirect():
    okta_auth_redirect_url = os.environ.get("OKTA_AUTH_REDIRECT_URL")
    # get request params
    # store app state and code verifier in session
    app_state = secrets.token_urlsafe(64)
    code_verifier = secrets.token_urlsafe(64)
    session['app_state'] = app_state
    logger.info(f"app_state: {app_state}")
    logger.info(f"urlsafe app_date: {session['app_state']}")
    session['code_verifier'] = code_verifier
    rsp = flask.wrappers.Response()
    app.session_interface.save_session(app,session, response=rsp)
    logger.info(f"session save response: {rsp.status_code}")
    # calculate code challenge
    hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
    encoded = base64.urlsafe_b64encode(hashed)

    code_challenge = encoded.decode('ascii').strip('=')
    query_params = {'client_id': os.environ['OKTA_CLIENT_ID'],
                    'redirect_uri': os.getenv('OKTA_LOCAL_REDIRECT_URL'),
                    'scope': "openid email profile offline_access",
                    'state': app_state,
                    'code_challenge': code_challenge,
                    'code_challenge_method': 'S256',
                    'response_type': 'code',
                    'response_mode': 'query'}
    # build request_uri
    request_uri = "{base_url}?{query_params}".format(
        base_url=os.environ['OKTA_AUTH_REDIRECT_URL'] + "oauth2/default/v1/authorize",
        query_params=requests.compat.urlencode(query_params)
    )
    logger.info("OKTA request uri: {0}".format(request_uri))
    return redirect(request_uri)

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

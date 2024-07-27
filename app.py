from flask import Flask, request, Blueprint, render_template, make_response
import sqlite3
import yaml
from flask_login import login_required, current_user
import json
from datetime import datetime
import hash
import os
import flask_login
import objects
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("VACUUMSESSIONKEY")
app.config['SESSION_TYPE'] = 'filesystem'
auth = Blueprint('auth', __name__)
login_manager = flask_login.LoginManager(app)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4'}
app.config['UPLOAD_FOLDER'] = '/home/colin/python/blog2/vacuumflask/uploads'
db_path = "/home/colin/python/blog2/vacuumflask/data/vacuumflask.db"

@login_manager.user_loader
def load_user(user_id):
    user = objects.User(user_id)
    return user

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    if username and password:
        pwdHashed = hash.hash(password)
        if pwdHashed == os.environ.get('VACUUMROOTHASH')  \
            and username == os.environ.get('VACUUMROOTUSER'):
            my_user = objects.User(username)
            flask_login.login_user(my_user)
            return json.dumps({'success': True, "tempapikey": my_user.get_apikey()}), 200, {'ContentType': 'application/json'}
        else:
            print ("Password hash didn't match")
            return json.dumps({'success': False}), 401, {'ContentType': 'application/json'}
    else:
        print ("User name and password not sent")
        return json.dumps({'success': False}), 401, {'ContentType': 'application/json'}

@app.route('/brat/<int:number>')
def get_brat_no(number):
    return f'Brat number {number} reporting in for duity'


@app.route('/post/<int:number>')
def blogpost(number):
    conn = sqlite3.connect(db_path)
    sql = "SELECT * FROM post WHERE id = ?"
    cur = conn.cursor()
    #post_id = request.args.get('number', type=int)
    cur.execute(sql, [number])
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
    return json.JSONEncoder().encode(post)

@app.route('/post/<old_id>')
def oldblogpost(number):
    conn = sqlite3.connect(db_path)
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
    return json.JSONEncoder().encode(post)

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
    return json.JSONEncoder().encode(posts)


@app.route('/post', methods=['POST'])
@flask_login.login_required
def create_blogpost():
    required_parms = ['subject', 'date', 'rss_description','seo_keywords', 'body' ]
    data = dict()
    for parm in required_parms:
        data[parm] = request.form.get(parm)
    conn = sqlite3.connect(db_path)
    sql = """insert into post(subject,date,rss_description,seo_keywords,body)
        values(?,?,?,?,?);"""
    cur = conn.cursor()
    post_date_obj = datetime.strptime(data['date'], "%m/%d/%Y")
    cur.execute(sql, [data['subject'], int(post_date_obj.timestamp())
        ,data['rss_description'], data['seo_keywords']
        ,data['body']])
    conn.commit()
    conn.close()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
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

@app.route('/')
def index():
    conn = sqlite3.connect(db_path)
    sql = """select id, old_id, date,post.rss_description, seo_keywords, body, subject
            from post 
            order by date desc;"""
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    conn.close()
    posts = []
    for post in results:
        blog = objects.blog_post()
        blog.load_from_array(post)
        posts.append(blog.serialize())
    return render_template('index.html', posts=posts, debug=app.debug)

if __name__ == '__main__':

    login_manager.init_app(app)
    #app.run(debug=True)

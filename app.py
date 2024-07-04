from flask import Flask, request
import sqlite3
import yaml
import json
from datetime import datetime
app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/double')
def double():
    try:
        # Get the integer from the query parameter
        number = int(request.args.get('number'))
        # Calculate the double of the number
        result = number * 2
        return f'The double of {number} is {result}'
    except (TypeError, ValueError):
        return 'Please provide a valid integer as the "number" query parameter.'


# Define a route with an integer parameter
@app.route('/square/<int:number>')
def square(number):
    # Calculate the square of the number
    result = number ** 2
    # Return the result as a string
    return f'The square of {number} is {result}'

@app.route('/brat/<int:number>')
def get_brat_no(number):
    conn = sqlite3.connect('data/vacuumflask.db')
    sql = "SELECT * FROM post WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, [number])
    results = cur.fetchall()
    conn.close()
    return f'Brat number {number} reporting in for duity'

@app.route('/blogpost/<int:number>')
def blogpost(number):
    conn = sqlite3.connect('data/vacuumflask.db')
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

@app.route('/blogpost', methods=['POST'])
def create_blogpost():
    required_parms = ['subject', 'date', 'rss_description','seo_keywords', 'body' ]
    data = dict()
    for parm in required_parms:
        data[parm] = request.form.get(parm)
    conn = sqlite3.connect('data/vacuumflask.db')
    sql = """insert into post(subject,date,rss_description,seo_keywords,body)
        values(?,?,?,?,?);"""
    cur = conn.cursor()
    post_date_obj = datetime.strptime(data['date'], "%m/%d/%Y")
    cur.execute(sql, [data['subject'], int(post_date_obj.timestamp())
        ,data['rss_description'], data['seo_keywords']
        ,data['body']])
    conn.commit()
    conn.close()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}rmd

if __name__ == '__main__':
    app.run(debug=True)

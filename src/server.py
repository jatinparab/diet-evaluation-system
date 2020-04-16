# -*- coding: utf-8 -*-
import uuid as uuid
from _curses import flash

from flask import *
import boto3, botocore, json, datetime
from boto3 import *
from boto3.dynamodb.conditions import Key, Attr
import os
import uuid

UPLOAD_FOLDER = '{0}{1}'.format(os.getcwd(), '/src/templates/img/')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__, static_folder='templates', static_url_path='')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

error_page = '''
            <!DOCTYPE HTML>
            <html>
              <head>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                <link rel="icon" href="favicon.ico" />
                <meta http-equiv="refresh" content="3;url=/">
                <title>HEALTHY DIET EVALUATION SYSTEM</title>
              </head>
              <body>You entered an invalid user ID, you will be redirected to homepage in 3 seconds ...</body>
            </html>
            '''


def get_status(score):
    return 'Unhealthy' if score < 40.0 else 'Healthy' if score > 70.0 else 'Fair'


def get_time_format(timestamp):
    return timestamp[:4] + '-' + timestamp[4:6] + '-' + timestamp[6:8] + ' ' + timestamp[8:10] + ':' + timestamp[
                                                                                                       10:12] + ':' + timestamp[
                                                                                                                      12:14]


@app.route("/", methods=['GET', 'POST'])
def handle():
    if request.method == 'GET' and not request.args.get('q'):
        return app.send_static_file("index.html")

    elif request.method == 'POST' or request.args.get('q'):
        if request.method == 'POST':
            userID = request.form['userID']
        else:
            userID = request.args['q']

        if len(userID) == 0:
            return error_page
        session = boto3.Session(
            aws_access_key_id='AKIAIXDBGVH3NYOYVTZQ',
            aws_secret_access_key='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',
        )
        dynamodb = session.resource('dynamodb', region_name='ap-south-1')
        table = dynamodb.Table('scores')
        response = table.query(
            Limit=90,
            KeyConditionExpression=Key('userID').eq(userID),
            ScanIndexForward=False
        )
        response['Items'] = sorted(response['Items'], key=lambda item: int(item['time']), reverse=True)
        item_lenth = len(response['Items'])
        items = []
        imgNames = []
        if item_lenth == 0:
            return redirect('{0}?q={1}'.format(url_for('submit_link'), userID))
        elif item_lenth == 1:
            try:
                new_score = float(response['Items'][0]['score'])
            except ValueError:
                new_score = 0
            if new_score > 1:
                items.append(response['Items'][0])
            imgNames.append([str(get_time_format(response['Items'][0]['time'])),
                             response['Items'][0]['imgName'],
                             str(round(new_score, 1))])
        else:
            for item in response['Items']:
                try:
                    score = float(item['score'])
                except ValueError:
                    score = 0
                imgNames.append(
                    [str(get_time_format(item['time'])), item['imgName'], str(round(score, 1))])
            scores, count = -1, 1
            for index in range(0, item_lenth):
                try:
                    scores = float(response['Items'][index]['score'])
                except ValueError:
                    scores = 0
                if scores > 1:
                    break
            if scores < 0:
                return error_page
            i = index + 1
            while i < item_lenth:
                if response['Items'][i]['time'] == response['Items'][i - 1]['time']:
                    try:
                        score = float(response['Items'][i]['score'])
                    except ValueError:
                        score = 0
                    count = 1
                    new_score = score
                    if new_score > 1:
                        scores += new_score
                        count += 1
                    i += 1
                else:
                    if scores > 1:
                        response['Items'][i - 1]['score'] = scores / count
                        items.append(response['Items'][i - 1])
                    try:
                        scores = float(response['Items'][i]['score'])
                    except ValueError:
                        scores = 0
                    count = 1
                    i += 1
                    if i >= item_lenth:
                        break
                    while not scores > 1:
                        try:
                            scores = float(response['Items'][i]['score'])
                        except ValueError:
                            scores = 0
                        count = 1
                        i += 1
                        if i >= item_lenth:
                            break

            if scores > 1:
                response['Items'][item_lenth - 1]['score'] = scores / count
                items.append(response['Items'][item_lenth - 1])

        result = []
        monthDate = int((datetime.datetime.now() + datetime.timedelta(-30)).strftime('%Y%m%d%H%M%S'))
        weekDate = int((datetime.datetime.now() + datetime.timedelta(-7)).strftime('%Y%m%d%H%M%S'))
        monthTotal = 0.0
        monthNum = 0
        weekTotal = 0.0
        weekNum = 0
        for item in items:
            timestamp = item['time']
            time = int(timestamp)
            score = round(float(item['score']), 1)
            if time >= monthDate:
                monthTotal += score
                monthNum += 1
            if time >= weekDate:
                weekTotal += score
                weekNum += 1
            result.append([timestamp, score])

        score_weekly = 0.0
        score_monthly = 0.0
        if weekNum > 0:
            score_weekly = round(weekTotal / weekNum, 1)
            weekStatus = get_status(score_weekly)
        else:
            weekStatus = 'No records'
        if monthNum > 0:
            score_monthly = round(monthTotal / monthNum, 1)
            monthStatus = get_status(score_monthly)
        else:
            monthStatus = 'No records'

        return render_template("userInfo.html", data=result, week=score_weekly, status_week=weekStatus,
                               month=score_monthly, status_month=monthStatus, user=userID, imgName=imgNames)

    else:
        redirect(url_for('/'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/submit_link", methods=['GET', 'POST'])
def submit_link():
    import urllib.request
    import base64
    import uuid
    from recognize import recognize
    if request.method == 'GET':
        userID = request.args.get('q', '')
        return render_template("submit_link.html", userID=userID)
    elif request.method == 'POST':
        url = request.form.get('url')
        userID = request.form.get('userID')
        # check if the post request has the file part
        if 'file' in request.files:

            file = request.files['file']

            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = file.filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                full_path = '{0}{1}'.format(UPLOAD_FOLDER, filename)
                path = 'img/{0}'.format(filename)
        elif url:
            uuid = uuid.uuid4()

            uuid = str(uuid)
            path = 'img/{0}.{1}'.format(uuid, 'png')
            full_path = '{0}/src/templates/{1}'.format(os.getcwd(), path)
            resource = urllib.request.urlopen(url)
            output = open(full_path, "wb")
            output.write(resource.read())
            output.close()
        else:
            flash('Please enter valid data')
            return redirect(request.url)
        with open(full_path, 'rb') as image:
            response = recognize(image.read(), path, userID)
            return render_template("result.html", score=response['score'],
                                   detected_labels=response['detected_labels'], imagePath=path, userID=userID)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=80, threaded=True)

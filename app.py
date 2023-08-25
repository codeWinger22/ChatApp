import json
import os
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for, jsonify

#for chat

from datetime import datetime
from bson.json_util import dumps
from flask_socketio import SocketIO, join_room, leave_room
from pymongo.errors import DuplicateKeyError
from db import get_user, save_user, save_room, add_room_members, get_rooms_for_user, get_room, is_room_member, \
   get_room_members, is_room_admin, update_room, remove_room_members, save_message, get_messages,get_room_existence
from flask_cors import CORS, cross_origin


# set up the environment variable
# this environment variable need to be set in order to run it over http
# as we are running this currently on localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # without https



from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user)

# this flask login package is important for user session management instead of creating it manually we are using the
# predefined library


from oauthlib.oauth2 import WebApplicationClient
# WebapplicationClient because we are building it on the client side
import requests
# from db import init_db_command
from user import User, UserProfile
from engineio.async_drivers import gevent

# now we will import the environment variables
# GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID',None)
# GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET',None)
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_CLIENT_ID = "652381501875-vav5i893k6atvuj80vei5j0u77cfid5v.apps.googleusercontent.com"

GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")

# this discovery url is basically the one from where your app will fetch google account from



app = Flask(__name__, static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///basicinformation.sqlite3'
app.config['SECRET_KEY'] = "secret key"
db = SQLAlchemy(app)
app.secret_key = "sfdjkafnk"
socketio = SocketIO(app)

CORS(app, origins=["http://localhost:5000"])
cors = CORS(app, resource={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'



# either you can set a secret key in environment variable or just generate a 24char secret key


login_manager = LoginManager()
login_manager.init_app(app)


# this is not required until the external db.py file is working

def init_db_command():
    connection = sqlite3.connect('database.db')
    with open('schema.sql') as f:
        connection.executescript(f.read())

    cur = connection.cursor()
    connection.commit()
    connection.close()


# initialize a handler
@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content", 403

    # try:
    init_db_command()


# except sqlite3.OperationalError:
#    pass

client = WebApplicationClient(GOOGLE_CLIENT_ID)


# initialize helper
@login_manager.user_loader
def load_user(user_id):
    flag = 0
    user = User.get(user_id, flag)
    print(user, "from main helper")
    if not user:
        return None
    return user

    # return User.get(user_id,flag)


@app.route('/connection')
def connection():
    return render_template('admin_doctor.html')

def assignDoctors():
    doctordata = UserProfile.getDoctorData(flag = 1)
    #the above method returns count of doctors if present or returns None
    patientdata = UserProfile.getDoctorData(flag=2)    #returns list with count and query result
    if((doctordata[0] != 0) and (patientdata[0] != 0)):
        docCount = doctordata[0]
        patCount = patientdata[0]
        docdata= doctordata[1]
        patdata = patientdata[1]
        #for i in docdata:
         #   print(i[0],"testing")
        d = dict()
        print(patCount,"this is patient count")
        print(docCount,"this is doctor count")
        print(docdata,"this is doctor data")
        print(patdata,"this is patient data")
        if(patCount<=docCount):
            max_capacity = patCount
            print(max_capacity)
            for i in range(patCount):
                d[docdata[i][0]] = patdata[i][0]

            #a = docdata[0][0]
            #b = patdata[0][0]
            #d = {a : b}
            print(d)
            create_room(d)
        else:
            max_capacity = patCount//docCount
            algorithmicAssignment(patCount,docCount,docdata,patdata,max_capacity)
    elif(doctordata==None and patientdata != None):
        max_capacity = 0
        print("no doctors available")
    elif(doctordata !=None and patientdata==None):
        max_capacity = 0
        print("no patients avaiable")

def algorithmicAssignment(patCount,docCount,docData,patData,max_capacity):
    #not completely tested might give error tested only on standalone algorithm.py file
    doclist = []
    patlist= []
    #patdata and docdata contains tuple inside list
    for i in docData:
        doclist.append(i[0])
    for j in patData:
        patlist.append(j[0])
    d = dict()
    if (max_capacity == patCount):
        for i in range(max_capacity):
            d[doclist[i]] = patlist[i]

    else:
        print("here")
        count = 1
        maincount = 0
        for i in range(patCount):
            if (count > max_capacity):
                count = 1
                maincount = maincount + 1
            patval = patlist[i]
            d[doclist[maincount]] = patlist[i]
            count = count + 1
        count = 1
        maincount = 0
        l = []
        for i in range(patCount):
            if (count > max_capacity):
                d[doclist[maincount]] = l
                count = 1
                l = []
                maincount = maincount + 1
            patval = patlist[i]
            # d[patval] = doct[maincount

            l.append(patlist[i])
            count = count + 1

    print(d)
    print("Dictionary of Assignment")
    print(d)
    create_room(d)
    #optimization required



#internally called


def create_room(d):
    count = 0
    initial = "room"
    try:
        for key,value in d.items():
            room_name = initial + str(count)
            prevroom = get_rooms_for_user(key)
            print(type(prevroom))
            result = findoutroom(prevroom,room_name,key,value)



            count = count + 1
    except Exception as e:
        print(e)

def findoutroom(prevroom,room_name,key,value):

    for i in prevroom:
        if(i['room_name'] == room_name):
            print(i)
            print("user already exists")

            return 1
        else:
            print("reached else")
            room_id = save_room(room_name,key)
            add_room_members(room_id,room_name,value,key)
            return 0
    return 0

        #admin for the room will be doctor itself (you can change it later to site admin as well)








@app.route('/')
def index():
    assignDoctors()
    print("reached in index api")
    print(current_user)
    if (current_user.is_authenticated):
        print("from final ")
        print(current_user.name)
        print(current_user.email)
        return ("<h1> YOU ARE LOGGED IN </h1>"
                "<div> <p> Google Profile </p>"
                '<img src = "{}" alt = "Google Profile Pic" ></img></div>'
                '<a class "button" href = "/logout">Logout</a>'.format(current_user.name, current_user.email,
                                                                       current_user.profile_pic))
    else:
        print("not authenticated")
        return render_template('index.html')
    # return '<a class = "button" href = "/loginAdmin"> Google Admin Login </a>  <br><br> <a class = "button" href = "/loginDoctor"> Google Login </a>'


@app.route('/doctorsign')
def doctorsign():
    return render_template("doctorsignup.html")


@app.route('/doctorclick')
def doctorclick():
    return render_template('doctor_click.html')


@app.route('/adminapprovedoctor')
def adminapprovedoctor():
    data = UserProfile.getApproval()
    if (data == None):
        return render_template('admin_approve_doctor.html')

    return render_template('admin_approve_doctor.html', data=data)


@app.route('/adminviewdoctor')
def adminviewdoctor():
    return render_template('admin_view_doctor.html')


@app.route('/approveddoctorUpdate<doctorid>')
def approveddoctorUpdate(doctorid):
    result1 = UserProfile.updateApproval(doctorid)
    if (result1 == 1):
        return render_template('admin_approve_doctor.html')
    return render_template('admin_approve_doctor.html')
    # which means we need to reject and delete the entry of that doctor from userDoctor and DoctorProfile table

@app.route('/approveddoctorDelete<doctorid>')
def approveddoctorDelete(doctorid):
    result1  = User.remove(doctorid)
    result2 = UserProfile.remove(doctorid)
    if(result1==1 and result2 == 1):
        return  render_template('admin_approve_doctor.html')
    return render_template('admin_approve_doctor.html')


@app.route('/adminindex')
def adminindex():
    if (current_user.is_authenticated):
        print("from final ")
        print(current_user.name)
        print(current_user.email)

        return ("<h1> YOU ARE LOGGED IN AS ADMIN</h1>"
                "<div> <p> Google Profile </p>"
                '<img src = "{}" alt = "Google Profile Pic" ></img></div>'
                '<a class "button" href = "/logout">Logout</a>'.format(current_user.name, current_user.email,
                                                                       current_user.profile_pic))
    else:
        print("not authenticated")
        return render_template('index.html')


@app.route('/doctorindex')
def doctorindex():
    if (current_user.is_authenticated):
        print("from final ")
        print(current_user.name)
        print(current_user.email)
        return ("<h1> YOU ARE LOGGED IN AS DOCTOR</h1>"
                "<div> <p> Google Profile </p>"
                '<img src = "{}" alt = "Google Profile Pic" ></img></div>'
                '<a class "button" href = "/logout">Logout</a>'.format(current_user.name, current_user.email,
                                                                       current_user.profile_pic))
    else:
        print("not authenticated")
        return render_template('index.html')


@app.route('/patientindex')
def patientindex():
    if (current_user.is_authenticated):
        print("from final ")
        print(current_user.name)
        print(current_user.email)
        prevroom = get_rooms_for_user(current_user.id)
        print(type(prevroom))
        print(prevroom)
        for i in prevroom:
            print(i['_id']['room_id'])
            print(i['username'])
       # print(i['_id']['room_id'])
        # room id required
        room = get_room(room_id)
        print(room, "this is room")
        print(room['_id'])
        if room and is_room_member(room_id, current_user.username):
            room_members = get_room_members(room_id)
            messages = get_messages(room_id)
            return render_template('view_room.html', username=current_user.username, room=room,
                                   room_members=room_members,
                                   messages=messages)
        else:
            return "Room not found", 404

        return render_template('patienthome.html')
        # return ("<h1> YOU ARE LOGGED IN AS PATIENT</h1>"
        #       "<div> <p> Google Profile </p>"
        #      '<img src = "{}" alt = "Google Profile Pic" ></img></div>'
        #     '<a class "button" href = "/logout">Logout</a>'.format(current_user.name,current_user.email,current_user.profile_pic))
    else:
        print("not authenticated")
        return render_template('index.html')



@app.route('/logout')
@login_required
def logout():
    if (logout_user()):
        print("logged out")
        current_user.authenticated = False

    return redirect(url_for('index'))

    # return '<a class = "button" href = "/login"> Google Login </a>'


@app.route('/login<flag>')
def login(flag):
    print("this is login flag ")
    print(flag)

    if (flag == '1'):
        google_provider_cgf = get_google_provider_cfg()
        authorization_endpoint = google_provider_cgf['authorization_endpoint']
        request_uri = client.prepare_request_uri(authorization_endpoint,
                                                 redirect_uri="http://localhost:5000/login/callbackAdmin",
                                                 scope=['openid', 'email', 'profile'])
        print("completed login process", request_uri)
    elif (flag == '2'):
        google_provider_cgf = get_google_provider_cfg()
        authorization_endpoint = google_provider_cgf['authorization_endpoint']
        request_uri = client.prepare_request_uri(authorization_endpoint,
                                                 redirect_uri="http://localhost:5000/login/callbackDoctor",
                                                 scope=['openid', 'email', 'profile'])
        print("completed login process", request_uri)

    elif (flag == '3'):
        google_provider_cgf = get_google_provider_cfg()
        authorization_endpoint = google_provider_cgf['authorization_endpoint']
        request_uri = client.prepare_request_uri(authorization_endpoint,
                                                 redirect_uri="http://localhost:5000/login/callbackPatient",
                                                 scope=['openid', 'email', 'profile'])
        print("completed login process", request_uri)

    return redirect(request_uri)

    # configuration url
    # redirect url = http://localhost:5000/login/callbackAdmin
    # client = WebApplicationClient(GOOGLE_CLIENT_ID_ADMIN)


@app.route('/login/callbackAdmin')
def callbackAdmin():
    print("reached in callbackAdmin")
    flag = 1

    code = request.args.get('code')
    # authorization code
    # now with this we can get the authorization
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg['token_endpoint']

    # prepare token url
    token_url, headers, body = client.prepare_token_request(token_endpoint, authorization_response=request.url,
                                                            redirect_url="http://localhost:5000/login/callbackAdmin",
                                                            code=code)
    token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg['userinfo_endpoint']
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    print(userinfo_response.json())
    if (userinfo_response.json().get('email_verified')):
        unique_id = userinfo_response.json()['sub']
        user_email = userinfo_response.json()['email']
        picture = userinfo_response.json()['picture']
        username = userinfo_response.json()['given_name']
        print("before inserting into db callback function")
    else:
        return "User email not available or not verified by google", 400
    # now we need to insert this user inside our sqlite db

    user = User(id=unique_id, name=username, email=user_email, profile_pic=picture)
    print(unique_id)

    returnfunction = User.get(unique_id, flag)
    print(returnfunction)
    if (returnfunction != None):
        print("user already exists")
    else:

        User.create(unique_id, username, user_email, picture, flag)

    # start the session
    if (login_user(user)):
        print("user logged in")
        print("completed callback admin process ")
        current_user.autheticated = True
    else:
        print("user not logged in")

    # and redirect to the homepage
    return redirect(url_for('connection'))  # def index which is created previously


@app.route('/login/callbackDoctor')
def callbackDoctor():
    print("reached in callbackDoctor")
    flag = 2

    code = request.args.get('code')
    # authorization code
    # now with this we can get the authorization
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg['token_endpoint']

    # prepare token url
    token_url, headers, body = client.prepare_token_request(token_endpoint, authorization_response=request.url,
                                                            redirect_url="http://localhost:5000/login/callbackDoctor",
                                                            code=code)
    token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg['userinfo_endpoint']
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    print(userinfo_response.json())
    if (userinfo_response.json().get('email_verified')):
        unique_id = userinfo_response.json()['sub']
        user_email = userinfo_response.json()['email']
        picture = userinfo_response.json()['picture']
        username = userinfo_response.json()['given_name']
        print("before inserting into db callback function")
    else:
        return "User email not available or not verified by google", 400
    # now we need to insert this user inside our sqlite db

    user = User(id=unique_id, name=username, email=user_email, profile_pic=picture)

    print(unique_id, "from callbackdoctor")

    returnfunction = User.get(unique_id, flag)
    result = UserProfile.getProfile(unique_id, flag)

    print(returnfunction)
    print(result, "getprofile")
    # print(result.status,"from doctorcallback")

    if (returnfunction != None):
        if (result != None):
            if (result.status == 0):
                return render_template('DoctorApprovalPending.html')
            else:
                print("user already exists")
                # start the session
                if (login_user(user)):
                    print("user logged in")
                    print(user)
                    print("completed callback doctor process ")
                    current_user.autheticated = True
                    return redirect(url_for('doctorindex'))



    else:

        User.create(unique_id, username, user_email, picture, flag)
        return render_template('doctorprofile.html', id=unique_id)

    return redirect(url_for('doctorindex'))

    # start the session


# if(login_user(user)):
#     print("user logged in")
#    print("completed callback doctor process ")
#   current_user.autheticated = True
# else:
#    print("user not logged in")


# and redirect to the homepage
# return redirect(url_for('doctorindex')) #def index which is created previously


@app.route('/getDoctorProfile', methods=['POST'])
def getDoctorProfile():
    data = request.form
    name = data['name']
    email = data['email']
    address = data['qualification']
    qualification = data['qualification']
    user = data['id']

    print(user)
    flag = 2

    returnfunction = User.get(str(user), flag)
    print("from doctor profile")
    print(returnfunction)

    # id name email address qual status
    if(returnfunction == None):
        data = UserProfile.getApproval()
        if (data == None):
            return render_template('admin_approve_doctor.html')
    else:
        status = 0
        id = returnfunction.id
        name = returnfunction.name
        email = returnfunction.email
    # userprofile = UserProfile(id = id , name = name , email = email, address = address, qualification = qualification,status=status)
        result = UserProfile.add(id, name, email, address, qualification, status, flag=2)
    # user = User.get(id,2)
        if (result == None):
            current_user.autheticated = False
            return render_template("DoctorApprovalPending.html")
        else:

            print("user already exists")
        # start the session
            if (login_user(user)):
                print("user logged in")
                print("doctor profiling completed ")
                current_user.autheticated = True
    return redirect(url_for('doctorindex'))  # def index which is created previously


@app.route('/login/callbackPatient')
def callbackPatient():
    print("reached in callbackPatient")
    flag = 3

    code = request.args.get('code')
    # authorization code
    # now with this we can get the authorization
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg['token_endpoint']

    # prepare token url
    token_url, headers, body = client.prepare_token_request(token_endpoint, authorization_response=request.url,
                                                            redirect_url="http://localhost:5000/login/callbackPatient",
                                                            code=code)
    token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg['userinfo_endpoint']
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    print(userinfo_response.json())
    if (userinfo_response.json().get('email_verified')):
        unique_id = userinfo_response.json()['sub']
        user_email = userinfo_response.json()['email']
        picture = userinfo_response.json()['picture']
        username = userinfo_response.json()['given_name']
        print("before inserting into db callback function")
    else:
        return "User email not available or not verified by google", 400
    # now we need to insert this user inside our sqlite db

    user = User(id=unique_id, name=username, email=user_email, profile_pic=picture)
    print(unique_id)

    returnfunction = User.get(unique_id, flag)
    print(returnfunction)
    if (returnfunction != None):
        print("user already exists")
    else:

        User.create(unique_id, username, user_email, picture, flag)

    # start the session
    if (login_user(user)):
        print("user logged in")
        print("completed callback patient process ")
        current_user.autheticated = True
    else:
        print("user not logged in")

    # and redirect to the homepage
    return redirect(url_for('patientindex'))  # def index which is created previously


# -----------------------------------------------------------------------


# original login and callback
""" @app.route('/loginoriginal')
def login():
    #configuration url 
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
    google_provider_cgf =  get_google_provider_cfg()
    authorization_endpoint = google_provider_cgf['authorization_endpoint']
    request_uri  = client.prepare_request_uri(authorization_endpoint,redirect_uri="http://localhost:5000/login/callback",scope = ['openid','email','profile'])
    print("this is request uri")
    print(request_uri)
    return redirect(request_uri)

@app.route('/login/callbackoriginal')
def callback():
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
    code = request.args.get('code')
    #authorization code 
    #now with this we can get the authorization
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint  = google_provider_cfg['token_endpoint']

    #prepare token url 
    token_url , headers , body = client.prepare_token_request(token_endpoint,authorization_response=request.url,redirect_url="http://localhost:5000/login/callback",code = code)
    token_response = requests.post(token_url,headers=headers,data = body,auth=(GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET))
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg['userinfo_endpoint']
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri,headers=headers,data = body)
    print(userinfo_response.json())
    if(userinfo_response.json().get('email_verified')):
        unique_id = userinfo_response.json()['sub']
        user_email = userinfo_response.json()['email']
        picture = userinfo_response.json()['picture']
        username = userinfo_response.json()['given_name']
        print("before inserting into db callback function")
    else:
        return "User email not available or not verified by google",400
    #now we need to insert this user inside our sqlite db

    user = User(id= unique_id,name = username, email = user_email,profile_pic=picture)
    print(unique_id)
    returnfunction = User.get(unique_id)
    print(returnfunction)
    if( returnfunction != None):
        print("user already exists")
    else:
        User.create(unique_id,username,user_email, picture)


    #start the session
    if(login_user(user)):
        print("user logged in")
    else:
        print("user not logged in")



    #and redirect to the homepage
    return redirect(url_for('index')) #def index which is created previously
    """


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


if __name__ == '__main__':
    app.run(debug=True)

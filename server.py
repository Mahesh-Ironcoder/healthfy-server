import json
from flask.helpers import make_response


import pandas as pd
from flask import Flask, request, session, abort, redirect
from flask.json import jsonify
from flask_cors import CORS, cross_origin

import pickle

import datetime

import firebase_admin
from firebase_admin import credentials, auth, exceptions, firestore

cred = credentials.Certificate(
    "resources/healthfy-97c5c-firebase-adminsdk-px6u9-1458c0eda2.json")
firebase_app = firebase_admin.initialize_app(cred)

db = firestore.client()


app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

gluco_Modal = None
dia_Modal = None
col_Modal = None


@app.route("/api")
@cross_origin()
def index():
    print(request.headers.get("Origin"))
    # print(request.)
    # print(list(request.headers.items()))
    return "hello from Healthfy", 200


@app.before_first_request
def loadModals():
    print("from first request")
    # gluco_Modal = pickle.load(open('glucoseModel.pkl', 'rb'))
    dia_Modal = pickle.load(open('DiabetiesModel.pkl', 'rb'))
    col_Modal = pickle.load(open('colestrolModel.pkl', 'rb'))


@app.route("/api/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        formData = request.form.to_dict()
        userName = formData.get("username")
        password = formData.get("password")
        print(userName)
        print(password)
        auth = None
        with open("./authDB.json") as fp:
            auth = json.load(fp)
            if auth == None:
                return "Error loading database", 205
            profiles = auth.get("profiles")
            if profiles:
                for profile in profiles:
                    if profile.get("username") == userName:
                        if profile.get("password") == password:
                            session['user_profile'] = profile
                            return jsonify(verified=True, message="user is verified"), 200
                        else:
                            return (
                                jsonify(
                                    verified=False,
                                    message="user is not verified. Wrong credentials",
                                ),
                                206,
                            )
                return (
                    jsonify(
                        verified=False,
                        message="user is not verified. Wrong credentials - 2",
                        redirectTo="login",
                    ),
                    206,
                )
    return "from login get route", 200


def calculateAge(birthDate):
    today = datetime.date.today()
    age = today.year - birthDate.year - \
        ((today.month, today.day) < (birthDate.month, birthDate.day))
    return age


def normalizeGender(gender):
    cs = {"female": 0, "male": 1}
    return cs.get(gender)


@app.route('/api/signup', methods=['POST'])
def signUp():
    user = request.get_json()
    print(user)
    # try:
    newUser = auth.create_user(email=user['email'], email_verified=False, phone_number=user['phNo'],
                               password=user['password'], display_name=user['dn'], disabled=False)

    userData = {"height": user['height'], 'weight': user['weight'],
                'age': calculateAge(user['birthDate']), 'gender': normalizeGender(user['gender'])}
    db.collection(u'userProfiles').document(f"{newUser.uid}").set(userData)
    return jsonify({"status": "success"})

    # except:
    #     return jsonify({"status": "failed"})


@app.route('/api/sessionLogin', methods=['POST'])
def session_login():
    # Get the ID token sent by the client
    id_token = request.json['idToken']
    # Set session expiration to 5 days.
    expires_in = datetime.timedelta(days=5)
    try:
        # Create the session cookie. This will also verify the ID token in the process.
        # The session cookie will have the same claims as the ID token.
        session_cookie = auth.create_session_cookie(
            id_token, expires_in=expires_in)
        response = jsonify({'status': 'success'})
        # Set cookie policy for session cookie.
        expires = datetime.datetime.now() + expires_in
        response.set_cookie(
            'session', session_cookie, expires=expires, httponly=True, secure=True)
        return response
    except exceptions.FirebaseError:
        return abort(401, 'Failed to create a session cookie')


def verify_cookie(userCookie):
    return auth.verify_session_cookie(
        userCookie, check_revoked=True)


@app.route('/api/verify_cookie')
def verify_cookie_from_web():
    userCookie = request.cookies.get('session')
    dc = verify_cookie(userCookie)
    if(dc):
        return {"verified": True}
    return {"verified": False}


@app.route("/api/predict_glucose", methods=["POST"])
def predictGlucose():
    userData = {}
    userData["Diastolic BP"] = int(request.form.get("diastole"))
    userData["Systolic BP"] = int(request.form.get("sistole"))
    userCookie = request.cookies.get('session')
    uid = request.form.get("uid")
    try:
        decoded_claims = verify_cookie(userCookie)
        doc_ref = db.document('userProfiles/'+uid)
        userDoc = doc_ref.get()
        if userDoc.exists:
            userFields = userDoc.to_dict()
            userHeight = userFields.get("height")
            userWeight = userFields.get("weight")
            userAge = int(userFields.get("age"))
            userGender = normalizeGender(userFields.get("gender"))

            gluco_Modal = pickle.load(open('glucoseModel.pkl', 'rb'))
            tempData = [("age", userAge), ("gender", userGender),
                        ("height", userHeight), ("weight", userWeight)]
            userData.update(tempData)
            x_predict = pd.DataFrame(userData, index=[0])

            if gluco_Modal != None:
                prediction = gluco_Modal.predict(x_predict), 200
                glucoseValue = prediction[0][0]
                print(glucoseValue)

                time = datetime.datetime.now().__str__().split(" ")
                time[1] = time[1].split(".")[0]

                doc_ref.collection('glucose_trends').document(
                    time[0]).update({time[1]: glucoseValue})
                doc_ref.collection('bp_trends').document(
                    time[0]).update({time[1]: {"diastole": userData["Diastolic BP"], "systole": userData["Systolic BP"]}})

                return jsonify(prediction="success", glucosePrediction=glucoseValue), 200
            return "NO modal to load", 204
        return "Error accessing store", 204
    except auth.InvalidSessionCookieError:
        # Session cookie is invalid, expired or revoked. Force user to login.
        return jsonify({'status': 'Failed', 'message': 'Session cookie is invalid, expired or revoked. Force user to login'})


@app.route('/api/session_logout')
@cross_origin()
def session_logout():
    response = jsonify({'message': "Logged out successfully"})
    response.set_cookie(
        'session', expires=datetime.datetime.now() - datetime.timedelta(days=10))
    return response


@app.route("/api/predict_colestrol")
def predictColestrol():
    userData = {}
    userData["dist"] = int(request.args.get('diastole'))
    userData["sist"] = int(request.args.get('systole'))
    up = session["user_profile"]
    up.pop('username')
    up.pop('password')
    userData.update(up)
    print("ud: ", userData)
    x_predict = pd.DataFrame(userData, index=[0])

    cs = {"female": 0, "male": 1}
    x_predict["gender"] = x_predict["gender"].map(cs)

    col_Modal = pickle.load(open('colestrolModel.pkl', 'rb'))

    if col_Modal != None:
        prediction = col_Modal.predict(x_predict), 200
        print(prediction[0][0])
        return jsonify(prediction="success", colestrolPrediction=prediction[0][0]), 200
    return "NO modal to load", 204


if __name__ == "__main__":
    app.secret_key = "THISKEYISSUPERSECRET"
    app.run(debug=True, load_dotenv=True,)

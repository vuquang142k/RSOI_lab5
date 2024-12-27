from flask import Flask, request, make_response, jsonify, Response
import uuid
import json
import datetime
import requests
import os

from authlib.integrations.flask_client import OAuth
import jwt

import os
from peewee import *
from peewee import Model, PostgresqlDatabase

####### БД #######
pg_db = PostgresqlDatabase(
    os.getenv('DATA_BASE_NAME'),
    user=os.getenv('DATA_BASE_USER'),
    password=os.getenv('DATA_BASE_PASS'),
    host=os.getenv('DATA_BASE_HOST'),
    port=int(os.getenv('DATA_BASE_PORT'))
)

class BaseModel(Model):
    class Meta:
        database = pg_db

class RentalModel(BaseModel):
    id = IdentityField()
    rental_uid = UUIDField(unique=True, null=False)
    username = CharField(max_length=80, null=False)
    payment_uid = UUIDField(null=False)
    car_uid = UUIDField(null=False)
    date_from = DateField(null=False, formats='%Y-%m-%d')
    date_to = DateField(null=False, formats='%Y-%m-%d')
    status = CharField(max_length=20, constraints=[Check("status IN ('IN_PROGRESS', 'FINISHED', 'CANCELED')")])

    def to_dict(self):
        return {
            "rentalUid": str(self.rental_uid),
            "username": str(self.username),
            "paymentUid": str(self.payment_uid),
            "carUid": str(self.car_uid),
            "dateFrom": str(self.date_from),
            "dateTo": str(self.date_to),
            "status": str(self.status)
        }

    class Meta:
        db_table = "rental"

####### создание таблицы в БД #######
def create_tables():
    RentalModel.drop_table()
    RentalModel.create_table()

####### описание маршрутов #######
app = Flask(__name__)

def get_signing_key(jwt_token):
    jwks_url = "https://dev-268y6str0e3mrg1n.us.auth0.com/.well-known/jwks.json"
    response = requests.get(jwks_url)
    jwks = response.json()
    header = jwt.get_unverified_header(jwt_token)
    kid = header.get("kid")
    
    for key in jwks["keys"]:
        if key["kid"] == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    
    raise ValueError("No matching key found in JWKS")

def check_jwt(bearer):
    try:
        jwt_token = bearer.split()[1]
        signing_key = get_signing_key(jwt_token)
        data = jwt.decode(
            jwt_token,
            signing_key,
            algorithms=["RS256"],
            audience="https://dev-268y6str0e3mrg1n.us.auth0.com/api/v2/",
            options={"verify_exp": False}
        )
        return data["name"]
    except:
        return False

#пустой маршрут
@app.route("/")
def service():
    return "RENTAL"

#маршрут get
@app.route('/api/v1/rental/<string:rentalUid>', methods=['GET'])
def get_rental(rentalUid):
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
        
    try:
        rental = RentalModel.select().where(RentalModel.rental_uid == rentalUid).get().to_dict()

        response = make_response(jsonify(rental))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'
        
        return response

#маршрут gets
@app.route('/api/v1/rental', methods=['GET'])
def get_rentals():
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
    
    rentals = [rental.to_dict() for rental in RentalModel.select().where(RentalModel.username == client)]
    
    response = make_response(jsonify(rentals))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
    
    return response

#маршрут post
def validate_body(body):
    try:
        body = json.loads(body)
    except:
        return None, ['wrong']

    errors = []
    
    if ('carUid' not in body or type(body['carUid']) is not str) or ('dateFrom' not in body or type(body['dateFrom']) is not str) or ('dateTo' not in body or type(body['dateTo']) is not str) or ('paymentUid' not in body or type(body['paymentUid']) is not str):
        return None, ['Bad structure body!']

    return body, errors

@app.route('/api/v1/rental', methods=['POST'])
def post_rental():
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)

    body, errors = validate_body(request.get_data())

    if len(errors) > 0:
        
        response = make_response(jsonify(errors))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response

    rental = RentalModel.create(
        rental_uid=uuid.uuid4(),
        username=client,
        car_uid=uuid.UUID(body['carUid']),
        date_from=datetime.datetime.strptime(body['dateFrom'], "%Y-%m-%d").date(),
        date_to=datetime.datetime.strptime(body['dateTo'], "%Y-%m-%d").date(),
        payment_uid=uuid.UUID(body['paymentUid']),
        status='IN_PROGRESS'
    )

    response = make_response(jsonify(rental.to_dict()))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
    
    return response

#маршрут post finish
@app.route('/api/v1/rental/<string:rentalUid>/finish', methods=['POST'])
def post_rental_finish(rentalUid):
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
        
    try:
        rental = RentalModel.select().where(RentalModel.rental_uid == rentalUid).get()
        
        if rental.status != 'IN_PROGRESS':
            response = make_response(jsonify({'errors': ['rental not in progres']}))
            response.status_code = 403
            response.headers['Content-Type'] = 'application/json'
        
            return response

        rental.status = 'FINISHED'
        rental.save()

        response = make_response(jsonify(rental.to_dict()))
        response.status_code = 204
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except Exception as e:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'

        return response
    
#маршрут delete
@app.route('/api/v1/rental/<string:rentalUid>', methods=['DELETE'])
def delete_rental(rentalUid):
    bearer = request.headers.get('Authorization')
    
    if bearer == None:
        return Response(status=401)
    
    client = check_jwt(bearer)

    if not(client):
        return Response(status=401)
        
    try:
        rental = RentalModel.select().where(RentalModel.rental_uid == rentalUid).get()
        
        if rental.status != 'IN_PROGRESS':
            response = make_response(jsonify({'errors': ['rental not in progres']}))
            response.status_code = 403
            response.headers['Content-Type'] = 'application/json'
        
            return response

        rental.status = 'CANCELED'
        rental.save()

        response = make_response(jsonify(rental.to_dict()))
        #response = make_response(jsonify({'message': 'Rental canceled'}))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except Exception as e:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'

        return response

#маршрут health check
@app.route('/manage/health', methods=['GET'])
def health_check():
    response = make_response(jsonify({'status': 'OK'}))
    response.status_code = 200
    
    return response

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=8060)

import uuid
import json

from peewee import *
from peewee import Model, PostgresqlDatabase

from flask import Flask, request, make_response, jsonify, Response 
import requests 
import datetime 
import json 
import os 
  
from authlib.integrations.flask_client import OAuth 
import jwt

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

class PaymentModel(BaseModel):
    id = IdentityField()
    payment_uid = UUIDField(null=False)
    status = CharField(max_length=20, constraints=[Check("status IN ('PAID', 'CANCELED')")])
    price = IntegerField(null=False)

    def to_dict(self):
        return {
            "paymentUid": str(self.payment_uid),
            "status": str(self.status),
            "price": self.price,
        }

    class Meta:
        db_table = "payment"

####### создание таблицы в БД #######
def create_tables():
    PaymentModel.drop_table()
    PaymentModel.create_table()

####### описание сервиса #######
app = Flask(__name__)

# подключение OAuth
app.config['JSON_AS_ASCII'] = False
#app.secret_key = os.environ['APP_SECRET_KEY']

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id='2tzOe8ODXk00x0wmzA8RoWhSR552QD8f',
    client_secret='YZIJUrFjzqlozGrRLT7eGx3gjrBjGVW1sJ8jcCcwE1wswL4d8rN42QpfwpfPQC6o',
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://dev-268y6str0e3mrg1n.us.auth0.com/.well-known/openid-configuration",
)

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
    return "PAYMENT"

#маршрут get
@app.route('/api/v1/payment/<string:paymentUid>', methods=['GET'])
def get_payment(paymentUid):
    bearer = request.headers.get('Authorization') 
  
    if bearer == None: 
        return Response(status=401) 
  
    client = check_jwt(bearer) 
  
    if not(client): 
        return Response(status=401)
    
    try:
        payment = PaymentModel.select().where(PaymentModel.payment_uid == paymentUid).get().to_dict()

        response = make_response(jsonify(payment))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'
        
        return response

#маршрут post
def validate_body(body):
    try:
        body = json.loads(body)
    except:
        return None, ['Error']

    errors = []
    if 'price' not in body.keys() or type(body['price']) is not int:
        return None, ['wrong structure']

    return body, errors

@app.route('/api/v1/payment', methods=['POST'])
def post_payment():
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

    payment = PaymentModel.create(payment_uid=uuid.uuid4(), price=body['price'], status='PAID')

    response = make_response(jsonify(payment.to_dict()))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
    
    return response

#маршрут delete
@app.route('/api/v1/payment/<string:paymentUid>', methods=['DELETE'])
def delete_payment(paymentUid):
    bearer = request.headers.get('Authorization') 
  
    if bearer == None: 
        return Response(status=401) 
  
    client = check_jwt(bearer) 
  
    if not(client): 
        return Response(status=401)
        
    try:
        payment = PaymentModel.select().where(PaymentModel.payment_uid == paymentUid).get()
        
        payment.status = 'CANCELED'
        payment.save()

        response = make_response(jsonify(payment.to_dict()))
        #response = make_response(jsonify({'message': 'Payment canceled'}))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
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
    app.run(host='0.0.0.0', port=8050)

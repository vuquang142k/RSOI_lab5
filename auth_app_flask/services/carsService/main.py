import os
from peewee import *
from peewee import Model, PostgresqlDatabase
from flask import Flask, request, make_response, jsonify, Response 
import requests 
import datetime 
import json 
  
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

class CarsModel(BaseModel):
    id = IdentityField()
    car_uid = UUIDField(unique=True, null=False)
    brand = CharField(max_length=80, null=False)
    model = CharField(max_length=80, null=False)
    registration_number = CharField(max_length=20, null=False)
    power = IntegerField()
    price = IntegerField(null=False)
    availability = BooleanField(null=False)
    type = CharField(max_length=20, constraints=[Check("type IN ('SEDAN', 'SUV', 'MINIVAN', 'ROADSTER')")])

    def to_dict(self):
        return {
            "carUid": str(self.car_uid),
            "brand": str(self.brand),
            "model": str(self.model),
            "registrationNumber": str(self.registration_number),
            "power": self.power,
            "type": str(self.type),
            "price": self.price,
            "available": bool(self.availability)
        }

    class Meta:
        db_table = "cars"

####### создание таблицы в БД #######
def create_tables():
    CarsModel.drop_table()
    CarsModel.create_table()

    CarsModel.get_or_create(
        id=1,
        car_uid="109b42f3-198d-4c89-9276-a7520a7120ab",
        brand="Mercedes Benz",
        model="GLA 250",
        registration_number="ЛО777Х799",
        power=249,
        type="SEDAN",
        price=3500,
        availability=True
    )

####### описание маршрутов #######
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
    return "CARS"

#маршрут get
@app.route('/api/v1/cars/<string:carUid>', methods=['GET'])
def get_car(carUid):
    bearer = request.headers.get('Authorization') 
  
    if bearer == None: 
        return Response(status=401) 
  
    client = check_jwt(bearer) 
  
    if not(client): 
        return Response(status=401)
         
    try:
        car = CarsModel.select().where(CarsModel.car_uid == carUid).get().to_dict()

        response = make_response(jsonify(car))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'
        
        return response

#маршрут gets
def validate_args(args):
    errors = []
    if 'page' in args.keys():
        try:
            page = int(args['page'])
            if page <= 0:
                errors.append('wrong page number')
        except ValueError:
            errors.append('page should be a number')
            page = None
    else:
        errors.append('enter page number')
        page = None

    if 'size' in args.keys():
        try:
            size = int(args['size'])
            if size <= 0:
                errors.append('wrong size number')
        except ValueError:
            size = None
            errors.append('Size should be a number')
    else:
        errors.append('enter size number')
        size = None

    if 'showAll' in args.keys():
        if args['showAll'].lower() == 'true':
            show_all = True
        elif args['showAll'].lower() == 'false':
            show_all = False
        else:
            errors.append('showAll must be true or false')
            show_all = None
    else:
        show_all = False

    return page, size, show_all, errors

@app.route('/api/v1/cars', methods=['GET'])
def get_cars():
    bearer = request.headers.get('Authorization') 
  
    if bearer == None: 
        return Response(status=401) 
  
    client = check_jwt(bearer) 
  
    if not(client): 
        return Response(status=401)
         
    page, size, show_all, errors = validate_args(request.args)

    if len(errors) > 0:
        response = make_response(jsonify({'errors': errors}))
        response.status_code = 400
        response.headers['Content-Type'] = 'application/json'
        
        return response

    if not show_all:
        query = CarsModel.select().where(CarsModel.availability == True)
        count_total = query.count()
        cars = [car.to_dict() for car in query.paginate(page, size)]
    else:
        count_total = CarsModel.select().count()
        cars = [car.to_dict() for car in CarsModel.select().paginate(page, size)]
    
    response = make_response(jsonify({"page": page, "pageSize": size, "totalElements": count_total, "items": cars}))
    response.status_code = 200
    response.headers['Content-Type'] = 'application/json'
        
    return response
    
#маршрут post
@app.route('/api/v1/cars/<string:carUid>/order', methods=['POST'])
def post_car_order(carUid):
    bearer = request.headers.get('Authorization') 
  
    if bearer == None: 
        return Response(status=401) 
  
    client = check_jwt(bearer) 
  
    if not(client): 
        return Response(status=401)
         
    try:
        car = CarsModel.select().where(CarsModel.car_uid == carUid).get()
        
        if car.availability is False:
            response = make_response(jsonify({'errors': ['Car is booked']}))
            response.status_code = 403
            response.headers['Content-Type'] = 'application/json'
        
            return response
        
        car.availability = False
        car.save()

        response = make_response(jsonify(car.to_dict()))
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        
        return response
    except:
        response = make_response(jsonify({'errors': ['No Uid']}))
        response.status_code = 404
        response.headers['Content-Type'] = 'application/json'
        
        return response

#маршрут delete
@app.route('/api/v1/cars/<string:carUid>/order', methods=['DELETE'])
def delete_car_order(carUid):
    bearer = request.headers.get('Authorization') 
  
    if bearer == None: 
        return Response(status=401) 
  
    client = check_jwt(bearer) 
  
    if not(client): 
        return Response(status=401)
         
    try:
        car = CarsModel.select().where(CarsModel.car_uid == carUid).get()
        
        if car.availability is True:
            response = make_response(jsonify({'errors': ['Car not requested']}))
            response.status_code = 403
            response.headers['Content-Type'] = 'application/json'
        
            return response
        
        car.availability = True
        car.save()

        response = make_response(jsonify({'status': 'OK'}))
        response.status_code = 200
        
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
    app.run(host='0.0.0.0', port=8070)

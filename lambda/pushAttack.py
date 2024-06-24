import os
import json
#from bson import json_util
from pymongo import MongoClient
import random
from datetime import datetime, timedelta
import boto3

lambda_client = boto3.client('lambda')
function_arn = 'updatePostAttackStats'
client = boto3.client('apigatewaymanagementapi', endpoint_url="https://xxxxxxxxxxxxxxxx.us-east-1.amazonaws.com/production")



# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None

def connect_to_database(uri):
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('=> using cached database instance')
        return cached_db
    client = MongoClient(uri)
    print(client)
    cached_db = client.test 
    #db = client['test']
    return cached_db

def get_controls_data(db):
    # Assuming there's only one document in control_data collection
    document = db.controls_data.find_one()
    controls_data = document['info']['controls']
    return controls_data

def get_attack_data(db):
    # Assuming there's only one document in control_data collection
    attacks_document = db.attacks.find_one()
    #print(user_document)
    if attacks_document:
        attacks_document.pop('_id', None)
    else:
        attacks_document = {}
    return attacks_document

    

    
def random_threat(threats, excluded_threats):
    available_threats = {k: v for k, v in threats.items() if v['name'] not in excluded_threats}
    if not available_threats:
        return None, None  # Indicates no available threats not in excluded list
    random_threat_key = random.choice(list(available_threats.keys()))
    #return available_threats[random_threat_key]['name'], random_threat_key
    #random_threat_key = 't6'
    return available_threats, random_threat_key


def get_all_threats(db):
    document = db.threats.find_one()
    if document and 'threats' in document:
        return document['threats']
    else:
        return {}
    
def get_game_status(db):
    document = db.game_status.find_one()
    if document:
        game_status = document.get('started', "No data")
        if game_status == "No data":
            print('game_status collection does not have any data')
            return False
        else:
            return document
    else:
        print('game_status collection is not found in DB')
        return False

def get_connection_id(db):
    document = db.connection_id.find_one()
    connectionId_doc = document.get('connection_id', False)
    
    connection_ids = [connection for connection in connectionId_doc.values()]
    if connection_ids:
        return connection_ids
    else:
        return "Not Found"
    
# Function to post messages to all connections
def post_to_all_connections(connection_ids, controls_with_cost):
    for connection_id in connection_ids:
        response = client.post_to_connection(
            ConnectionId=connection_id, 
            Data=json.dumps(controls_with_cost).encode('utf-8')
        )
        print(f"Message sent to {connection_id}, response: {response}")


def push_attack_websocket(db, attack):
    connection_ids = get_connection_id(db)
    if connection_ids == "Not Found":
        print('Could not find the connectionIDs in the system...')
        return 

    attack_to_push = json.dumps(attack).encode('utf-8')

    stale_connection_ids = []
    for connection_id in connection_ids:
        try:
            client.post_to_connection(
                ConnectionId=connection_id,
                Data=attack_to_push
            )
        except client.exceptions.GoneException:
            # If a GoneException is caught, the connection is stale.
            stale_connection_ids.append(connection_id)
    
    print(f'list of stale connections: {stale_connection_ids}')

    #post_to_all_connections(connection_ids, attack)
    print('=> returning result: ', attack)
    return

def stop_game(db):
    try:
        collection = db['game_status']
        # update query
        update_query = {
                        '$set': {
                            "started": "False",
                            "stop_timestamp": datetime.utcnow(),
                            "update_attack_stats": "False"
                        }
                    }
        collection.update_one({}, update_query, upsert=True)
        return
    except Exception as e:
            print(f'Stop Game flag is failed to set in DB')
            return


def lambda_handler(event, context):
    print('event: ', event)

    #cognito_username = event['requestContext']['authorizer']['claims']['username']
    #user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)
    #user_id = 'dummyuser1'



    # Extract the path from the event
    db = connect_to_database(MONGODB_URI)
    #user_id = "3" # Replace with actual user ID
    game_status_data = get_game_status(db)
    if game_status_data:
        game_status = game_status_data.get('started', "No Data")
        print(f'game_status: {game_status}')
    else:
        return
    if game_status == "No Data" or game_status == "False":
        print('Game has not been started by Admin')
        return
    threshold_time = datetime.utcnow() - timedelta(minutes=5)
    game_start_time = game_status_data.get('start_timestamp', datetime.utcnow())
    if game_start_time >= threshold_time:
        print('Game start time is less than the set threshold time of 2 mins')
        return

    attack_data = get_attack_data(db)

    print(f'attack_data:{attack_data}')

    # threat_name, threat_key = random_threat(db)
    # print (threat_name)
    #threat_list = set(user_data.get("threats", []))  # Convert list to set for efficiency
    #threat_list = set([threat.get("name") for threat in attack_data if threat.get("name") is not None])
    attack_list = set([attack.get("name") for attack in attack_data.get('attacks_taken_place', {}) if attack.get("name") is not None])
    print(f"attack_list:{attack_list}")
    all_threats = get_all_threats(db)
    while True:
        available_threats, threat_key = random_threat(all_threats, attack_list)
        #[random_threat_key]['name']
        if available_threats is None:
            print("All the available attacks are simulated")
            attack = {
                "attack": "Game has ended." }
            push_attack_websocket(db, attack)
            stop_game(db)
            return
        else:
            print(f"Selected threat: {available_threats[threat_key]['name']} (Key: {threat_key})")
            break 
    
    
    
    response = update_attack_in_database(db, available_threats, threat_key)

    if response in ['Update to DB failed', 'update_attack_stats flag is failed to set in DB']:
        return
    
    attack = {
        "attack": available_threats[threat_key]['name']
    }
    
    push_attack_websocket(db, attack)
    # connection_ids = get_connection_id(db)
    # if connection_ids == "Not Found":
    #     print('Could not find the connectionIDs in the system...')
    
    # attack = {
    #     "attack": available_threats[threat_key]['name']
    # }

    # attack_to_push = json.dumps(attack).encode('utf-8')

    # stale_connection_ids = []
    # for connection_id in connection_ids:
    #     try:
    #         client.post_to_connection(
    #             ConnectionId=connection_id,
    #             Data=attack_to_push
    #         )
    #     except client.exceptions.GoneException:
    #         # If a GoneException is caught, the connection is stale.
    #         stale_connection_ids.append(connection_id)
    
    # print(f'list of stale connections: {stale_connection_ids}')

    # #post_to_all_connections(connection_ids, attack)
    # print('=> returning result: ', attack)

        
    function_input = {"attack_name": available_threats[threat_key]['name'], 
                      "attack_down_time": available_threats[threat_key]['downtime'], 
                      "attack_key":threat_key
                      }
    # Convert the payload dictionary to a JSON string format
    function_input_str = json.dumps(function_input)
    response = lambda_client.invoke(
                            FunctionName=function_arn,
                            InvocationType='Event',  # Set to 'Event' for asynchronous execution
                            Payload=function_input_str.encode('utf-8')  # Convert string payload to bytes 
                            )

    # The response from an asynchronous invoke does not contain the function's response
    # It will include a status code and function ARN if the request was successful
    print('Status Code:', response['StatusCode'])
    print('response', response)
    print('=> returning from  mainfunction ')
    return


#current_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def update_attack_in_database(db, available_threats, threat_key):
    try:
        db.attacks.update_one(
        {}, 
        {
            '$push': {  # Use '$push' to add to an array
                'attacks_taken_place': {  #
                    'name': available_threats[threat_key]['name'],  # The new element
                    "timestamp": datetime.utcnow()
                }
            }
        }
    ,upsert=True)
    except Exception as e:
            # Handle exceptions and possible S3 errors or MongoDB deletion errors
            print(f'Attack update to the DB failed')
            return "Update to DB failed"
    
    try:
        collection = db['game_status']
        update_query = {
                        '$set': {
                            "update_attack_stats": "True",
                        }
                    }
        collection.update_one({}, update_query, upsert=True)
        return 'update_attack_stats flag is set successfully'
    except Exception as e:
            print(f'update_attack_stats flag is failed to set in DB')
            return 'update_attack_stats flag is failed to set in DB'
    
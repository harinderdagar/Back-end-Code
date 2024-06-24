import os
import json
from pymongo import MongoClient
import random
from datetime import datetime, timedelta
import boto3

client = boto3.client('apigatewaymanagementapi', endpoint_url="https://xxxxxxxxxxxxxx.us-east-1.amazonaws.com/production")



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


def get_past_situations_data(db):
    # Assuming there's only one document in control_data collection
    past_situations_document = db.past_situations.find_one()
    #print(user_document)
    if past_situations_document:
        past_situations_document.pop('_id', None)
    else:
        past_situations_document = {}
    return past_situations_document

    

    
def random_situation(all_situations, past_situations_list):
    available_situations = {k: v for k, v in all_situations.items() if k not in past_situations_list}
    if not available_situations:
        return None, None  # Indicates no available situations not in excluded list
    available_situations_key = random.choice(list(available_situations.keys()))
    #return available_threats[random_threat_key]['name'], random_threat_key
    #random_threat_key = 't6'
    return available_situations, available_situations_key


def get_all_situations(db):
    document = db.situations.find_one()
    if document and 'situations' in document:
        return document['situations']
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
    


def push_situation_websocket(db, situation):
    connection_ids = get_connection_id(db)
    if connection_ids == "Not Found":
        print('Could not find the connectionIDs in the system...')
        return 

    situation_to_push = json.dumps(situation).encode('utf-8')

    stale_connection_ids = []
    for connection_id in connection_ids:
        try:
            client.post_to_connection(
                ConnectionId=connection_id,
                Data=situation_to_push
            )
        except client.exceptions.GoneException:
            # If a GoneException is caught, the connection is stale.
            stale_connection_ids.append(connection_id)
    
    print(f'list of stale connections: {stale_connection_ids}')

    print('=> returning result: ', situation)
    return



def update_situation_in_database(db, available_situations_key):
    try:
        db.attacks.update_one(
        {},  
        {
            '$push': {  # Use '$push' to add to an array
                'situations_taken_place': {  
                    'situation_id': available_situations_key,  # The new element
                    "timestamp": datetime.utcnow()
                }
            }
        }
    ,upsert=True)
    except Exception as e:
            print(f'Situation update to the DB failed')
            return "Update to DB failed"
    
def lambda_handler(event, context):
    # Handler for AWS Lambda: processes the event and executes game logic
    print('event: ', event)

    # Establish database connection
    db = connect_to_database(MONGODB_URI)

    # Check current game status from database
    game_status_data = get_game_status(db)
    if not game_status_data:
        return  # Exit if game status is not found

    # Extract game status and check if the game has been started
    game_status = game_status_data.get('started', "No Data")
    if game_status in ["No Data", "False"]:
        print('Game has not been started by Admin')
        return

    # Define time thresholds for checking the attack timing
    threshold_time_1 = datetime.utcnow() - timedelta(minutes=2)
    threshold_time_2 = datetime.utcnow() - timedelta(minutes=3)
    attack_time = game_status_data.get('attack_timestamp', datetime.utcnow())

    # Validate if the current attack time is within the specified window
    if not (threshold_time_2 <= attack_time < threshold_time_1):
        print('Game attack time is not within 2 and 3 mins')
        return

    # Retrieve past situations and prepare for new situation selection
    past_situations_data = get_past_situations_data(db)
    past_situations_list = set(situation.get("situation_id") for situation in past_situations_data.get('situations_taken_place', {}))
    all_situations = get_all_situations(db)

    # Randomly select a new situation that has not occurred yet
    while True:
        available_situations, available_situations_key = random_situation(all_situations, past_situations_list)
        if available_situations is None:
            print("All available situations are simulated")
            return
        print(f"Selected situation: (Key: {available_situations_key})")
        break 

    # Update the situation in database and push to WebSocket
    response = update_situation_in_database(db, available_situations_key)
    if response in ['Update to DB failed', 'Situation could not be updated into DB, not pushing the situation to the users...']:
        return

    # Define the situation to push
    situation = {"situation": available_situations[available_situations_key]}
    push_situation_websocket(db, situation)
    print('=> returning from main function')
    return
import os
import json
from pymongo import MongoClient
import boto3


# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None
initial_budget = 15000
client = boto3.client('apigatewaymanagementapi', endpoint_url="https://xxxxxxxxxxxxxx.us-east-1.amazonaws.com/production")



def connect_to_database(uri):
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('=> using cached database instance')
        return cached_db
    client = MongoClient(uri)
    print(client)
    cached_db = client.test  
    return cached_db


def get_controls_data(db):
    document = db.controls_data.find_one()
    controls_data = document['info']['controls']
    response_controls = {key: {'control': value['control'], 'cost': value['cost']}
                        for key, value in controls_data.items()}
    return response_controls

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


# def lambda_handler(event, context):
#     print('event: ', event)
    
#     db = connect_to_database(MONGODB_URI)
#     #user_id = "3" # Replace with actual user ID
#     connection_ids = get_connection_id(db)
#     if connection_ids == "Not Found":
#         print('Could not find the connectionIDs in the system...')
#         return

#     response_controls = get_controls_data(db)
    
#     controls_with_cost = {
#         "budget": initial_budget,
#         "controls": response_controls
#     }

#     # Send the message
#     post_to_all_connections(connection_ids, controls_with_cost)
#     print('=> returning result: ', controls_with_cost)


def lambda_handler(event, context):
    print('event: ', event)
    
    db = connect_to_database(MONGODB_URI)
    #user_id = "3" # Replace with actual user ID
    connection_ids = get_connection_id(db)
    if connection_ids == "Not Found":
        print('Could not find the connectionIDs in the system...')
        return

    response_controls = get_controls_data(db)
    
    controls_with_cost = {
        "budget": initial_budget,
        "controls": response_controls
    }

    # Serialize to JSON and encode to bytes
    controls_to_push = json.dumps(controls_with_cost).encode('utf-8')

    stale_connection_ids = []
    for connection_id in connection_ids:
        try:
            client.post_to_connection(
                ConnectionId=connection_id,
                Data=controls_to_push
            )
        except client.exceptions.GoneException:
            # If a GoneException is caught, the connection is stale.
            stale_connection_ids.append(connection_id)
    
    print(f'list of stale connections: {stale_connection_ids}')
    print('=> returning result: ', controls_with_cost)
import json
from pymongo import MongoClient
import os
from datetime import datetime
import boto3

# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None

lambda_client = boto3.client('lambda')
function_arn = 'pushControls'


def return_success(response_data):
    return {
            'statusCode': 200,
            #'headers': { 'Content-Type': 'application/json' },
            'headers': {
            'Access-Control-Allow-Origin': '*',  # Allows requests from any origin
            'Access-Control-Allow-Methods': 'GET',  # Adjust as needed
            'Access-Control-Allow-Headers': 'Content-Type',  # Adjust as needed
            'Content-Type': 'application/json'
            },
            
            'body': json.dumps(response_data)
        }

def return_error(status_code, error):
    return {
            'statusCode': status_code,
            #'headers': { 'Content-Type': 'application/json' },
            'headers': {
            'Access-Control-Allow-Origin': '*',  # Allows requests from any origin
            'Access-Control-Allow-Methods': 'GET',  # Adjust as needed
            'Access-Control-Allow-Headers': 'Content-Type',  # Adjust as needed
            'Content-Type': 'application/json'
            },
            
            'body': json.dumps({'error': str(error)})
        }

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

#update start game time
def start_game(db):
    try:
        collection = db['game_status']
        update_query = {
                        '$set': {
                            "started": "True",
                            "start_timestamp": datetime.utcnow()
                        }
                    }
        collection.update_one({}, update_query, upsert=True)
        return return_success('Start Game flag is set successfully')
    except Exception as e:
            print(f'Start Game flag is failed to set in DB')
            return return_error(400, 'Start Game flag is failed to set in DB')

#update Stop game time   
def stop_game(db):
    try:
        collection = db['game_status']
        update_query = {
                        '$set': {
                            "started": "False",
                            "stop_timestamp": datetime.utcnow()
                        }
                    }
        collection.update_one({}, update_query, upsert=True)
        return return_success('Stop Game flag is set successfully')
    except Exception as e:
            print(f'Stop Game flag is failed to set in DB')
            return return_error(400, 'Stop Game flag is failed to set in DB')

    
def verify_admin_user(db, user_id):
    # Fetching admin user details from the database
    admin_users_db = db.adminUsers.find_one()  # Athere's only one document 
    admin_users = admin_users_db['users'] if admin_users_db else []
    # Check if user_id is in the list of admin users
    if user_id not in admin_users:
        # Return an error response if user_id is not found
        return return_error(400, "Invalid User")
    else:
        # If found, print a confirmation message
        print(f'Found user {user_id} in DB')



def lambda_handler(event, context):
    print(event)
    # Parse the incoming JSON payload from the event body   
    
    path = event.get('path')
    db = connect_to_database(MONGODB_URI)
    # user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)
    # print(f'{user_id} User in Token')
    # response = verify_admin_user(db, user_id)
    # if response:
    #     return response


    if path == '/startGame':

        if event.get('multiValueQueryStringParameters', {}):
            return return_error(400,f"unexpected query parameter") 
        
        response = start_game(db)
        function_input = {"invoke":"pushControls"
                      }
        # Convert the payload dictionary to a JSON string format
        function_input_str = json.dumps(function_input)
        lambda_response = lambda_client.invoke(
                                FunctionName=function_arn,
                                InvocationType='Event',  # Set to 'Event' for asynchronous execution
                                Payload=function_input_str.encode('utf-8')  # Convert string payload to bytes 
                                )
        print("invoked pushControls lambda function")
        print('Status Code:', lambda_response['StatusCode'])
        print('response', lambda_response)
        print('=> returning from  mainfunction ')

        return response
    
    elif path == '/stopGame':
        if event.get('multiValueQueryStringParameters', {}):
            return return_error(400,f"unexpected query parameter") 
        
        response = stop_game(db)
        return response


    
    else:
        return return_error(400,f"Endpoint not found")
import os
import json
from pymongo import MongoClient
from datetime import datetime

# Load MongoDB URI from environment variable
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None

def connect_to_database(uri):
    """ Connect to MongoDB using the URI, with caching to avoid multiple connections. """
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('=> using cached database instance')
        return cached_db
    try:
        client = MongoClient(uri)
        cached_db = client.test  # 'test' is the intended database
        print(client)
    except Exception as e:
        print(f"gameGetUserStats: Error connecting to database: {e}")
        raise
    return cached_db

def return_success(response_data):
    """ Return a success HTTP response with JSON body. """
    try:
        response_body = json.dumps(response_data, cls=CustomJSONEncoder)
    except Exception as e:
        return return_error(500, f"JSON Encoding Error: {e}")
    return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json'
            },
            'body': response_body
        }

def return_error(status_code, error):
    """ Return an error HTTP response with JSON body describing the error. """
    error_message = json.dumps({'error': str(error)})
    return {
            'statusCode': status_code,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json'
            },
            'body': error_message
        }

class CustomJSONEncoder(json.JSONEncoder):
    """ Custom JSON encoder for encoding datetime objects into ISO format. """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def get_user_stats(db, user_id):
    """ Fetch or create initial user stats based on the user ID. """
    try:
        user_data = db.usersData.find_one({"user_id": user_id})
    except Exception as e:
        print(f'gameGetUserStats: {user_id}- Database query failed. Error is {e}')
        return return_error(500, f"Internal Server error.")

    if not user_data:
        user_data = {"user_id": user_id, "initial_budget": 0, "player_start_time": "", "controls": [], "threats": [], "levels": {}}
    else:
        user_data.pop('_id', None)  # Remove MongoDB-specific '_id' field

    return return_success(user_data)

def lambda_handler(event, context):
    """ Lambda function handler processing HTTP requests. """
    print('event: ', event)
    #user_id = "dummyuser1"  # Dummy user ID for testing purposes
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)

    if user_id:
        path = event.get('path')
        try:
            db = connect_to_database(MONGODB_URI)
        except Exception as e:
            print(f'gameGetUserStats: Failed to connect to database. Error is {e}')
            return return_error(500, f"Internal Server error.")

        if path == '/getUserStats':
            if event.get('multiValueQueryStringParameters', {}):
                print(f'gameGetUserStats: {user_id} - Unexpected query parameter')
                return return_error(400, "Unexpected query parameter")
            response = get_user_stats(db, user_id)
        else:
            print(f'gameGetUserStats: {user_id} - Endpoint not found')
            response = return_error(403, "Endpoint not found")
    else:
        print(f'gameGetUserStats: UserID cannot be deduced from the API request token.')
        response = return_error(438, "UserID cannot be deduced from the API request.")

    print('=> returning result: ', response)
    return response
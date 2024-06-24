import os
import json
from pymongo import MongoClient
from datetime import datetime

# Retrieve MongoDB URI from environment variables
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None
initial_budget = 15000

def connect_to_database(uri):
    """Connect to the MongoDB database using the provided URI and cache the connection."""
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('gamePlay: using cached database instance')
        return cached_db
    try:
        client = MongoClient(uri)
        cached_db = client.test  #'test' is the database name
        return cached_db
    except Exception as e:
        print(f"gamePlay: Connection error: {e}")
        raise e

def return_success(response_data):
    """Return a success response with the provided data formatted as JSON."""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(response_data)
    }

def return_error(status_code, error):
    """Return an error response with the provided status code and error message."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'error': str(error)})
    }

def find_or_create_user_document(db, user_id, initial_budget):
    """Retrieve a user document from the database or create a new one if it doesn't exist."""
    try:
        user_data = db.usersData.find_one({"user_id": user_id})
        if not user_data:
            user_data = {"user_id": user_id, "initial_budget": initial_budget, "player_start_time": datetime.utcnow(), "controls": [], "threats": [], "levels": {}}
            db.usersData.insert_one(user_data)
            print(f"gamePlay: {user_id} has been registered in the game")
            return return_success(f"{user_id} has been registered in the game")
        else:
            return return_error(409, 'Your game state is present in the system. Please continue to play the game or contact admin')
    except Exception as e:
        print(f"gamePlay: Database error: {e}")
        return return_error(500, "Database operation failed")

def lambda_handler(event, context):
    """Handle incoming requests to the Lambda function."""
    global initial_budget
    print(f'gamePlay: event {event}')
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)
    if user_id:
        path = event.get('path')
        try:
            db = connect_to_database(MONGODB_URI)
            if path == '/play':
                if event.get('multiValueQueryStringParameters', {}):
                    return return_error(400, "Unexpected query parameter")
                response = find_or_create_user_document(db, user_id, initial_budget)
            else:
                response = return_error(403, "Endpoint not found")
        except Exception as e:
            print(f"gamePlay: Handler error: {e}")
            response = return_error(501, "Lambda function failed to execute")
    else:
        print(f'gamePlay: {user_id} UserID cannot be deduced from the API request')
        response = return_error(438, "UserID cannot be deduced from the API request")
        
    print('gamePlay: returning result: ', response)
    return response
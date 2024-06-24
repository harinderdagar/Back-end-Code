import os
import json
#from bson import json_util
from pymongo import MongoClient

# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None

def lambda_handler(event, context):
    print(event)
    print('*********************')
    print(context)
    return {"status_code": 200}

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


def return_success(response_data):
     return {
        'statusCode': 200,
        'body': json.dumps(response_data)
    }

def return_error(error_code, response_data):
     return {
        'statusCode': error_code,
        'body': json.dumps(response_data)
    }

def get_next_key(connection_id_doc):
    # This function returns the next key to be used for the new connection_id.
    # If connection_id_doc is None or doesn't have 'connection_id', it starts from "1".
    if connection_id_doc and 'connection_id' in connection_id_doc and connection_id_doc['connection_id']:
        max_key = max(map(int, connection_id_doc['connection_id'].keys()))
        next_key = str(max_key + 1)
    else:
        next_key = "1"
    print(f'next_key: {next_key}')
    return next_key


def add_connection_id(db, connection_id):
    # This function attempts to add a new connection_id to the database.
    try:
        # Access the collection; MongoDB creates it on the first insert/update.
        collection = db['connection_id']
        # Attempt to find one document in the collection.
        connection_id_doc = collection.find_one()
    except Exception as e:
        print(f'Cannot access collection connection_id: {e}')
        return return_error(400, 'Cannot access collection connection_id')
    
    try:
        # Generate the next key
        new_data_key = get_next_key(connection_id_doc)
        # Prepare the update query. If no documents exist, this operation will create one.
        update_query = {'$set': {f'connection_id.{new_data_key}': connection_id}}
        # Perform the update operation, creating a new document if none exist (upsert=True).
        collection.update_one({}, update_query, upsert=True)
        return return_success('connection_id is updated successfully')
    except Exception as e:
        print(f'connection_id update to DB failed: {e}')
        return return_error(400, 'connection_id update to DB failed')



def lambda_handler(event, context):
    # Extract the connection ID from the event
    connection_id = event['requestContext']['connectionId']
    #connection_id = event['requestContext']
    # Log the connection ID
    print(f"Received connection ID: {connection_id}")

    db = connect_to_database(MONGODB_URI)
    response = add_connection_id(db, connection_id)

    # Return a response, necessary for the API Gateway integration
    return response
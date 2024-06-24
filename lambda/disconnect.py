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
    cached_db = client.test  # 
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

def get_key(connection_id, connection_id_doc):
    # Traverse the dictionary
    connection_id_key = ""
    found = False  # Flag to indicate if the inner value has been found
    print(f'connection_id_doc:{connection_id_doc}')
    for key, inner_dict in connection_id_doc.items():
        print(f'value:{inner_dict}')
        for inner_key, inner_value in inner_dict.items():
            print(f'inner_key:{inner_key}')
            print(f'inner_value:{inner_value}')
            if inner_value == connection_id:
                connection_id_key = inner_key
                found = True  # Set the flag to True because the value has been found
                break  # Break out of the inner loop
        if found:
            break  # Break out of the outer loop if the flag is True
    print(f'connection_id_key: {connection_id_key}')
    return connection_id_key


def delete_connection_id(db, connection_id):
    # This function attempts to add a new connection_id to the database.
    try:
        # Access the collection; MongoDB creates it on the first insert/update.
        collection = db['connection_id']
        # Attempt to find one document in the collection.
        connection_id_doc = collection.find_one()
        if connection_id_doc:
            connection_id_doc.pop('_id', None)
    except Exception as e:
        print(f'Cannot access collection connection_id: {e}')
        return return_error(400, 'Cannot access collection connection_id')
    
    try:      
        # Generate the next key
        connection_id_key = get_key(connection_id, connection_id_doc)
        # Prepare the update query. If no documents exist, this operation will create one.
        update_query = {'$unset': {f'connection_id.{connection_id_key}': connection_id}}
        print(f'update_query:{update_query}')
        result = collection.update_one({}, update_query)
        print(f'result:{result}')
        if result.modified_count > 0:
            return return_success(f"Deleted {connection_id} from the DB.")
        else:
            return return_error(400, f"Error: in deleting the connection_id {connection_id} from the database.")
    except Exception as e:
        print(f'connection_id update to DB failed: {e}')
        return return_error(400, 'connection_id deletion from DB failed')



def lambda_handler(event, context):
    # Extract the connection ID from the event
    connection_id = event['requestContext']['connectionId']
    #connection_id = event['requestContext']
    # Log the connection ID
    print(f"Received connection ID: {connection_id}")

    db = connect_to_database(MONGODB_URI)
    response = delete_connection_id(db, connection_id)

    # Return a response, necessary for the API Gateway integration
    return response
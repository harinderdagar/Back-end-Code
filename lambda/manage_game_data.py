import json
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure


# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None


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
    try:
        cached_db = client.test
    except ConnectionFailure as e:
        print(f"Could not connect to MongoDB: {e}")
    
    #db = client['test']
    return cached_db


def verify_threats_id(db, effectiveness_keys):
    #threats_collection = db['threats']
    threats_document = db.threats.find_one()  # There's only one document 
    existing_threats = threats_document['threats'].keys() if threats_document else []
     # Validate provided threat IDs
    if not all(threat_id in existing_threats for threat_id in effectiveness_keys):
        # Return an error response
        return return_error(400,f"Provided threat IDs are invalid or do not exist, or first add the the threat id")
    

def verify_threat_name(db, data, threat_data):
    #threats_collection = db['threats']
    threat_name = threat_data.get('name', "")
    threat_key = list(data.keys())[0]
    print(f'threat_name: {threat_name}')
    threats_document = db.threats.find_one()
    existing_threats = threats_document['threats'].values() if threats_document else []
     # Validate provided threat IDs
    if any(threat_name.lower() == threat['name'].lower() for threat in existing_threats):
        # Return an error response
        return return_error(400,f"Provided threat name is already present in the DB...")
    
    existing_threats = threats_document['threats'].keys() if threats_document else []
    print(f'threat_key: {threat_key}')
    print(f'existing_threats: {existing_threats}')
    if threat_key in existing_threats:
        # Return an error response
        return return_error(400,f"Provided threat id is already present in the DB...")



def update_control_data(db, data, control_data):
    try:
        controls_collection = db['controls_data']
        update_query = {"$set": {f"info.controls.{list(data.keys())[0]}": control_data}}
        controls_collection.update_one({}, update_query, upsert=True)
        return return_success('Data updated successfully')
    except Exception as e:
            # Handle exceptions 
            print(f'Data update to DB failed')
            return return_error(400, 'Data cannot be found in DB')
    

def update_threat_data(db, data, threat_data):
    try:
        threats_collection = db['threats']
        update_query = {"$set": {f"threats.{list(data.keys())[0]}": threat_data}}
        threats_collection.update_one({}, update_query, upsert=True)
        return return_success('Data updated successfully')
    except Exception as e:
            # Handle exceptions 
            print(f'Data update to DB failed')
            return return_error(400, 'Data cannot be found in DB')
    
def get_controls_list(db):
    collection = db['controls_data']  
    # Fetch the document;
    controls_data = collection.find_one()
    
    
    if controls_data:
        controls_data.pop('_id', None) #exclude '_id'
        #json_str = json.dumps(controls_data, indent=4)
        return return_success(controls_data)
        #return return_success(json_str)
    else:
        return return_error(400, 'Data cannot be found in DB')
    

def get_threats_list(db):
    collection = db['threats']
    
    # Fetch the document;
    threats_data = collection.find_one()
    
    # Convert the document to JSON
    if threats_data:
        threats_data.pop('_id', None)
        #json_str = json.dumps(threats_data, indent=4)
        return return_success(threats_data)
    else:
        return return_error(400, 'Data cannot be found in DB')
    

def delete_threats(db, threat_ids):
    collection = db['threats']
    query = {'$or': [{f'threats.{threat_id}': {'$exists': True}} for threat_id in threat_ids]}

    # Check if the document exists
    document = collection.find_one(query)

    # If the document exists, delete the specified threats
    if document:
        update_query = {f'$unset': {f'threats.{threat_id}': "" for threat_id in threat_ids}}
        print(f'update_query:{update_query}')
        result = collection.update_one({}, update_query)
        print(f'result:{result}')
        if result.modified_count > 0:
            return return_success(f"Deleted {threat_ids} from the DB.")
        else:
            return return_error(400, f"Error: in deleting the threat_id(s) {threat_ids} from the database.")
    else:
        return return_error(400, f"Error: None of the specified threat_id(s) {threat_ids} exist in the database.")
    

def delete_controls(db, control_ids):
    collection = db['controls_data']
    query = {'$or': [{f'info.controls.{control_id}': {'$exists': True}} for control_id in control_ids]}

    # Check if the document exists
    document = collection.find_one(query)

    # If the document exists, delete the specified controls
    if document:
        update_query = {f'$unset': {f'info.controls.{control_id}': "" for control_id in control_ids}}
        print(f'update_query:{update_query}')
        result = collection.update_one({}, update_query)
        print(f'result:{result}')
        if result.modified_count > 0:
            return return_success(f"Deleted {control_ids} from the DB.")
        else:
            return return_error(400, f"Error: in deleting the control_id(s) {control_ids} from the database.")
    else:
        return return_error(400, f"Error: None of the specified control_id(s) {control_ids} exist in the database.")
    


def reset_game(db):
    operation_status = True
    try:
        db.drop_collection('users')
        print("Collection 'users' dropped successfully.")
    
    except OperationFailure as e:
        print(f"Error dropping collection 'users': {e}")
        operation_status = False
    
    # Attempt to drop the second collection
    try:
        db.drop_collection('attacks')
        print("Collection 'attacks' dropped successfully.")
    except OperationFailure as e:
        print(f"Error dropping collection 'attacks': {e}")
        operation_status = False
    
    try:
        collection = db['game_status']
        # Define update query
        update_query = {
                        '$set': {
                            "started": "False",
                            "stop_timestamp": datetime.utcnow(),
                            "update_attack_stats": "False"
                        }
                    }
        collection.update_one({}, update_query, upsert=True)
    except OperationFailure as e:
            print(f'Stop Game flag is failed to set in DB')
            operation_status = False

    return return_success("Game reset is successful") if operation_status else return_error(400, "Game reset failed...")

def verify_admin_user(db, user_id):
    # Fetching admin user details from the database
    admin_users_db = db.adminUsers.find_one()  # Assuming there's only one document as per the given structure
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
    

    if path == '/addControl':
        response = {}
        data = json.loads(event['body'])
        print(data) 
        control_data = data[list(data.keys())[0]]  # Extract the control data
        effectiveness_keys = control_data.get('effectiveness', {}).keys()  # Get threat IDs from effectiveness
        response = verify_threats_id(db, effectiveness_keys)
        if response:
            return response
        
        response = update_control_data(db, data, control_data)
        return response
    
    elif path == '/addThreat':
        data = json.loads(event['body'])
        threat_data = data[list(data.keys())[0]]
        print(data) 
        response = verify_threat_name(db, data, threat_data)
        if response:
            return response
        key = list(data.keys())[0]
        data[key]['downtime'] = int(data[key]['downtime'])
        response = update_threat_data(db, data, threat_data)
        return response

    elif path == '/getThreats':
        if event.get('multiValueQueryStringParameters', {}):
            return return_error(400,f"unexpected query parameter") 
        return get_threats_list(db)
    
    elif path == '/getControls':
        if event.get('multiValueQueryStringParameters', {}):
            return return_error(400,f"unexpected query parameter") 
        return get_controls_list(db)
    
    elif path == '/deleteThreats':
        params = event.get('multiValueQueryStringParameters', {})

        # Handle repeated parameters (e.g., controls=s1&controls=s2...)
        if 'threat_ids' in params and isinstance(params['threat_ids'], list):
            threat_ids = params['threat_ids'][0].split(',')
            threat_ids = set(threat_ids)
            threat_ids = list(threat_ids)
            threat_ids = [id for id in threat_ids if id not in [None, '']]
        else:
            #chosen_controls = []
            response = return_error(400,f"{params['threat_ids']} data is not expected in API .") 
            return response     
        return delete_threats(db, threat_ids)
    
    elif path == '/deleteControls':
        params = event.get('multiValueQueryStringParameters', {})

        # Handle repeated parameters (e.g., controls=s1&controls=s2...)
        if 'control_ids' in params and isinstance(params['control_ids'], list):
            control_ids = params['control_ids'][0].split(',')
            control_ids = set(control_ids)
            control_ids = list(control_ids)
            #print(f"control_ids:{control_ids}")
            control_ids = [id for id in control_ids if id not in [None, '']]
            #print(f"control_ids:{control_ids}")
        else:
            #chosen_controls = []
            response = return_error(400,f"{params['control_ids']} data is not expected in API .") 
            return response     
        return delete_controls(db, control_ids)
    
    elif path == '/resetGame':
        if event.get('multiValueQueryStringParameters', {}):
            return return_error(400,f"unexpected query parameter") 
        return reset_game(db)
    
    else:
        return return_error(400,f"Endpoint not found")
            # Fallback if the path is not recognized
            # response = {
            #     'statusCode': 403,
            #     'headers': {'Content-Type': 'application/json'},
            #     'body': json.dumps({'message': 'Endpoint not found'})
            # }
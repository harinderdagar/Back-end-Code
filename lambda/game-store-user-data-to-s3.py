import os
import json
from pymongo import MongoClient
import boto3
from datetime import datetime
from bson.json_util import dumps

# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None

# AWS S3 client setup
s3_client = boto3.client('s3')
bucket_name = 'game-store-user-data-to-s3'

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
    return cached_db

def get_user_data(db, user_id):
    # extracting userdata based on the user_id
    user_document = db.users.find_one({"user_id": user_id})
    #print(user_document)
    if user_document:
        user_document.pop('_id', None)
        return True, user_document
    else:
        return False, {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'UserData is not found, Click on PLAY button to start the game'})
        }
    


def lambda_handler(event, context):
    print('event: ', event)
    if event.get('multiValueQueryStringParameters', {}):
        return return_error(400,f"unexpected query parameter")
    

    # Extract the path from the event
    path = event.get('path')
    db = connect_to_database(MONGODB_URI)
    user_id = "dummyuser1"
    

    if path == '/remove':
        # Logic for endpoint1
        user_data_status, user_data = get_user_data(db, user_id)
        if not user_data_status:
            return user_data
        # Convert the document to a JSON string
        user_document_str = dumps(user_data, indent=2)
        # Generate a filename based on user_id and current timestamp
        filename = f'user_data_{user_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.txt'

         # Write the data to a temporary file (Lambda environment's /tmp directory)
        tmp_file_path = f'/tmp/{filename}'
        with open(tmp_file_path, 'w') as file:
            file.write(user_document_str)

    
        
        try:
        # Upload the file to S3
            s3_client.upload_file(tmp_file_path, bucket_name, filename)
            
            # verify the upload was successful by checking the file's existence
            s3_client.head_object(Bucket=bucket_name, Key=filename)
            
            # Since upload was successful, delete the document from MongoDB
            delete_result = db.users.delete_one({'user_id': user_id})
            
            # Check if the document was successfully deleted
            if delete_result.deleted_count > 0:
                print(f'status: success message: File {filename} uploaded to S3 and user document deleted successfully')
                return return_success('Data is deleted....')
                
            else:
                print(f'status: warning message: File {filename} uploaded to S3 but failed to delete user document')
                return return_error(400, 'Data cannot be deleted from DB')
        except Exception as e:
            # Handle exceptions and possible S3 errors or MongoDB deletion errors
            print(f'status: error message: File {filename} Failed to upload file to S3 or delete user document {str(e)}')
            return return_error(400, 'Data cannot stored on the disk')
        finally:
        # Delete the temporary file, regardless of the upload's success or failure
            try:
                os.remove(tmp_file_path)
            except Exception as e:
                # Log the error if the file could not be deleted
                print(f"Error deleting temporary file: {str(e)}")
            
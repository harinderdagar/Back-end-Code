import json

def lambda_handler(event, context):
    # Extract the connection ID from the event
    connection_id = event['requestContext']['connectionId']
    print(f'connection_id: {connection_id}')
    print(f'event: {event}')
    message = event['body']
    return {
        'statusCode': 401,
        'body': json.dumps({'message': 'Unauthorized Request'})
    }
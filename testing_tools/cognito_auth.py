import boto3
import hashlib
import hmac
import base64
from botocore.exceptions import ClientError

def get_access_token(client_id, client_secret, username, password, scope):
    def get_secret_hash(username, client_id, client_secret):
        message = username + client_id
        digest = hmac.new(client_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    secret_hash = get_secret_hash(username, client_id, client_secret)

    client = boto3.client('cognito-idp', region_name='us-east-1')

    try:
        auth_response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash
            },
            ClientMetadata={
                'scope': scope
            }
        )

        access_token = auth_response['AuthenticationResult']['AccessToken']
        print(f'access_token:{access_token}')
        return access_token

    except ClientError as e:
        print(e)
        return None


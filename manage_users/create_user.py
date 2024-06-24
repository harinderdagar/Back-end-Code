import boto3
import argparse
import csv

# Create a Cognito Identity Provider client
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

# Specify the user pool ID
user_pool_id = 'us-east-1_kzKpqNzPe'

def read_users_from_csv(filename):
    users = []
    with open(filename, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row:  # check if the row is not empty
                users.append({'username': row[0].strip()})
    return users

def set_user_password(client, user_pool_id, user):
    try:
        response = client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=user['username'],
            Password='***********',
            Permanent=True  # Set the password to be permanent
        )
        print(f"Password set successfully for user {user['username']}.")
    except Exception as e:
        print(f"Failed to set password for user {user['username']}: {e}")

def create_cognito_users(client, user_pool_id, users):
    for user in users:
        try:
            response = client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=user['username'],
                TemporaryPassword='***********',
                MessageAction='SUPPRESS'  # To prevent sending an invitation email
            )
            set_user_password(client, user_pool_id, user)
            print(f"User {user['username']} created successfully: {response}")
        except client.exceptions.UsernameExistsException:
            print(f"User {user['username']} already exists.")
        except Exception as e:
            print(f"Failed to create user {user['username']}: {e}")

def delete_cognito_user(client, user_pool_id, users):
    for user in users:
        try:
            response = client.admin_delete_user(
                Username=user['username'],
                UserPoolId=user_pool_id
            )
            print(f"User {user['username']} deleted successfully.")
        except client.exceptions.UserNotFoundException:
            print(f"User {user['username']} does not exist.")
        except Exception as e:
            print(f"An error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage AWS Cognito users")
    parser.add_argument('action', choices=['add', 'delete'], help='Action to perform: add or delete users')
    parser.add_argument('filename', help='Filename containing the users in CSV format')
    
    args = parser.parse_args()
    users = read_users_from_csv(args.filename)

    if args.action == 'add':
        create_cognito_users(cognito_client, user_pool_id, users)
    elif args.action == 'delete':
        delete_cognito_user(cognito_client, user_pool_id, users)

if __name__ == '__main__':
    main()

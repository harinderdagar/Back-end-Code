import os
import json
from pymongo import MongoClient
from datetime import datetime

# Environment variable: MongoDB URI
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
        #print(client)
    except Exception as e:
        print(f"gameRequestBudget: Error connecting to database: {e}")
        raise
    return cached_db

def return_success(response_data):
    """Returns a standard HTTP success response with given data."""
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
    """Returns a standard HTTP error response with given status code and error message."""
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

def get_user_document(db, user_id):
    """Retrieves a user document based on user_id."""
    # if not db:
    #     return "error", return_error(500, "Database connection is not established")
    try:
        user_data = db.usersData.find_one({"user_id": user_id})
        if not user_data:
            print(f'gameRequestBudget: {user_id}: You are not registered in the game.')
            return "error", return_error(436, 'You are not registered in the game.')
        elif user_data.get("apply_for_budget", False):
            return "success", user_data
        else:
            print(f'gameRequestBudget: {user_id}: Not eligible for budget renewal.')
            return "error", return_error(437, 'Not eligible for budget renewal.')
    except Exception as e:
        print(f'gameRequestBudget: {user_id}: Error accessing user data: {e}')
        return "error", return_error(500, f"Database operation failed.")

def calculate_budget(user_data, user_id):
    """Calculates the new budget for a user based on production data."""
    try:
        production_amount = user_data.get('accumulated_production_amount', 0)
        no_of_attacks = user_data.get('no_of_attacks', 0)
        production_score = 100 * production_amount / user_data.get('expected_production_amount', 1) if no_of_attacks > 0 else 0
        production_efficiency = min(max(production_score, 0), 100)

        if production_efficiency >= 80:
            assigned_budget = production_amount * 0.1
            print(f"gameRequestBudget: {user_id}: Got maximum budget {round(assigned_budget, 2)}")
        elif production_efficiency >= 50:
            assigned_budget = production_amount * 0.05
            print(f"gameRequestBudget: {user_id}: Got moderate budget{round(assigned_budget, 2)}")
        else:
            assigned_budget = production_amount * 0.03
            print(f"gameRequestBudget: {user_id}: Got minimum budget{round(assigned_budget, 2)}")

        assigned_budget = round(assigned_budget, 2)
        budget_left = user_data.get('budget_left', 0) + assigned_budget
        return assigned_budget, budget_left, production_amount - assigned_budget
    except Exception as e:
        print(f"gameRequestBudget: {user_id}: Error calculating budget: {e}")
        return 0, 0, 0  # Default values in case of error
    


def is_budget_enough(user_id, budget_left):
    try:
        if budget_left >= 1000:
            return 'success', False
        else:
            return 'success', True
            
    except Exception as e:
        print(f'gameRequestBudget: {user_id}- There is issue in deciding the flag of the apply_for_budget....')
        return 'error', return_error(514, f"There is issue in calculating the left budget....")


def update_budget_in_DB(db, user_id, assigned_budget, budget_left, production_amount, apply_for_budget):
    """Updates user's budget information in the database."""
    # if not db:
    #     print(f"gameRequestBudget: {user_id}:Database connection is not established")
    #     return False
    try:
        current_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        db.usersData.update_one(
            {"user_id": user_id},
            {
                '$push': {'assigned_budget': {'$each': [{'budget': assigned_budget, 'timestamp': current_timestamp}]}},
                '$set': {
                    "accumulated_production_amount": production_amount,
                    "apply_for_budget": apply_for_budget,
                    "budget_left": budget_left
                }
            }
        )
        return True
    except Exception as e:
        print(f"gameRequestBudget: {user_id}:Failed to update user data in the database: {e}")
        return False

def lambda_handler(event, context):
    """Handles incoming requests to the Lambda function."""
    try:
        print('event:', event)
        #user_id = 'dummyuser1'  # For demonstration, user ID is hardcoded
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)

        if not user_id:
            print('gameRequestBudget: User ID not found in the request')
            return return_error(438, 'UserID cannot be deduced from the API request token.')

        path = event.get('path')
        if path == '/requestBudget':
            try:
                db = connect_to_database(MONGODB_URI)
            except Exception as e:
                print(f'gameRequestBudget: Failed to connect to database. Error is {e}')
                return return_error(500, f"Internal Server error.")

            status, response = get_user_document(db, user_id)
            if status == 'error':
                return response
            else:
                user_data = response
                assigned_budget, budget_left, production_amount = calculate_budget(user_data, user_id)
                success_status, response = is_budget_enough(user_id, budget_left)
                if success_status == 'success':
                    apply_for_budget = response
                else:
                    apply_for_budget = False
                    return response
                if update_budget_in_DB(db, user_id, assigned_budget, budget_left, production_amount, apply_for_budget):
                    response_data = {'assigned_budget': assigned_budget, 'total_budget_you_have': budget_left}
                    return return_success(response_data)
                else:
                    print(f"gameRequestBudget: {user_id}: Failed to update user budget information in the database")
                    return return_error(500, 'Failed to update user budget information in the database')
        else:
            print(f"gameRequestBudget: {user_id}: {path} Endpoint not found")
            return return_error(403, 'Endpoint not found')
    except Exception as e:
        print(f'gameRequestBudget: {user_id}- An error occurred: {str(e)}')
        return return_error(500, 'Internal server error.')
import os
import json
from pymongo import MongoClient
from datetime import datetime, timedelta

# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None
control_degrade_time_period = 15 # in mins

def connect_to_database(uri):
    """ Connect to MongoDB using the URI, with caching to avoid multiple connections. """
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('=> using cached database instance')
        return cached_db
    try:
        client = MongoClient(uri)
        cached_db = client.test  # 'test' is the database name
        #print(client)
    except Exception as e:
        print(f"gameSelectControls: Error connecting to database: {e}")
        raise
    return cached_db

def return_success(response_data):
    """Formats a successful HTTP response with JSON body."""
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
    """Formats an error HTTP response based on the status code and error message."""
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

def find_or_create_user_document(db, user_id):
    """Checks for an existing user or creates a new user entry in the database."""
    try:
        user_data = db.usersData.find_one({"user_id": user_id})
        if not user_data:
            print(f'gameSelectControls: {user_id} - You are not registered in the game, click on PLAY button.')
            return return_error(436, 'You are not registered in the game, click on PLAY button.')
        if user_data.get("is_playing_status", False):
            print(f"gameSelectControls: {user_id} - Your game state is present in the system. Please continue to play the game or contact admin.")
            return return_error(409, 'Your game state is present in the system. Please continue to play the game or contact admin.')
    except Exception as e:
        print(f"gameSelectControls: {user_id} - Error is str{e}")
        return return_error(500, 'Database issue when finding the user {user_id} information')

def get_controls_data(db):
    """Retrieves control data from the database."""
    try:
        document = db.controls_data.find_one()
        controls_data = document['info']['controls']
        print(f"gameSelectControls: returning {controls_data}")
        return controls_data
    except Exception as e:
        print(f"gameSelectControls: Error in getting controls from DB. Error is str{e}")
        return return_error(500, 'Cannot get the controls from DB')

def get_user_data(db, user_id):
    """Retrieves user data from the database."""
    try:
        user_document = db.usersData.find_one({"user_id": user_id})
        if user_document:
            user_document.pop('_id', None)
            return True, user_document
        else:
            print(f"gameSelectControls: {user_id} - UserData is not found, Click on PLAY button.")
            return False, return_error(404, 'UserData is not found, Click on PLAY button.')
    except Exception as e:
        print(f"gameSelectControls: Error in getting user {user_id} from DB. Error is str{e}")
        return return_error(500, 'Cannot get the user {user_id} information from DB')


def verify_choosen_controls(chosen_controls, controls_data, user_id):
    """Verifies if the selected controls are available in the database."""
    try:
        controls_list = [control['control'] for control in controls_data.values()]
        for control in chosen_controls:
            if control not in controls_list:
                print(f"gameSelectControls: {user_id} - {control} is not present in database")
                return return_error(435, f"{control} is not present in database")
    except Exception as e:
        print(f"gameSelectControls: verify_choosen_controls function has issue for user {user_id} from DB. Error is str{e}")
        return return_error(500, 'Internal server error.')

def calculate_control_cost(user_data, controls_data, chosen_controls, controls_cost=0):
    """Calculates the total cost of selected controls against the user's budget."""
    try:
        budget_left = user_data.get('budget_left', "Not Present")
        budget = int(user_data['initial_budget']) if budget_left == "Not Present" else budget_left

        for control in controls_data.values():
            if control['control'] in chosen_controls:
                cost = int(control["cost"].replace("$", ""))
                controls_cost += cost
        return controls_cost, budget
    except Exception as e:
        print(f"gameSelectControls: Error in calculating control cost for user {user_data['user_id']}. Error is str{e}")
        return return_error(500, 'Internal server error.')

def is_budget_enough(db, user_id, budget_left, controls_data):
    try:
        controls_cost = []
        controls_cost_1 = 0
        controls_cost_2 = 0
        status, response = get_user_data(db, user_id)
        if status:
            print(f'status:{status}')
            user_data = response
        else:
            return 'error', response
        budget_left = int(user_data['budget_left'])
        selected_controls = [control['control'] for control in user_data['controls']]
        print(f'gameSelectControls: {user_id}- selected_controls: {selected_controls}')
        for selected_control in selected_controls:
            for control in controls_data.values():
                if selected_control != control['control']:
                    controls_cost.append(int(control["cost"].replace("$", "")))      
        print(f'controls_cost:{controls_cost}')
        if controls_cost:
            controls_cost_1, controls_cost_2  = sorted(controls_cost)[:2]
            if budget_left >= controls_cost_1 + controls_cost_2:
                return 'success', False
            else:
                return 'success', True
        
        else:
            print(f'gameSelectControls: {user_id}- There is issue in calculating the left budget....')
            return 'error', return_error(514, f"There is issue in calculating the left budget....")
    except Exception as e:
        print(f"gameSelectControls: {user_id}- Error in checking if budget is enough for user {user_id}. Error is str{e}")
        return 'error', return_error(500, 'Internal server error.')

def get_degraded_controls(user_data, chosen_controls_with_timestamp):
    """Identifies and segregates controls based on their timestamps to manage control degradation."""
    global control_degrade_time_period
    try:
        now = datetime.utcnow()
        threshold_time = now - timedelta(minutes=control_degrade_time_period)
        old_controls = user_data['controls']
        all_controls = old_controls + chosen_controls_with_timestamp
        new_controls = [control for control in all_controls if control['timestamp'] > threshold_time]
        removed_controls = [control for control in all_controls if control['timestamp'] <= threshold_time]

        return new_controls, removed_controls, old_controls
    except Exception as e:
        print(f"gameSelectControls: {user_data['user_id']}- Error in getting degraded controls for user {user_data['user_id']}. Error is str{e}")
        return return_error(500, 'Internal server error.')

# def get_degraded_controls(user_data, controls_data, chosen_controls_with_timestamp):
#     """Identifies and segregates controls based on their timestamps to manage control degradation."""
#     controls_list = []

#     try:
#         old_controls = user_data['controls']
#         chosen_controls_with_timestamp
#         controls_data = [(control['control'], control['effectiveness']) for control in controls_data.values()]
#         print(f"chosen_controls:{chosen_controls_with_timestamp}")
#         print(f"controls_data:{controls_data}")
#         for control1 in chosen_controls_with_timestamp:
#             #print(f"control1:{control1}")
#             for control2 in controls_data:
#                 #print(f"control2:{control2} and {control2[0]}")
#                 if control1.get('control', False) == control2[0]:
#                     effectiveness = control2[1]
#                     control1['effectiveness'] = effectiveness
#                     controls_list.append(control1)

#         print(f"gameSelectControls: {user_data['user_id']}- new controls list are {controls_list}")
        
#         now = datetime.utcnow()
#         threshold_time = now - timedelta(minutes=control_degrade_time_period)
#         old_controls = user_data['controls']
#         all_controls = old_controls + chosen_controls_with_timestamp
#         new_controls = [control for control in all_controls if control['timestamp'] > threshold_time]
#         removed_controls = [control for control in all_controls if control['timestamp'] <= threshold_time]


#         return new_controls, removed_controls, old_controls, controls_list
#     except Exception as e:
#         print(f"gameSelectControls: {user_data['user_id']}- Error in getting degraded controls for user {user_data['user_id']}. Error is str{e}")
#         return return_error(500, 'Internal server error.')

def verify_controls(old_controls, chosen_controls, user_id):
    """Checks if the selected controls were previously chosen in earlier levels."""
    try:
        existing_controls = {control['control'] for control in old_controls}
        for control in chosen_controls:
            if control in existing_controls:
                print(f"gameSelectControls: {user_id} - {control} has already been chosen previously.")
                return return_error(434, f"'{control}' has already been chosen previously.")
    except Exception as e:
        print(f"gameSelectControls: {user_id}- Error in verifying controls for user {user_id}. Error is str{e}")
        return return_error(500, 'Internal server error.')

def change_datetime_format(new_controls, degraded_controls):
    try:
        new_control_list = []
        degraded_controls_list = []
        for control in new_controls:
            if 'timestamp' in control and isinstance(control['timestamp'], datetime):
                control['timestamp'] = control['timestamp'].isoformat()
            new_control_list.append(control['control'])
        
        for control in degraded_controls:
            if 'timestamp' in control and isinstance(control['timestamp'], datetime):
                control['timestamp'] = control['timestamp'].isoformat()
            degraded_controls_list.append(control['control'])
        
        return new_control_list, degraded_controls_list
    except Exception as e:
        print(f"gameSelectControls: Error in changing datetime format. Error is str{e}")
        return return_error(500, 'Internal server error.')

def set_choices_database_level(db, user_id, chosen_controls, buget, controls_cost, user_data, new_controls, degraded_controls, old_controls, controls_data):
    try:
        #is_playing_status = False
        apply_for_budget = user_data.get('apply_for_budget', False)
        #current_levels = user_data.get("levels", {})
        
        response = verify_controls(old_controls, chosen_controls, user_id)
        if response:
            return response
        
        if buget >= controls_cost:
            budget_left = buget - controls_cost
            #is_playing_status = True
        else:
            return return_error(432, f"The chosen controls costing ${controls_cost} exceed the assigned budget.") 
        

        db.usersData.update_one(
            {"user_id": user_id},
            {   
                '$set': {
                    "controls": new_controls,
                    "budget_left": budget_left
                }
            }
        )

        success_status, response = is_budget_enough(db, user_id, budget_left, controls_data)
        if success_status == 'success':
            apply_for_budget = response
        else:
            return response
        
        db.usersData.update_one(
            {"user_id": user_id},
            {        
                '$set': {
                    "apply_for_budget": apply_for_budget
                }
            }
        )
        


        new_control_list, degraded_controls_list = change_datetime_format(new_controls, degraded_controls)
        response_data = {
                "chosen_controls": new_control_list,
                "degraded_controls_list": degraded_controls_list,
                 "request_for_budget": apply_for_budget,
                  "budget_left": budget_left }
        return return_success(response_data)
    except Exception as e:
        print(f"gameSelectControls: {user_id}- Error in setting choices in database for user {user_id}. Error is str{e}")
        return return_error(500, 'Internal server error.')

def lambda_handler(event, context):
    """Main function for AWS Lambda to handle incoming requests."""
    print(f"gameSelectControls: {event}")
    try:
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)

        if not user_id:
            print('gameSelectControls: User ID cannot be found in the request')
            return return_error(438, 'UserID cannot be deduced from the API request token.')

        # Extract the path from the event
        path = event.get('path')
        try:
            db = connect_to_database(MONGODB_URI)
        except Exception as e:
            print(f'gameSelectControls: Failed to connect to database. Error is {e}')
            return return_error(500, f"Internal Server error.")

        if path == '/selectControls':
            params = event.get('multiValueQueryStringParameters', {})
            chosen_controls = []
                    # Handle repeated parameters (e.g., controls=s1&controls=s2...)
            if 'controls' in params and isinstance(params['controls'], list):
                chosen_controls = params['controls'][0].split(',')
                chosen_controls = set(chosen_controls)
                chosen_controls = list(chosen_controls)
                chosen_controls = [id for id in chosen_controls if id not in [None, '']]
            else:
            #chosen_controls = []
                response = return_error(400,f"'{params['controls']}' data is not expected in API .") 
                return response

            # Validate and process controls if provided
            if chosen_controls:
                chosen_controls = list(set(chosen_controls))  # Remove duplicates
                print(f"gameSelectControls: {user_id}- Chosen controls are {chosen_controls}")
                response = find_or_create_user_document(db, user_id)
                print(f"gameSelectControls: {user_id}- find_or_create_user_document response is {response}")
                if response and 'statusCode' in response:
                    return response

                controls_data = get_controls_data(db)
                print(f"gameSelectControls: {user_id}- controls_data got from DB {controls_data}")
                if 'statusCode' in controls_data:
                    return controls_data

                response = verify_choosen_controls(chosen_controls, controls_data, user_id)
                if response:
                    return response

                status, user_data = get_user_data(db, user_id)
                #print(f"gameSelectControls: {user_id}- user_data got from DB {user_data}")
                if not status:
                    return user_data
                
                chosen_controls_with_timestamp = [{"control": control, "timestamp": datetime.utcnow()} for control in chosen_controls]   
                #new_controls, degraded_controls, old_controls, controls_list = get_degraded_controls(user_data, controls_data, chosen_controls_with_timestamp)
                new_controls, degraded_controls, old_controls = get_degraded_controls(user_data, chosen_controls_with_timestamp)
                print(f"gameSelectControls: {user_data['user_id']}- new Controls {new_controls}")
                print(f"gameSelectControls: {user_data['user_id']}- degraded Controls {degraded_controls}")
                print(f"gameSelectControls: {user_data['user_id']}- old Controls {old_controls}")
                #print(f"gameSelectControls: {user_data['user_id']}- old Controls {controls_list}")

                controls_cost, buget = calculate_control_cost(user_data, controls_data, chosen_controls)

                #response = set_choices_database_level(db, user_id, chosen_controls, buget, controls_cost, user_data, new_controls, degraded_controls, old_controls, controls_data, controls_list)
                response = set_choices_database_level(db, user_id, chosen_controls, buget, controls_cost, user_data, new_controls, degraded_controls, old_controls, controls_data)

                return response

            else:
                print(f"gameSelectControls: {user_id} - No controls specified or invalid control data provided.")
                return return_error(400, "No controls specified or invalid control data provided.")

        else:
            # Fallback if the path is not recognized
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': 'Endpoint not found'})
            }
    except Exception as e:
        print(f'gameSelectControls: {user_id}- An error occurred: {str(e)}')
        return return_error(500, 'Internal server error.')
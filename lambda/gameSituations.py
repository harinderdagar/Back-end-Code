import os
import json
from pymongo import MongoClient
from datetime import datetime

# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None
not_sufficient_fund = False

def connect_to_database(uri):
    """ Connect to MongoDB using the URI, with caching to avoid multiple connections. """
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('=> using cached database instance')
        return cached_db
    try:
        client = MongoClient(uri)
        cached_db = client.test
        #print(client)
    except Exception as e:
        print(f"gameSituations: Error connecting to database: {e}")
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
            print(f'gameSituations: {user_id} - You are not registered in the game, click on PLAY button.')
            return return_error(436, 'You are not registered in the game, click on PLAY button.')
        if user_data.get("is_playing_status", False):
            print(f"gameSituations: {user_id} - Your game state is present in the system. Please continue to play the game or contact admin.")
            return return_error(409, 'Your game state is present in the system. Please continue to play the game or contact admin.')
    except Exception as e:
        print(f"gameSituations: {user_id} - Error is str{e}")
        return return_error(500, 'Database issue when finding the user {user_id} information')

def get_controls_data(db):
    """Retrieves control data from the database."""
    try:
        document = db.controls_data.find_one()
        controls_data = document['info']['controls']
        print(f"gameSituations: returning {controls_data}")
        return controls_data
    except Exception as e:
        print(f"gameSituations: Error in getting controls from DB. Error is str{e}")
        return return_error(500, 'Cannot get the controls from DB')

def get_situations_data(db):
    """Retrieves situations data from the database."""
    try:
        document = db.situations.find_one()
        situations_data = document['situations']
        print(f"gameSituations: returning {situations_data}")
        return situations_data
    except Exception as e:
        print(f"gameSituations: Error in getting situations from DB. Error is str{e}")
        return return_error(500, 'Cannot get the situations from DB')


def get_user_data(db, user_id):
    """Retrieves user data from the database."""
    try:
        user_document = db.usersData.find_one({"user_id": user_id})
        if user_document:
            user_document.pop('_id', None)
            return True, user_document
        else:
            print(f"gameSituations: {user_id} - UserData is not found, Click on PLAY button.")
            return False, return_error(404, 'UserData is not found, Click on PLAY button.')
    except Exception as e:
        print(f"gameSituations: Error in getting user {user_id} from DB. Error is str{e}")
        return return_error(500, 'Cannot get the user {user_id} information from DB')

    
    

def verify_completed_situation(situation_completed, situations_data, option_choosen, user_id):
    """Verifies if the completed situation is available in the database."""
    try:
        situations_list = list(situations_data.keys())
        # print(f'situations_list is {situations_list}')
        if situation_completed not in situations_list:
            print(f"gameSituations: {user_id} - {situation_completed} is not present in database")
            return return_error(439, f"{situation_completed} is not present in database")
        if situations_data[situation_completed]['options'].get(option_choosen, False) == False:
            print(f"gameSituations: {user_id} - Chossen option is not present in DB '{option_choosen}'")
            return return_error(440, f"Your choosen option is not present in DB.")


    except Exception as e:
        print(f"gameSituations: verify_completed_situation function has issue for user {user_id} from DB. Error is str{e}")
        return return_error(500, 'Internal server error.')


def verify_situation(situation_completed, option_choosen, user_data, user_id):
    """Checks if the completed situation was previously completed."""
    try:
        old_situations = user_data.get('situations',[])
        print(f"gameSituations: {user_id} - old_situations {old_situations} which are present in the db.")
        # existing_situations = {situation['completed_situation']: situation['choosen_option'] for situation in old_situations}
        for situation in old_situations:
            if situation['completed_situation'] == situation_completed:
                if situation['choosen_option'] == option_choosen:
                    print(f"gameSituations: {user_id} - '{situation_completed}' and its option '{option_choosen}' has already been selected previously.")
                    return return_success(f"'{situation_completed}' and its option '{option_choosen}' has already been selected previously.")
                
    except Exception as e:
        print(f"gameSituations: verify_task -{user_id}- Error in verifying completed situation for user {user_id}. Error is str{e}")
        return return_error(500, 'Internal server error.')
    

def calculate_situation_cost(user_data, situations_data, situation_completed, option_choosen):
    """Calculates the total cost of situation choosen option against the user's budget."""
    try:
        # budget_left = user_data.get('budget_left', "Not Present")
        # budget = int(user_data['initial_budget']) if budget_left == "Not Present" else budget_left


        option_data = situations_data[situation_completed]['options'].get(option_choosen, False)
        if option_data:
            situation_cost = option_data.get("cost", 0)
            action = option_data.get("action")
            print(f"gameSituations: Choosen option '{option_choosen}' of completed situation '{situation_completed}' costing {situation_cost}")
            #return situation_cost
            return {'error': False, 'result': (situation_cost, action)}
        else:
            print(f"gameSituations: {option_choosen} is not present in the {list(situations_data[situation_completed]['options'].keys())}")
            return return_error(500, f'Choosen {option_choosen} is not present.')
    except Exception as e:
        print(f"gameSituations: Error in calculating situation cost for user {user_data['user_id']}. Error is str{e}")
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
        print(f'gameSituations: {user_id}- selected_controls: {selected_controls}')
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
        
        elif not selected_controls:
            print(f'gameSituations: {user_id}- None of the controls are not selected....')
            if budget_left >= 1000:
                return 'success', False
            else:
                return 'success', True
            
        else:
            print(f'gameSituations: {user_id}- There is issue in calculating the left budget....')
            return 'error', return_error(514, f"There is issue in calculating the left budget....")
    except Exception as e:
        print(f"gameSituations: {user_id}- Error in checking if budget is enough for user {user_id}. Error is str{e}")
        return 'error', return_error(500, 'Internal server error.')
    

    



def set_choices_database_level(db, user_id, situation_completed, option_choosen, situation_cost, user_data, controls_data, effected_controls, obsolete_controls, downtime, effective_option ):
    try:
        global not_sufficient_fund
        # effected_controls_upgrade_time_expired = 0
        budget_left = user_data.get('budget_left', "Not Present")
        budget = int(user_data['initial_budget']) if budget_left == "Not Present" else budget_left

        user_downtime = user_data.get("downtime", 0) + downtime
        user_obsolete_controls = list(set(user_data.get("obsolete_controls", []) + obsolete_controls))


        if budget >= situation_cost:
            budget_left = budget - situation_cost
            #is_playing_status = True
        else:
            db.usersData.update_one(
            {"user_id": user_id},
            {   
                '$push': {
                    "situations": {"completed_situation": situation_completed, "effective_action":effective_option, "choosen_option":option_choosen, "effected_controls": effected_controls, "obsolete_controls": obsolete_controls, "situation_cost": situation_cost, "downtime":downtime, "timestamp": datetime.utcnow()}
                    # "obsolete_controls": user_obsolete_controls
                    # "obsolete_controls": { "$each": obsolete_controls }
                    # "effected_controls_upgrade_time_expired": effected_controls_upgrade_time_expired
                },
                '$set': {
                    "downtime": user_downtime,
                    "obsolete_controls": user_obsolete_controls
                }
            }
        )
            print(f"gameSituations: {user_id}- In the else condition budget_left is {budget_left} and Situation cost is {situation_cost}")
        if not_sufficient_fund:
            print (f"flag is set to not_sufficient_fund: {not_sufficient_fund} ")
            not_sufficient_fund = False
            return return_error(432, f"The selected option, which costs ${situation_cost}, exceeds the remaining budget. Your only available choice is the first option listed for this situation.") 
        

        db.usersData.update_one(
            {"user_id": user_id},
            {   
                '$push': {
                    "situations": {"completed_situation": situation_completed, "effective_action":effective_option, "choosen_option":option_choosen, "effected_controls": effected_controls, "obsolete_controls": obsolete_controls, "situation_cost": situation_cost, "downtime":downtime, "timestamp": datetime.utcnow()}
                    # "obsolete_controls": user_obsolete_controls
                    # "obsolete_controls": { "$each": obsolete_controls }
                    # "effected_controls_upgrade_time_expired": effected_controls_upgrade_time_expired
                },
                '$set': {
                    "budget_left": budget_left,
                    "downtime": user_downtime,
                    "obsolete_controls": user_obsolete_controls
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
        

        response_data = {"budget_left": budget_left, "apply_for_budget": apply_for_budget, "response": "Your Situation response is well noted"}
        return return_success(response_data)
    except Exception as e:
        print(f"gameSituations: {user_id}- Error in setting the situation {situation_completed} in database for user {user_id}. Error is str{e}")
        return return_error(500, 'Internal server error.')
    
def get_situation_type(user_data, situation_completed, situations_data, option_choosen, user_id):
    try:
        data = situations_data.get(situation_completed, False).get("options", False).get(option_choosen, False)
        if data:
            if data.get("cost", False):
                print(f"gameSituations: {user_id}- Cost is found")
                effective_action = get_effective_action(user_data, data.get("cost"), option_choosen, user_id)
                return "cost", effective_action
            elif data.get("control", False):
                print(f"gameSituations: {user_id}- Control is found")
                return "control", data.get("control")
            elif data.get("downtime", False):
                print(f"gameSituations: {user_id}- Downtime is found")
                return "downtime", data.get("downtime")
        
        print(f"gameSituations: {user_id}- Error in getting option effected attributes")
        return 'error', return_error(441, 'Option data is not found in database')
    except Exception as e:
        print(f"gameSituations: {user_id}- Error in get_situation_type function. Error is str{e}")
        return 'error', return_error(500, 'Internal server error.')
    
def get_effective_action(user_data, situation_cost, option_choosen, user_id) :
    try:
        global not_sufficient_fund
        budget_left = user_data.get('budget_left', "Not Present")
        budget = int(user_data['initial_budget']) if budget_left == "Not Present" else budget_left
        effective_action = ""
        #is_playing_status = Fals
        #current_levels = user_data.get("levels", {})
        if budget >= situation_cost:
            effective_action = option_choosen
            #is_playing_status = True
        else:
            #effective_action = situations_data.get(situation_completed).get(option_choosen).get('1')
            effective_action = "1"
            not_sufficient_fund = True
            print(f"gameSituations: {user_id}- Default choosen option is used as user does not sufficient fund")
        
        return effective_action
    except Exception as e:
        print(f"gameSituations: {user_id}- Error in get_effective_action function. Error is str{e}")
        return 'error', return_error(500, 'Internal server error.')
    
def get_controls_name(controls, controls_data, user_id ):
    try:
        control_list = []

        if controls:
            for control in set(controls):
                control_list.append(controls_data[control]['control'])
        
        print(f"gameSituations: {user_id}- control_list is {control_list}")
        return control_list
    except Exception as e:
        print(f"gameSituations: {user_id}- Error in get_obsolete_controls_name function. Error is str{e}")
        return 'error', return_error(500, 'Internal server error.')
    
        



def lambda_handler(event, context):
    """Main function for AWS Lambda to handle incoming requests."""
    print(f"gameSituations: {event}")
    try:
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)

        if not user_id:
            print('gameSituations: User ID cannot be found in the request')
            return return_error(438, 'UserID cannot be deduced from the API request token.')

        # Extract the path from the event
        path = event.get('path')
        try:
            db = connect_to_database(MONGODB_URI)
        except Exception as e:
            print(f'gameSituations: Failed to connect to database. Error is {e}')
            return return_error(500, f"Internal Server error.")

        if path == '/situation':
            params = event.get('multiValueQueryStringParameters', {})
                    # Handle repeated parameters (e.g., controls=s1&controls=s2...)
            if 'situation' in params and isinstance(params['situation'], list):
                if len(params['situation'][0].split(',')) != 2:
                    return_error(442,f"'{params['situation']}' query parameters are not well formed .") 
                situation_completed = params['situation'][0].split(',')[0]
                option_choosen = params['situation'][0].split(',')[1]
                print(f'gameSituations: situation completed request{situation_completed}')
            else:
                response = return_error(400,f"'{params['situation']}' data is not expected in API .") 
                return response

            # Validate and process controls if provided
            if situation_completed:
                response = find_or_create_user_document(db, user_id)
                print(f"gameSituations: {user_id}- find_or_create_user_document response is {response}")
                if response and 'statusCode' in response:
                    return response
                
                situations_data = get_situations_data(db)
                print(f"gameSituations: {user_id}- get_situations_data got from DB {situations_data}")
                if 'statusCode' in situations_data:
                    return situations_data

                response = verify_completed_situation(situation_completed, situations_data, option_choosen, user_id)
                if response:
                    return response
                                
                status, user_data = get_user_data(db, user_id)
                #print(f"gameSituations: {user_id}- user_data got from DB {user_data}")
                if not status:
                    return user_data
                
                response = verify_situation(situation_completed, option_choosen, user_data, user_id)
                if response:
                    return response

                controls_data = get_controls_data(db)
                print(f"gameSituations: {user_id}- controls_data got from DB {controls_data}")
                if 'statusCode' in controls_data:
                    return controls_data
                
                situation_type, data =  get_situation_type(user_data, situation_completed, situations_data, option_choosen, user_id)
                if situation_type == 'error':
                    return data

                # budget = 1
                effected_controls = []
                obsolete_controls = []
                downtime = 0
                situation_cost = 0
                effective_option = option_choosen
                if situation_type:
                    if situation_type == 'cost':
                        if data:
                            effective_option = data
                            response = calculate_situation_cost(user_data, situations_data, situation_completed, option_choosen)
                            if response['result']:
                                situation_cost, action = response['result']
                                print(f" gameSituations: {user_id}-Situation Cost: {situation_cost}, action:{action}")
            
                            else:
                                return response
                            if effective_option != option_choosen:
                                situation_type, data =  get_situation_type(user_data, situation_completed, situations_data, effective_option, user_id)
                        else:
                            print(f" gameSituations: {user_id}- Cannot identify the impact of the selected option")

                    if situation_type == 'control':
                        if isinstance(data[-1], int):
                            effected_controls = data
                            effected_controls = get_controls_name(effected_controls[:-1], controls_data, user_id )
                            print(f" gameSituations: {user_id}- effected controls: {effected_controls}")
                        else:
                            obsolete_controls = data
                            obsolete_controls = get_controls_name(obsolete_controls, controls_data, user_id )
                            print(f" gameSituations: {user_id}- obsolete controls: {obsolete_controls}")

                    if situation_type == 'downtime':
                        downtime = data
                        print(f" gameSituations: {user_id}- downtime: {downtime}")
                else:
                    print(f"gameSituations: {user_id}- Cannot find the situation")

                #completed_situation_with_timestamp = {"completed_situation": situation_completed, "effective_option":effective_option, "choosen_option":option_choosen, "timestamp": datetime.utcnow()}
                #response = set_choices_database_level(db, user_id, chosen_controls, buget, controls_cost, user_data, new_controls, degraded_controls, old_controls, controls_data, controls_list)
                #response = set_choices_database_level(db, user_id, completed_situation_with_timestamp, budget, situation_cost, user_data, controls_data, situation_completed)
                response = set_choices_database_level(db, user_id, situation_completed, option_choosen, situation_cost, user_data, controls_data, effected_controls, obsolete_controls, downtime, effective_option )

                return response

            else:
                print(f"gameSituations: {user_id} - No Situation specified or invalid Situation data provided.")
                return return_error(400, "No Situation specified or invalid Situation data provided.")

        else:
            # Fallback if the path is not recognized
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': 'Endpoint not found'})
            }
    except Exception as e:
        print(f'gameSituations: {user_id}- An error occurred: {str(e)}')
        return return_error(500, 'Internal server error.')
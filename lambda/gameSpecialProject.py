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
        cached_db = client.test 
        #print(client)
    except Exception as e:
        print(f"specialProject: Error connecting to database: {e}")
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
            print(f'specialProject: {user_id} - You are not registered in the game, click on PLAY button.')
            return return_error(436, 'You are not registered in the game.')
        if user_data.get("is_playing_status", False):
            print(f"specialProject: {user_id} - Your game state is present in the system. Please continue to play the game or contact admin.")
            return return_error(409, 'Your game state is present in the system. Please continue to play the game or contact admin.')
    except Exception as e:
        print(f"specialProject: {user_id} - Error is str{e}")
        return return_error(500, 'Database issue when finding the user {user_id} information')

def get_controls_data(db):
    """Retrieves control data from the database."""
    try:
        document = db.controls_data.find_one()
        controls_data = document['info']['controls']
        print(f"specialProject: returning {controls_data}")
        return controls_data
    except Exception as e:
        print(f"specialProject: Error in getting controls from DB. Error is str{e}")
        return return_error(500, 'Cannot get the controls from DB')
    
def get_tasks_data(db):
    """Retrieves tasks data from the database."""
    try:
        document = db.specialProjects.find_one()
        tasks_data = document['projects']
        print(f"specialProject: returning {tasks_data}")
        return tasks_data
    except Exception as e:
        print(f"specialProject: Error in getting tasks from DB. Error is str{e}")
        return return_error(500, 'Cannot get the tasks from DB')

def get_user_data(db, user_id):
    """Retrieves user data from the database."""
    try:
        user_document = db.usersData.find_one({"user_id": user_id})
        if user_document:
            user_document.pop('_id', None)
            return True, user_document
        else:
            print(f"specialProject: {user_id} - UserData is not found, Click on PLAY button.")
            return False, return_error(404, 'UserData is not found, Click on PLAY button.')
    except Exception as e:
        print(f"specialProject: Error in getting user {user_id} from DB. Error is str{e}")
        return return_error(500, 'Cannot get the user {user_id} information from DB')

    
def verify_completed_task(task_completed, tasks_data, user_id):
    """Verifies if the completed task is available in the database."""
    try:
        tasks_list = [task['name'] for task in tasks_data.values()]
        if task_completed not in tasks_list:
            print(f"specialProject: {user_id} - Completed {task_completed} is not present in database")
            return return_error(445, f" Completed {task_completed} is not present in database")
    except Exception as e:
        print(f"specialProject: verify_completed_task function has issue for user {user_id} from DB. Error is str{e}")
        return return_error(500, 'Internal server error.')



def calculate_task_cost(user_data, tasks_data, task_completed, task_cost=0):
    """Calculates the total cost of completed task against the user's budget."""
    try:
        budget_left = user_data.get('budget_left', "Not Present")
        budget = int(user_data['initial_budget']) if budget_left == "Not Present" else budget_left

        for task in tasks_data.values():
            print('task is {task}')
            if task['name'] == task_completed:
                cost = task["cost"]
                task_cost += cost
        return {'error': False, 'result': (task_cost, budget)}
    except Exception as e:
        print(f"specialProject: Error in calculating task cost for user {user_data['user_id']}. Error is str{e}")
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
        print(f'specialProject: {user_id}- selected_controls: {selected_controls}')
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
            print(f'specialProject: {user_id}- None of the controls are not selected....')
            if budget_left >= 1000:
                return 'success', False
            else:
                return 'success', True
            
        else:
            print(f'specialProject: {user_id}- There is issue in calculating the left budget....')
            return 'error', return_error(514, f"There is issue in calculating the left budget....")
    except Exception as e:
        print(f"specialProject: {user_id}- Error in checking if budget is enough for user {user_id}. Error is str{e}")
        return 'error', return_error(500, 'Internal server error.')
    



    
def verify_task(task_completed, user_data, user_id):
    """Checks if the completed task was previously completed."""
    try:
        old_tasks = user_data.get('tasks',[])
        print(f"specialProject: {user_id} - tasks {old_tasks} which are present in the db.")
        existing_tasks = {task['completed_task'] for task in old_tasks}
        if task_completed in existing_tasks:
            print(f"specialProject: {user_id} - {task_completed} has already been completed previously.")
            # return return_success(f"'{task_completed}' has already been completed previously.")
            return return_error(444, f"'{task_completed}' project has already been completed previously.")
    except Exception as e:
        print(f"specialProject: verify_task -{user_id}- Error in verifying completed tasks for user {user_id}. Error is str{e}")
        return return_error(500, 'Internal server error.')


def set_choices_database_level(db, user_id, completed_task_with_timestamp, budget, task_cost, user_data, controls_data, task_completed):
    try:
        #is_playing_status = False
        apply_for_budget = user_data.get('apply_for_budget', False)
        #current_levels = user_data.get("levels", {})
       
        if budget >= task_cost:
            budget_left = budget - task_cost
            #is_playing_status = True
        else:
            return return_error(443, f"The chosen Project costing ${task_cost} exceed the left budget.") 
        

        db.usersData.update_one(
            {"user_id": user_id},
            {   
                '$push': {
                    "tasks": completed_task_with_timestamp
                },
                '$set': {
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
        

        response_data = {"budget_left": budget_left, "apply_for_budget": apply_for_budget}
        return return_success(response_data)
    except Exception as e:
        print(f"specialProject: {user_id}- Error in setting the task {task_completed} in database for user {user_id}. Error is str{e}")
        return return_error(500, 'Internal server error.')



def lambda_handler(event, context):
    """Main function for AWS Lambda to handle incoming requests."""
    print(f"specialProject: {event}")
    try:
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)

        if not user_id:
            print('specialProject: User ID cannot be found in the request')
            return return_error(438, 'UserID cannot be deduced from the API request token.')

        # Extract the path from the event
        path = event.get('path')
        try:
            db = connect_to_database(MONGODB_URI)
        except Exception as e:
            print(f'specialProject: Failed to connect to database. Error is {e}')
            return return_error(500, f"Internal Server error.")

        if path == '/specialProject':
            params = event.get('multiValueQueryStringParameters', {})
            #task_completed = []
                    # Handle repeated parameters (e.g., controls=s1&controls=s2...)
            if 'project' in params and isinstance(params['project'], list):
                task_completed = params['project'][0].split(',')[0]
                # task_completed = set(task_completed)
                # task_completed = list(task_completed)
                # task_completed = task_completed[0]
                print(f'specialProject: task completed request{task_completed}')
            else:
                response = return_error(400,f"'{params['task']}' data is not expected in API .") 
                return response

            # Validate and process controls if provided
            if task_completed:
                response = find_or_create_user_document(db, user_id)
                print(f"specialProject: {user_id}- find_or_create_user_document response is {response}")
                if response and 'statusCode' in response:
                    return response
                
                tasks_data = get_tasks_data(db)
                print(f"specialProject: {user_id}- tasks_data got from DB {tasks_data}")
                if 'statusCode' in tasks_data:
                    return tasks_data

                response = verify_completed_task(task_completed, tasks_data, user_id)
                if response:
                    return response
                
                status, user_data = get_user_data(db, user_id)
                #print(f"specialProject: {user_id}- user_data got from DB {user_data}")
                if not status:
                    return user_data
                
                response = verify_task(task_completed, user_data, user_id)
                if response:
                    return response

                controls_data = get_controls_data(db)
                print(f"specialProject: {user_id}- controls_data got from DB {controls_data}")
                if 'statusCode' in controls_data:
                    return controls_data
                
                response = calculate_task_cost(user_data, tasks_data, task_completed)
                if response['result']:
                    task_cost, budget = response['result']
                    print("Task Cost:", task_cost, "Budget:", budget)
                else:
                    return response
                     
                completed_task_with_timestamp = {"completed_task": task_completed, "timestamp": datetime.utcnow()}
                #response = set_choices_database_level(db, user_id, chosen_controls, buget, controls_cost, user_data, new_controls, degraded_controls, old_controls, controls_data, controls_list)
                response = set_choices_database_level(db, user_id, completed_task_with_timestamp, budget, task_cost, user_data, controls_data, task_completed)

                return response

            else:
                print(f"specialProject: {user_id} - No task specified or invalid task data provided.")
                return return_error(400, "No task specified or invalid task data provided.")

        else:
            # Fallback if the path is not recognized
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'message': 'Endpoint not found'})
            }
    except Exception as e:
        print(f'specialProject: {user_id}- An error occurred: {str(e)}')
        return return_error(500, 'Internal server error.')
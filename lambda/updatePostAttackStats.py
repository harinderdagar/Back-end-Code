# Standard library imports
import os
import json
from pymongo import MongoClient
import random
from datetime import datetime, timedelta

# Setting up environment variables and initial values
MONGODB_URI = os.environ['MONGODB_URI'] 
cached_db = None  # Caching mechanism to avoid reconnecting to DB
per_hour_earning = 10000  # Set the hourly earning rate

# Function to connect to MongoDB database using the URI
def connect_to_database(uri):
    global cached_db
    print('=> connect to database')
    if cached_db is not None:
        print('=> using cached database instance')
        return cached_db
    client = MongoClient(uri)
    print(client)
    cached_db = client.test  # Test is the database name
    return cached_db

# Function to retrieve control data from the database
def get_controls_data(db):
    document = db.controls_data.find_one()
    controls_data = document['info']['controls']
    return controls_data

# Function to retrieve tasks data from the database
def get_tasks_data(db):
    document = db.specialProjects.find_one()
    tasks_data = document['projects']
    print(f'tasks data is {tasks_data}')
    return tasks_data

# Function to retrieve user data from the database based on user ID
def get_user_data(db, user_id):
    user_document = db.usersData.find_one({"user_id": user_id})
    if user_document:
        user_document.pop('_id', None)  # Remove the MongoDB unique ID before returning
        return True, user_document
    else:
        return False, "'message': 'UserData is not found, Click on PLAY button to start the game'"

# Function to calculate the combined effectiveness of chosen controls and completed tasks
def calculate_combined_effectiveness(chosen_controls, controls_data, threat_key, tasks_data, tasks_completed, situations_completed_controls):
    controls_effectiveness_list = {}
    task_effectiveness_list = {}
    combined_effectiveness = 1

    # Mapping controls and tasks for quick lookup
    controls_dict = {control['control']: control['effectiveness'].get(threat_key, '0%') for control in controls_data.values()}
    tasks_dict = {task['name']: task['effectiveness'].get(threat_key, '0') for task in tasks_data.values()}

    # Process controls for effectiveness calculation
    for chosen_control in chosen_controls:
        if chosen_control not in situations_completed_controls:
            effectiveness_str = controls_dict.get(chosen_control, '0%')
            effectiveness = float(effectiveness_str.strip('%')) / 100
            if effectiveness > 0:
                controls_effectiveness_list[chosen_control] = effectiveness_str
                combined_effectiveness *= (1 - effectiveness)

    # Process tasks for effectiveness calculation
    for task_completed in tasks_completed:
        effectiveness_str = tasks_dict.get(task_completed, '0%')
        effectiveness = float(effectiveness_str.strip('%')) / 100
        if effectiveness > 0:
            task_effectiveness_list[task_completed] = effectiveness_str
            combined_effectiveness *= (1 - effectiveness)

    combined_effectiveness = 1 - combined_effectiveness
    controls_tasks_combined_effectiveness = f"{combined_effectiveness * 100:.2f}%"
    print(f"controls and tasks effectiveness: {combined_effectiveness * 100:.2f}%")
    print(f"Controls effectiveness list: {controls_effectiveness_list}")
    print(f"Task effectiveness list: {task_effectiveness_list}")

    return controls_tasks_combined_effectiveness, controls_effectiveness_list, task_effectiveness_list



# functions handle user interaction and data manipulation within the MongoDB database, focusing on user controls, tasks, and the impacts of attack scenarios on user performance metrics. 
def get_user_controls(user_data):
    controls = user_data.get('controls', "Not Present")
    if controls == "Not Present":
        chosen_controls = []
    else:
        chosen_controls = [control['control'] for control in controls]
    return chosen_controls

def get_user_tasks(user_data):
    tasks = user_data.get('tasks', "Not Present")
    if tasks == "Not Present":
        tasks_completed = []
    else:
        tasks_completed = [task['completed_task'] for task in tasks]
    return tasks_completed

def get_user_situations_controls(user_data):
    situations = user_data.get('situations', "Not Present")
    if situations == "Not Present":
        situations_completed_controls = []
    else:
        situations_completed_controls = [control for situation in situations 
                        if situation.get('effected_controls_upgrade_time_expired', 1) == 0
                        for control in situation['effected_controls']]
        print(f"situations_completed_controls:{situations_completed_controls}")
        situations_completed_controls = list(set(situations_completed_controls))
    return situations_completed_controls



def get_userIds(db):
    user_ids = [doc['user_id'] for doc in db.usersData.find({}, {'_id': 0, 'user_id': 1})]
    return user_ids

    
# The `lambda_handler` function serves as the entry point for AWS Lambda execution
def lambda_handler(event, context):
    print('event: ', event)

    #cognito_username = event['requestContext']['authorizer']['claims']['username']
    #user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)
    #user_id = 'dummyuser1'
    #attack = 'Phishing'
    #threat_key = 't3'
    #attack_downtime = 8
    attack = event.get('attack_name', 'Not Found')
    threat_key = event.get('attack_key', 'Not Found')
    attack_downtime = event.get('attack_down_time', 'Not Found')
    

    if 'Not Found' in [attack, threat_key, attack_downtime]:
        print('Attack information is not present in the function invocation')
        return
    attack_downtime = int(attack_downtime)
    db = connect_to_database(MONGODB_URI)
    user_ids = get_userIds(db)

    if user_ids:
        for user_id in user_ids:
            #user_id = "3" # Replace with actual user ID
            status, response = get_user_data(db, user_id)
            if status:
                print(f'status:{status}')
                user_data = response
            else:
                #print(response)
                return
            #print(f'response:{response}')
            #print(f'user_data:{user_data}, type:{type(user_data)}')
            chosen_controls = get_user_controls(user_data)
            tasks_completed = get_user_tasks(user_data)
            situations_completed_controls = get_user_situations_controls(user_data)

            controls_data = get_controls_data(db)
            tasks_data = get_tasks_data(db)

            controls_tasks_combined_effectiveness, controls_effectiveness_list, task_effectiveness_list = calculate_combined_effectiveness(chosen_controls, controls_data, threat_key, tasks_data, tasks_completed, situations_completed_controls)        
            
            response = set_choices_database_level(db, user_id, chosen_controls, controls_tasks_combined_effectiveness, controls_effectiveness_list, threat_key, user_data, attack, attack_downtime, task_effectiveness_list)

    else:
        print('Userid cannot be found in the DB')

    print('=> returning result: ')
    return


def calculate_loss(user_data, is_attack_successfull):
    no_of_attacks_successfull = 0
    no_of_attacks_mitigated = 0
    if is_attack_successfull:
        no_of_attacks_successfull = 1 
    else:
        no_of_attacks_mitigated = 1
    # return f"{production_of_day}$", f"{loss}$", f"{production_amount}$"
    
    # total_earning = sum([int(threat.get("actual_earning")) for threat in user_data["threats"]])
    # expected_total_earning = production_amount * len(user_data["threats"])
    # total_loss = sum([int(threat.get("loss")) for threat in user_data["threats"]])

    no_of_attacks_successfull = int(user_data.get("no_of_attacks_successfull", 0)) + no_of_attacks_successfull
    no_of_attacks_mitigated = int(user_data.get("no_of_attacks_mitigated", 0)) + no_of_attacks_mitigated

    return no_of_attacks_successfull, no_of_attacks_mitigated


def check_attack_successfulness(controls_tasks_combined_effectiveness, controls_effectiveness_list):
    max_effectiveness_control= ""
    random_int = 0
    max_effectiveness = 0
    controls_effectiveness = int(float(controls_tasks_combined_effectiveness.strip('%')))
    print(f'controls_effectiveness: {controls_effectiveness}')
    if controls_effectiveness:
        random_int = random.randint(0, 99)
        print(random_int)
        attack_successful = random_int > controls_effectiveness
    else:
        attack_successful = True

    print(f'attack_successful: {attack_successful}')
    #if not attack_successful:
    if controls_effectiveness_list:
        for control , effectiveness in controls_effectiveness_list.items():
            effectiveness = int(effectiveness.strip('%'))
            if effectiveness > max_effectiveness:
                max_effectiveness = effectiveness
                max_effectiveness_control = control

    return attack_successful, max_effectiveness_control
        

def get_game_start_time(db):
    try:
        game_status= db.game_status.find_one()
        return game_status
    except Exception as e:
            print(f'Failed to get data from game_status collection')
            return "error"


def set_choices_database_level(db, user_id, chosen_controls, controls_tasks_combined_effectiveness, controls_effectiveness_list, threat_key, user_data, attack, attack_downtime, task_effectiveness_list):
    # Find the current user document
    #user_data = get_user_data(db, user_id)
    #user_document = db.usersData.find_one({"user_id": user_id})
    is_playing_status = False
    apply_for_budget = user_data.get('apply_for_budget', False)
    current_levels = user_data.get("levels", {})
    
    next_level = max([int(lvl) for lvl in current_levels.keys()], default=0) + 1
    update_path = f"levels.{next_level}"
    
    
    is_attack_successfull, control = check_attack_successfulness(controls_tasks_combined_effectiveness, controls_effectiveness_list)
    no_of_attacks_successfull, no_of_attacks_mitigated = calculate_loss(user_data, is_attack_successfull)

    #current_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    # uptime = int(total_earning/1000)
    # downtime = int(total_loss/1000)
    

    game_status = get_game_start_time(db)
    if game_status != "error":
        current_timestamp = datetime.now()
        game_start_time = game_status.get('start_timestamp') 
    
    user_game_start_time = user_data['player_start_time']
    if user_game_start_time > game_start_time:
        #expected_uptime = int(game_start_time - current_timestamp)
        # Calculate the difference between game_start_time and current_timestamp
        time_difference = current_timestamp - user_game_start_time
        print('Player started his game after admin gave go ahead')
    else: 
        time_difference = current_timestamp - game_start_time
        print('Player started his game before admin gave go ahead')

    
    expected_uptime = int(time_difference.total_seconds() / 60)
    print(f'expected_uptime:{expected_uptime}')
    print(f'is_attack_successfull:{is_attack_successfull}')
    if is_attack_successfull:
        if expected_uptime:
            if expected_uptime > (user_data.get('downtime', 0) + attack_downtime):
                uptime = expected_uptime - (user_data.get('downtime', 0) + attack_downtime)
            else:
                uptime = 0
        else:
            uptime = 0
        downtime = user_data.get('downtime', 0) + attack_downtime
    else:
        if expected_uptime > (user_data.get('downtime', 0)):
            uptime = expected_uptime - (user_data.get('downtime', 0))
        else:
            uptime = 0
        downtime = user_data.get('downtime', 0)
    print(f'uptime:{uptime}')
    print(f'downtime:{downtime}')
    total_earning = per_hour_earning * uptime
    print(f'total_earning:{total_earning}')
    expected_total_earning = per_hour_earning * expected_uptime
    print(f'expected_total_earning:{expected_total_earning}')
    total_loss = per_hour_earning * downtime
    print(f'total_loss:{total_loss}')
    if is_attack_successfull:
        loss_due_to_attack = per_hour_earning * attack_downtime
    else:
        loss_due_to_attack = 0
    print(f'loss_due_to_attack:{loss_due_to_attack}')

    #chosen_controls_with_timestamp = [{"control": control, "timestamp": datetime.utcnow()} for control in chosen_controls]
    
    # Current timestamp in the format DD-MM-YYYY hh:mm:ss
    current_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    #new_controls, degraded_controls = get_degraded_controls(user_data, chosen_controls_with_timestamp)


    try:
        db.usersData.update_one(
        {"user_id": user_id},
        {
            '$push': {
                # Update the 'threats' field to include an array that represents the tuple
                'threats': {
                    '$each': [
                        {
                            'name': attack,
                            'is_attack_successfull': is_attack_successfull,
                            'actual_earning': total_earning,
                            'expected_earning': expected_total_earning,
                            'loss_due_to_attack': loss_due_to_attack
                        }
                    ]
                }
            },
            
            '$set': {
                #'degraded_controls_list': degraded_controls_list,
                "is_playing_status": is_playing_status,
                "expected_uptime": expected_uptime,
                "uptime": uptime,
                "downtime": downtime,
                "no_of_attacks_successfull": no_of_attacks_successfull,
                "no_of_attacks_mitigated": no_of_attacks_mitigated,
                "accumulated_production_amount": total_earning,
                "accumulated_production_loss": total_loss,
                "expected_production_amount": expected_total_earning,
                f"{update_path}.controls.chosen": chosen_controls,
                f"{update_path}.controls.max_effective_control": control,
                f"{update_path}.controls.max_effective_control_effectiveness": controls_effectiveness_list.get(control, 0),
                f"{update_path}.controls_tasks_combined_effectiveness": controls_tasks_combined_effectiveness,
                f"{update_path}.controls_effectiveness": controls_effectiveness_list,
                f"{update_path}.tasks_effectiveness": task_effectiveness_list,
                f"{update_path}.attack": attack,
                # f"{update_path}.expected_earning": production_amount,
                # f"{update_path}.actual_earning": production_of_day,
                # f"{update_path}.loss": loss,
                f"{update_path}.timestamp": current_timestamp  # Adding the timestamp
            }
        }
    )
        print(f'Users attack stats has been updated successfully')
    except Exception as e:
        print(f'Users attack stats has failed to update in DB: {e}')
        return
    
    try:
        collection = db['game_status']
        update_query = {
                        '$set': {
                            "update_attack_stats": "False",
                        }
                    }
        collection.update_one({}, update_query, upsert=True)
        print('update_attack_stats flag is unset successfully')
    except Exception as e:
            print(f'update_attack_stats flag is failed to unset in DB: {e}')


    print('=> returning after update to DB....')
    return
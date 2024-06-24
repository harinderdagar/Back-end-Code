import asyncio
import json
import aiohttp
import websockets
import os
import logging
import random
import urllib.parse
from cognito_auth import get_access_token
import argparse 

# Setup argument parsing
parser = argparse.ArgumentParser(description="Run the async script with user credentials.")
parser.add_argument("username", help="The username for the user.")
parser.add_argument("password", help="The password for the user.")
args = parser.parse_args()

# Use the provided arguments
username = args.username
password = args.password

# Constants
TEMP_FILE_PATH = './controls_list.json'
URI = "wss://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/"
PLAY_URL = 'https://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/play'
REQUEST_BUDGET_URL = 'https://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/requestBudget'
SELECT_CONTROLS_URL = 'https://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/selectControls?controls='
GET_USER_STATS_URL = 'https://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/getUserStats'
SELECT_PROJECT_URL = 'https://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/task?task='
SOLVE_SITUATIONS_URL = 'https://XXXXXXXXXXXXXXXXXXXXXXXXXXXX.amazonaws.com/production/situation?situation='

sorted_controls = []
available_controls = {}
#selected_controls = []
available_projects = {
    1: {"project": "https", "cost": 500},
    2: {"project": "Strong Password Policies", "cost": 200},
    3: {"project": "Monitor System", "cost": 300}
}

available_situations = [(1,1), (1,2), (2,1), (2,2), (2,3)]

budget_left = 15000
initiate_stats_request = True
apply_for_budget = False
request_budget_flag = True
connection_established = False
start_task = False


# Replace the following variables with your own values
client_id = 'xxxxxxxxxxxxxxxxxxxxxx'
client_secret = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
custom_scope = 'https://api_userpool_resource_server.com/Read'

# Define the dedicated directory for logs
log_dir = "./logs"

# Ensure the log directory exists
os.makedirs(log_dir, exist_ok=True)

# Setup logging configuration
log_file_path = os.path.join(log_dir, f"{username}.log")

# Setup logging configuration
# logging.basicConfig(level=logging.INFO, filename=f'{username}.log', filemode='a',
#                     format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO, filename=log_file_path, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Global variable to store the access token
access_token = ''

async def listen(uri):
    global available_controls
    global sorted_controls
    global connection_established
    logging.info("WebSocket listen: Attempting to open WebSocket connection.")
    async with websockets.connect(uri) as websocket:
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                #logging.info(f"Received data from WebSocket: {data}")
                if data.get('budget', False):
                    connection_established = True 
                    # Sorting and formatting the controls.
                    sorted_controls = sorted(data['controls'].items(), key=lambda x: x[0])
                    formatted_controls = [f"{idx+1}. {control['control']}, {control['cost']}" for idx, (_, control) in enumerate(sorted_controls)]
                    formatted_message = "\n".join(formatted_controls)                     
                    # Printing formatted message.
                    logging.info(f"WebSocket listen: formatted Controls data: {formatted_message}")
                    if sorted_controls:
                        available_controls = {str(idx + 1): control for idx, (key, control) in enumerate(sorted_controls)}
                        with open(TEMP_FILE_PATH, 'w') as temp_file:
                            json.dump(available_controls, temp_file)
                        
                    if not available_controls:
                        logging.info(f'WebSocket listen:  inside websocket available_controls:{available_controls}')
                        logging.info("WebSocket listen:  No controls available. Admin has not started the game.") 
                        if os.path.exists(TEMP_FILE_PATH):
                            with open(TEMP_FILE_PATH, 'r') as temp_file:
                                available_controls = json.load(temp_file)                   
                    sorted_controls = [ item['control'] for item in available_controls.values()] 
                    logging.info(f"WebSocket listen: Available controls are {sorted_controls}")       
                    # else:
                    #     continue    
                elif data.get('attack', False):
                    # Printing formatted message.
                    logging.info(f"WebSocket listen: Attacks data: {data}")
                else:
                    logging.error(f"WebSocket listen: Cannot identify the received data on web socket: {data}")
                
            
        except websockets.exceptions.ConnectionClosed as e:
            logging.error(f"WebSocket listen: WebSocket connection closed with exception: {e}")

async def call_api(url, method='GET', payload=None):
    global access_token
    headers = {'Authorization': f'Bearer {access_token}'}
    async with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(url, headers=headers) as response:
                response_data = await response.json()
                #logging.info(f"API GET Response from {url}: Status {response.status}, Data {response_data}")
                # if response.status != 200:
                #     logging.error(f"call_api: API POST Response from {url}: Status {response.status}, Data {response_data}")
                if 500 <= response.status <= 599:
                    logging.error(f"call_api: API POST Response from {url}: Status {response.status}, Data {response_data}")
                else:
                    logging.info(f"call_api: API POST Response from {url}: Status {response.status}, Data {response_data}")
                return response_data, response.status
        else:
            async with session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()
                if response.status != 200:
                    logging.error(f"call_api: API POST Response from {url}: Status {response.status}, Data {response_data}")
                return response_data, response.status

async def user_interaction():
    continue_program = True
    play_game = True
    global available_controls
    #global selected_controls
    global sorted_controls
    global budget_left
    global connection_established
    global start_task
    global apply_for_budget
    logging.info("user_interaction: Starting user interaction loop.")
    try:
        while True:
            await asyncio.sleep(random.uniform(0, 6))
            if connection_established:
                if play_game:
                    api_response, response_status = await call_api(PLAY_URL)
                    if response_status == 200:
                        logging.info(f"user_interaction: Play API called. Response status: {response_status}")
                        play_game = False
                        start_task = True
                    else:
                        # await asyncio.sleep(5)
                        continue

                    #break
                # More processing and decision making here

                if not play_game:
                    if not available_controls:
                        if os.path.exists(TEMP_FILE_PATH):
                            logging.info(f"user_interaction: Reading the controls from the file, seems admin has not started the game")
                            with open(TEMP_FILE_PATH, 'r') as temp_file:
                                available_controls = json.load(temp_file)
                            #sorted_controls = [item['control'] for item in available_controls]
                            # for item in available_controls.values():
                            #     print(item)
                            sorted_controls = [ item['control'] for item in available_controls.values()]
                            logging.info(f"user_interaction: Availiable controls for selection {sorted_controls}")
                        
                        else:
                            # await asyncio.sleep(5)
                            continue
                
                    #for idx, (control_id, control) in enumerate(available_controls.items(), 1):
                        #logging.info(f"{idx}: {control['control']}, {control['cost']}")
                    option = random.randrange(1, len(available_controls))
                    #print(f'available_controls:{available_controls}')
                    # control_options = control_option_input.split(',')
                    # for option in control_options:
                    #     option = option.strip()
                    option = str(option)
                    selected_control = []
                    if option in available_controls:
                        logging.info(f"Choosen option is {available_controls[option]['control']}")
                        if int(available_controls[option]['cost'].replace('$', '')) <= budget_left:
                            logging.info(f"user_interaction: left budget ${budget_left} is greater then selected control cost {available_controls[option]['cost']}")
                            selected_control = available_controls[option]['control']
                            logging.info(f'user_interaction: selected_control: {selected_control}')
                            logging.info(f'user_interaction: sorted_controls: {sorted_controls}')

                            # if selected_control in sorted_controls:
                            #     logging.info(f"user_interaction: selected control {selected_control} is in the left controls list")
                            # #selected_controls.append(selected_control)
                                
                            # else:
                            #     logging.info(f"user_interaction: selected control {selected_control} is not in the left controls list")
                            #     # await asyncio.sleep(2)
                            #     continue
                        # elif budget_left <= 1000 :
                        #     if apply_for_budget == 'True':
                        #         await request_budget()
                            # api_response, response_status = await call_api(REQUEST_BUDGET_URL)
                            # logging.info(f'Request Budget api response after budget is left than 1000')
                            # logging.info(f"Request budget API called. Response status: {response_status}")


                    else:
                        logging.info(f"user_interaction: Invalid control option: {option}. Please try again.")
                        # await asyncio.sleep(5)
                        continue
                    # if selected_control:
                    safe_control = urllib.parse.quote(selected_control)
                    url = SELECT_CONTROLS_URL + safe_control
                    #controls_query = ','.join(selected_controls)
                    api_response, response_status = await call_api(url)
                    logging.info(f"user_interaction: Select control API called. Response status: {response_status}")

                    if response_status == 200:
                        budget_left = api_response['budget_left']
                        degraded_controls_list = api_response['degraded_controls_list']
                        apply_for_budget = api_response['request_for_budget']
                        sorted_controls = [item for item in sorted_controls if item not in selected_control]
                        sorted_controls = list(set(sorted_controls + degraded_controls_list))
                        logging.info(f'user_interaction: apply_for_budget : {apply_for_budget}')
                        logging.info(f'user_interaction: budget_left: {budget_left}')
                        logging.info(f'user_interaction: Controls avilable for selection: \n {sorted_controls}')
                        # await asyncio.sleep(5)
                            # api_response, response_status = await call_api(REQUEST_BUDGET_URL)
                            # logging.info(f'Request Budget api response after the apply_for_budget flag is True ')
                            # logging.info(f"Request budget API called. Response status: {response_status}")
                    else:
                        logging.info(f"user_interaction: select controls api response: {api_response}")
                    # await asyncio.sleep(5)
                    # else:
                    #     logging.info('user_interaction: Controls are not selected')
                    # # await asyncio.sleep(5)
            else:
                logging.info('user_interaction: Waiting for the websocket connection to establish....')
                # await asyncio.sleep(5)

    except Exception as e:
        logging.error(f"user_interaction: Unexpected error in user interaction: {e}")


async def complete_project():
    global start_task
    global available_projects
    global apply_for_budget
    global budget_left
    selected_projects = []
    logging.info("complete_project: Starting special project task.")
    try:
        while True:
            await asyncio.sleep(random.uniform(0, 6))
            if start_task:
                option = random.randrange(1, len(available_projects)+1)
                #print(f'available_controls:{available_controls}')
                # control_options = control_option_input.split(',')
                # for option in control_options:
                #     option = option.strip()
                selected_project = ""
                if option in available_projects.keys():
                    logging.info(f"complete_project: Choosen option is {available_projects[option]['project']}")
                    if available_projects[option]['cost'] <= budget_left:
                        logging.info(f"complete_project: left budget ${budget_left} is greater then selected project cost {available_projects[option]['cost']}")
                        selected_project = available_projects[option]['project']
                        logging.info(f'complete_project: selected_project: {selected_project}')
            

                        # if selected_project not in selected_projects:
                        #     logging.info(f"complete_project: selected project {selected_project} is in the left project list")
                        #     #selected_projects.append(selected_project)
                            
                        # else:
                        #     logging.info(f"complete_project: selected project {selected_project} is not in the left project list")
                        #     await asyncio.sleep(30)
                        #     continue

                else:
                    logging.info(f"complete_project:Invalid project option: {option}. Please try again.")
                    # await asyncio.sleep(5)
                    continue
                if selected_project:
                    safe_project = urllib.parse.quote(selected_project)
                    url = SELECT_PROJECT_URL + safe_project
                    #controls_query = ','.join(selected_controls)
                    api_response, response_status = await call_api(url)
                    logging.info(f"complete_project:Select project API called. Response status: {response_status}")

                    if response_status == 200:
                        if isinstance(api_response, dict):
                            # If the response is dict, extract the relevant data
                            selected_projects.append(selected_project)
                            budget_left = api_response['budget_left']
                            apply_for_budget = api_response['apply_for_budget']
                            logging.info(f'complete_project: apply_for_budget : {apply_for_budget}')
                            logging.info(f'complete_project: budget_left: {budget_left}')
                            # await asyncio.sleep(5)
                        else:
                            # If the response is a plain string, just log it
                            logging.info(f"complete_project: {api_response}")
                            # api_response, response_status = await call_api(REQUEST_BUDGET_URL)
                            # logging.info(f'Request Budget api response after the apply_for_budget flag is True ')
                            # logging.info(f"Request budget API called. Response status: {response_status}")
                    else:
                        logging.info(f"complete_project: select Projects api response: {api_response}")
                    # await asyncio.sleep(5)
                else:
                    logging.info('complete_project: selected project has already been selected in the past')
                # await asyncio.sleep(5)
            else:
                logging.info('complete_project: Waiting for player to register himself to the game....')
                # await asyncio.sleep(5)

    except Exception as e:
        logging.error(f"complete_project: Unexpected error in complete project function: {e}")




async def solve_situations():
    global start_task
    global available_situations
    global apply_for_budget
    global budget_left
    logging.info("solve_situations: Starting solve situations function")
    try:
        while True:
            await asyncio.sleep(random.uniform(0, 6))
            if start_task:
                option = random.randrange(0, len(available_situations))
                #print(f'available_controls:{available_controls}')
                # control_options = control_option_input.split(',')
                # for option in control_options:
                #     option = option.strip()

                selected_situation = available_situations[option]
                if selected_situation:
                    selected_situation_id, selected_option = selected_situation
                    safe_situation = urllib.parse.quote(f"situation{selected_situation_id},{selected_option}")
                    url = SOLVE_SITUATIONS_URL + safe_situation
                    #controls_query = ','.join(selected_controls)
                    api_response, response_status = await call_api(url)
                    logging.info(f"solve_situations: Selected situation API called with params situation{selected_situation_id},{selected_option}. Response status: {response_status}")

                    if response_status == 200:
                        if isinstance(api_response, dict):
                            #If the response is dict, extract the relevant data
                            budget_left = api_response['budget_left']
                            apply_for_budget = api_response['apply_for_budget']
                            logging.info(f'solve_situations: apply_for_budget : {apply_for_budget}')
                            logging.info(f'solve_situations: budget_left : {budget_left}')
                            #logging.info(f'projects avilable for completion: \n {selected_projects}')
                            # await asyncio.sleep(5)
                        else:
                            # If the response is a plain string, just log it
                            logging.info(f"solve_situations: {api_response}")
                            # api_response, response_status = await call_api(REQUEST_BUDGET_URL)
                            # logging.info(f'Request Budget api response after the apply_for_budget flag is True ')
                            # logging.info(f"Request budget API called. Response status: {response_status}")
                    else:
                        logging.info(f"solve_situations: solve situations response: {api_response}")
                    # await asyncio.sleep(5)
                else:
                    logging.info('solve_situations: selected situations is None "{selected_situation}"')
                # await asyncio.sleep(5)
            else:
                logging.info('solve_situations: Waiting for player to register himself to the game....')
                # await asyncio.sleep(5)

    except Exception as e:
        logging.error(f"Unexpected error in solve situations function: {e}")

async def request_budget():
    global request_budget_flag
    global apply_for_budget
    global connection_established
    try:
        while True:
            await asyncio.sleep(random.uniform(0, 6))
            if connection_established:
                # if apply_for_budget:
                #     if request_budget_flag:
                api_response, response_status = await call_api(REQUEST_BUDGET_URL)
                logging.info(f'request_budget: Request Budget api response after the apply_for_budget flag is True ')
                logging.info(f"request_budget: Request budget API called. Response status: {response_status}")
                    # else:
                    #     logging.info(f'request_budget: 5 mins has not past since applied for request budget')
                    # request_budget_flag = False
                    # # await asyncio.sleep(5)
                    # request_budget_flag = True
                
                # else:
                #     logging.info(f'request_budget: apply_for_budget is False')
                #     # await asyncio.sleep(5)
            else:
                logging.info('request_budget: Waiting for the websocket connection to establish....')
                # await asyncio.sleep(5)
    except Exception as e:
        logging.error(f"request_budget: Unexpected error in request_budget: {e}")
 


async def main():
    global access_token
    #access_token = 'Your_Access_Token'  # This should be set correctly
    access_token = get_access_token(client_id, client_secret, username, password, custom_scope)

    if access_token:
        logging.info("main: Access token retrieved, starting main async tasks.")
        tasks = [
            listen(URI),
            user_interaction(),
            get_user_stats(),
            request_budget(),
            solve_situations(),
            complete_project()
        ]
        await asyncio.gather(*tasks)
    else:
        logging.error("main: Failed to obtain access token. Exiting...")

async def get_user_stats():
    global apply_for_budget
    global connection_established
    global budget_left
    logging.info("get_user_stats: Starting periodic user stats retrieval.")
    while True:
        await asyncio.sleep(random.uniform(0, 6))
        try:
            if connection_established:
                api_response, response_status = await call_api(GET_USER_STATS_URL)
                logging.info(f"get_user_stats: Received user stats: {api_response}")
                if response_status == 200:
                    apply_for_budget = api_response.get('apply_for_budget', False)
                    logging.info(f'get_user_stats: apply_for_budget is {apply_for_budget}')
                    budget_left = api_response.get('budget_left', 15000)
                    logging.info(f'get_user_stats: Budget left for buying controls or completing projects {budget_left}')
            # await asyncio.sleep(5)  # Check every minute
        except Exception as e:
            logging.error(f"get_user_stats: Error retrieving user stats: {e}")
            # await asyncio.sleep(5)  # check after 30 sec

if __name__ == "__main__":
    asyncio.run(main())


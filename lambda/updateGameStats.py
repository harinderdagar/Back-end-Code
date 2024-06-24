import os
from pymongo import MongoClient
from datetime import datetime

# Environment variable: MongoDB URI
MONGODB_URI = os.environ['MONGODB_URI']
cached_db = None
per_hour_earning = 10000

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
    # extracting the user data based on user_id
    user_document = db.usersData.find_one({"user_id": user_id})
    #print(user_document)
    if user_document:
        user_document.pop('_id', None)
        return True, user_document
    else:
        return False, "'message': 'UserData is not found, Click on PLAY button to start the game'"

 # extracting all the user_id
def get_userIds(db):
    user_ids = [doc['user_id'] for doc in db.usersData.find({}, {'_id': 0, 'user_id': 1})]
    return user_ids

 # extracting Game status data
def get_game_start_time(db):
    try:
        game_status= db.game_status.find_one()
        return game_status
    except Exception as e:
            print(f'Failed to get data from game_status collection')
            return "error"

    

def lambda_handler(event, context):
    print('event: ', event)

    #cognito_username = event['requestContext']['authorizer']['claims']['username']
    #user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('username', None)
    #user_id = 'dummyuser1'
    #attack = 'Phishing'
    #threat_key = 't3'
    #attack_downtime = 8
    db = connect_to_database(MONGODB_URI)
    game_status = get_game_start_time(db)
    print(f'game_status:{game_status}')
    
    print(f'game_status_start or stop:{game_status.get('started', "False")}')

    if game_status != "error":
        if game_status.get('started', "False") == "False":
            print("Game has not been started by Admin")
            return
        elif game_status.get('update_attack_stats', "True") == "True":
            print("Game stats has been updated by updatePostAttackStats lambda function")
            return
    else:
        return
    user_ids = get_userIds(db)
    
    if user_ids:
        for user_id in user_ids:
            #user_id = "3" # Replace with actual user ID
            status, response = get_user_data(db, user_id)
            if status:
                print(f'status:{status}')
                user_data = response
            else:
                print(response)
                return
            print(f'response:{response}')
            #print(f'user_data:{user_data}, type:{type(user_data)}')        
            
            set_stats_in_DB(db, user_id, user_data, game_status)

    else:
        print('Userid cannot be found in the DB')
    
   
    update_situation_controls_expiry_time(db)

    print('=> returning result: ')
    return


#update the stats in the DB
def set_stats_in_DB(db, user_id, user_data, game_status):
    game_start_time = game_status['start_timestamp']
    user_game_start_time = user_data['player_start_time']
    current_timestamp = datetime.now()
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
    uptime = expected_uptime - user_data.get('downtime', 0)
    if uptime < 0:
        uptime = 0
    print(f'uptime:{uptime}')
    downtime = user_data.get('downtime', 0)
    print(f'downtime:{downtime}')
    total_earning = per_hour_earning * uptime
    print(f'total_earning:{total_earning}')
    expected_total_earning = per_hour_earning * expected_uptime
    print(f'expected_total_earning:{expected_total_earning}')
    total_loss = per_hour_earning * downtime
    print(f'total_loss:{total_loss}')


    db.usersData.update_one(
    {"user_id": user_id},
    {
        
        '$set': {
            "expected_uptime": expected_uptime,
            "uptime": uptime,
            "downtime": downtime,
            "accumulated_production_amount": total_earning,
            "accumulated_production_loss": total_loss,
            "expected_production_amount": expected_total_earning,
            "stats_update_timestamp": datetime.utcnow()
        }
    }
)

    # Current timestamp in the format DD-MM-YYYY hh:mm:ss
    stats_update_timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S") 
    print(f'{stats_update_timestamp}=> returning after update to DB....')
    return

def update_situation_controls_expiry_time(db):
    try:
        # Define the update pipeline
        # update_pipeline = [
        #     {
        #         '$set': {
        #             'situations': {
        #                 '$map': {
        #                     'input': '$situations',
        #                     'as': 'situation',
        #                     'in': {
        #                         '$cond': {
        #                             'if': {
        #                                 '$and': [
        #                                     {'$eq': [{'$type': {'$arrayElemAt': ['$$situation.effected_controls', -1]}}, 'int']},
        #                                     {'$lte': ['$$situation.timestamp', datetime.utcnow()]}
        #                                 ]
        #                             },
        #                             'then': {
        #                                 '$mergeObjects': [
        #                                     '$$situation',
        #                                     {'expired': 1}
        #                                 ]
        #                             },
        #                             'else': '$$situation'
        #                         }
        #                     }
        #                 }
        #             }
        #         }
        #     }
        # ]

        update_pipeline = [
            {
        '$set': {
            'situations': {
                '$map': {
                    'input': '$situations',
                    'as': 'situation',
                    'in': {
                        '$let': {
                            'vars': {
                                'last_int': {'$arrayElemAt': ['$$situation.effected_controls', -1]}  # Assuming last element is the integer
                            },
                            'in': {
                                '$cond': {
                                    'if': {
                                        '$and': [
                                            {'$eq': [{'$type': '$$last_int'}, 'int']},  # Check if last element is an integer
                                            {'$gt': [{'$subtract': [datetime.utcnow(), '$$situation.timestamp']}, {'$multiply': ['$$last_int', 60000]}]}  # Check time difference, converting minutes to milliseconds
                                        ]
                                    },
                                    'then': {
                                        '$mergeObjects': [
                                            '$$situation',
                                            {'expired': 1}
                                        ]
                                    },
                                    'else': '$$situation'
                                }
                            }
                        }
                    }
                }
            }
        }
    }
]

        # Perform the update
        result = db.usersData.update_many(
            {'situations': {'$exists': True, '$ne': []}},  # Filter documents where situations field exists and is not empty
            update_pipeline  # Pass the update pipeline as the second argument
        )
        print(f'Modified {result.modified_count} documents.')
    except Exception as e:
        print(f"An error occurred in the update_situation_controls_expiry_time function: {e}")
    return
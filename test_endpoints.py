import json
import requests
from dotenv import load_dotenv
import os
from colorama import Fore
import time
import re
import sys


load_dotenv()
username = os.getenv('PELOTON_USERNAME')
password = os.getenv('PELOTON_PASSWORD')

base_url = 'https://api.onepeloton.com'
login_path = '/auth/login'
workouts_path = '/api/user/{userId}/workouts'
workout_path = '/api/workout/{workoutId}'
ride_path = '/api/ride/{rideId}/details'

VERBOSE_MODE = True  # Change this to False if you don't want verbose output
SLEEP_TIMER = 0.3  # this means each API call will be made after a delay of 0.5 seconds being kind to the undocumented API friends...


def create_session(username, password):
    login_url = base_url + login_path
    data = {"username_or_email": username, "password": password}
    session = requests.Session()
    response = session.post(login_url, json=data)
    if response.status_code != 200:
        print(f"Failed to create session. Response: {response.json()}")
        return None, None
    return session, response.json()['user_id']


def handle_response(response, error_message, endpoint=None):
    if response.status_code != 200:
        error_details = error_message + ". Response: " + str(response.json())
        if endpoint and VERBOSE_MODE:
            print(f"Endpoint: {endpoint}\n{error_details}")
        return None
    data = response.json()
    if VERBOSE_MODE:
        print(json.dumps(data, indent=4))
    return data

def get_user_workouts(session, user_id):
    url = base_url + workouts_path.replace("{userId}", user_id)
    response = session.get(url)
    endpoint = url if response.status_code != 200 else None
    return handle_response(response, "Failed to fetch user workouts", endpoint)  

def get_workout_details(session, workout_id):
    url = base_url + workout_path.replace("{workoutId}", workout_id)
    response = session.get(url)
    endpoint = url if response.status_code != 200 else None
    return handle_response(response, "Failed to fetch workout details", endpoint)

def get_ride_details(session, ride_id):
    url = base_url + ride_path.replace("{rideId}", ride_id)
    response = session.get(url)
    endpoint = url if response.status_code != 200 else None
    return handle_response(response, "Failed to fetch ride details", endpoint)

def count_endpoints(endpoints):
    count = 0
    for category, request_types in endpoints.items():
        for request_type, endpoint_data_list in request_types.items():
            count += len(endpoint_data_list)
    return count


def load_endpoints():
    with open('base_endpoints.json') as f:
        endpoints = json.load(f)
        print(f"Loaded {count_endpoints(endpoints)} endpoints.")
        return endpoints

def preprocess_endpoints(session, endpoints, params):
    ready_to_test = {}
    parameters_filled = {}

    regex = re.compile("{(.*?)}")
    for category, request_types in endpoints.items():
        for request_type, endpoint_data_list in request_types.items():
            for endpoint_data in endpoint_data_list:
                endpoint = endpoint_data.get("endpoint")  # added this line to extract endpoint string from dictionary

                # Check if endpoint is missing or not a string
                if not endpoint or not isinstance(endpoint, str):
                    print(f"Skip invalid endpoint format: {endpoint_data}")
                    continue

                dynamic_parameters = regex.findall(endpoint)
                if not dynamic_parameters:
                    ready_to_test.setdefault(category, {}).setdefault(request_type, []).append(endpoint)
                else:
                    for param in dynamic_parameters:
                        param_value = params.get(param)
                        if not param_value and param == "userNameOrId":  # Add this line
                            param_value = params.get("userId")  # And this line
                        if param_value:
                            endpoint = endpoint.replace("{" + param + "}", param_value)
                            parameters_filled.setdefault(category, {}).setdefault(request_type, []).append(endpoint)
                        elif 'instructorId' in dynamic_parameters and 'instructorId' not in params:
                            instructor_list_response = session.get(base_url + "/api/instructor")
                            instructors = handle_response(instructor_list_response, "Failed to fetch instructors")
                            if isinstance(instructors, dict) and 'data' in instructors and len(instructors['data']) > 0:
                                 first_instructor_id = instructors['data'][0]['id']
                                 endpoint = endpoint.replace("{instructorId}", first_instructor_id)
                                 parameters_filled.setdefault(category, {}).setdefault(request_type, []).append(endpoint)
                        else:
                            ready_to_test.setdefault(category, {}).setdefault(request_type, []).append(endpoint)

    return ready_to_test, parameters_filled


def test_endpoints(session, user_id, ready_to_test, parameters_filled):
    print("\nStarting endpoint testing...")
    #set this to keep from duplicating
    tested_endpoints = set()
    success_count = 0
    fail_count = 0
    incomplete_count = 0

    test_result_data = {}

    regex = re.compile("{(.*?)}")

    combined_endpoints = [ready_to_test, parameters_filled]
    for endpoints in combined_endpoints:
        for category, request_types in endpoints.items():
            print(f"\nCategory: {category}")
            for request_type, endpoint_list in request_types.items():
                for endpoint in endpoint_list:
                     # If endpoint is already tested, skip it
                    if endpoint in tested_endpoints:
                        continue
                    else:
                        tested_endpoints.add(endpoint)
                    # Replace userID placeholder if exists
                    endpoint = endpoint.replace("{userId}", user_id)
                    missing_parameters = regex.findall(endpoint)  # Check if there are still some missing parameters

                    if missing_parameters:  # If there are still some missing params, print 'INCOMPLETE' and move to the next endpoint
                        print(f"\nEndpoint: {endpoint} {Fore.YELLOW}INCOMPLETE{Fore.RESET}")
                        incomplete_count += 1
                        endpoint_entry = {
                            "endpoint": endpoint,
                            "test_result": "Incomplete",
                            "failure_details": None,
                            "test_date": time.time()
                        }
                        test_result_data.setdefault(category, {}).setdefault(request_type, []).append(endpoint_entry)
                        continue

                    headers = {}
                    params = {}
                    if 'Peloton-Platform' in endpoint:
                        headers['Peloton-Platform'] = "your-value"

                    if 'user_query' in endpoint:
                        params['user_query'] = "your-value"

                    try:
                        url = base_url + endpoint
                        response = session.request(request_type, url, headers=headers, params=params)
                    except Exception as e:
                        print(f"\nRequest failed due to {e}")
                        continue

                    print(f"\nEndpoint: {endpoint}")
                    print(f'Status Code: {response.status_code}', end=' ')

                    failure_details = None
                    if response.status_code == 200:
                        print(f'{Fore.GREEN}SUCCESS!{Fore.RESET}')
                        success_count += 1
                        endpoint_result = 'Successful'

                    else:
                        print(f'{Fore.RED}FAIL{Fore.RESET}')
                        fail_count += 1
                        endpoint_result = 'Failed'

                        try:
                            if response.headers['content-type'] == 'application/json':
                                resp_content = response.json()
                                failure_details = {
                                    "status": resp_content.get('status'),
                                    "error_code": resp_content.get('error_code'),
                                    "message": resp_content.get('message')
                                }
                            else:
                                failure_details = {
                                    "status": response.status_code,
                                    "error_code": None,
                                    "message": 'Response is not a JSON'
                                }
                        except json.JSONDecodeError:
                            failure_details = {
                                "status": response.status_code,
                                "error_code": None,
                                "message": 'Error during response parsing'
                            }

                    endpoint_entry = {
                        "endpoint": endpoint,
                        "test_result": endpoint_result,
                        "failure_details": failure_details,
                        "test_date": time.time()
                    }
                    test_result_data.setdefault(category, {}).setdefault(request_type, []).append(endpoint_entry)

                    if VERBOSE_MODE:
                        try:
                            print(f'Response Content: \n{json.dumps(response.json(), indent=4)}\n')
                        except json.JSONDecodeError:
                            print(f'Response Content: {response.content}\n')

                    print(f"{Fore.LIGHTBLACK_EX}API-cognizant pause for {SLEEP_TIMER} seconds.{Fore.RESET}")
                    time.sleep(SLEEP_TIMER)

    # combine endpoints waiting for parameters and tested endpoint results
    endpoints = {**test_result_data}

    with open('queried_endpoints_temp.json', 'w') as f:
        json.dump(endpoints, f, indent=4)

    # if everything is okay until now, rename the temp file to queried_endpoints.json
    os.rename('queried_endpoints_temp.json', 'queried_endpoints.json')

    print("\nTesting completed!")
    print(f"Successful calls: {Fore.GREEN}{success_count}{Fore.RESET}")
    print(f"Failed calls: {Fore.RED}{fail_count}{Fore.RESET}")
    print(f"Incomplete calls: {Fore.YELLOW}{incomplete_count}{Fore.RESET}")

def main():
    original_output = sys.stdout
    if VERBOSE_MODE:
        print(f"VEBOSE_MODE=True, saving all outputs to verbose_mode.txt")
        print(f"Please hold...")
        log_file = open("verbose_mode.txt", "w")
        sys.stdout = log_file

    session, user_id = create_session(username, password)
    if session is None:
        print("Login unsuccessful. Exiting...", flush=True)
        return

    workoutId = None
    rideId = None
    workouts = get_user_workouts(session, user_id)
    if workouts and workouts['data']:
        workoutId = workouts['data'][0]['id']
        workout_details = get_workout_details(session, workoutId)
        if workout_details:
            rideId = workout_details['ride'].get('id')

    params = {"userId": user_id, "workoutId": workoutId, "rideId": rideId}
    endpoints = load_endpoints()
    initial_count = count_endpoints(endpoints)
    ready_to_test, parameters_filled = preprocess_endpoints(session, endpoints, params)

    global test_result_data
    test_result_data = {}

    test_endpoints(session, user_id, ready_to_test, parameters_filled)

    final_count = count_endpoints(endpoints)

    if initial_count != final_count:
        print(f"WARNING: Initial count of endpoints ({initial_count}) does not match final count ({final_count}).", flush=True)
    else:
        print(f"Endpoint counts matched. Initial and final count is {initial_count}.", flush=True)

    # Revert the output back to terminal and close the file if VERBOSE_MODE was enabled
    if VERBOSE_MODE:
        sys.stdout = original_output
        log_file.close()

if __name__ == "__main__":
    main()
import json
import requests
from dotenv import load_dotenv
import os
from colorama import Fore
import time
import re

load_dotenv()
username = os.getenv('PELOTON_USERNAME')
password = os.getenv('PELOTON_PASSWORD')

base_url = 'https://api.onepeloton.com'
login_path = '/auth/login'

VERBOSE_MODE = False  # Change this to False if you don't want verbose output

def create_session(username, password):
    login_url = base_url + login_path
    data = {"username_or_email": username, "password": password}
    session = requests.Session()
    response = session.post(login_url, json=data)
    if response.status_code != 200:
        print(f"Failed to create session. Response: {response.json()}")
        return None, None
    return session, response.json()['session_id']

def count_endpoints(endpoints):
    count = 0
    for category, request_types in endpoints.items():
        for request_type, endpoint_data_list in request_types.items():
            count += len(endpoint_data_list)
    return count

def load_endpoints():
    with open('endpoints.json') as f:
        endpoints = json.load(f)
        print(f"Loaded {count_endpoints(endpoints)} endpoints.")
        return endpoints

def preprocess_endpoints(endpoints):
    ready_to_test = {}
    parameters_needed = {}

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
                        if "{" + param + "}" not in endpoint:  
                            parameters_needed.setdefault(category, {}).setdefault(request_type, []).append(endpoint)
                            break
                    else:
                        ready_to_test.setdefault(category, {}).setdefault(request_type, []).append(endpoint)

    return ready_to_test, parameters_needed

def test_endpoints(session, user_id, ready_to_test, parameters_needed):
    print("\nStarting endpoint testing...")
    success_count = 0
    fail_count = 0
    incomplete_count = 0

    test_result_data = {}

    regex = re.compile("{(.*?)}")

    for category, request_types in ready_to_test.items():
        print(f"\nCategory: {category}")
        for request_type, endpoint_list in request_types.items():
            for endpoint in endpoint_list:
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
                if response.status_code==200:
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
    
    # combine endpoints waiting for parameters and tested endpoint results
    endpoints = {**test_result_data, **parameters_needed}
    with open('endpoints.json', 'w') as f:
        json.dump(endpoints, f, indent=4)

    print("\nTesting completed!")
    print(f"Successful calls: {Fore.GREEN}{success_count}{Fore.RESET}")
    print(f"Failed calls: {Fore.RED}{fail_count}{Fore.RESET}")
    print(f"Incomplete calls: {Fore.YELLOW}{incomplete_count}{Fore.RESET}")

    # include the check here as well right before writing the file
    print(f"Going to save {count_endpoints(endpoints)} endpoints. If no errors were shown above, the file will be overwritten.")

    # write to a temporary file first
    with open('endpoints_temp.json', 'w') as f:
        json.dump(endpoints, f, indent=4)

    # if everything is okay until now, replace the original file
    os.rename('endpoints_temp.json', 'endpoints.json')


def main():
    session, user_id = create_session(username, password)
    if session is None:
        print("Login unsuccessful. Exiting...")
        return
    
    endpoints = load_endpoints()
    initial_count = count_endpoints(endpoints)
    ready_to_test, parameters_needed = preprocess_endpoints(endpoints)

    global test_result_data
    test_result_data = {}

    test_endpoints(session, user_id, ready_to_test, parameters_needed)

    final_count = count_endpoints(endpoints)

    if initial_count != final_count:
        print(f"WARNING: Initial count of endpoints ({initial_count}) does not match final count ({final_count}).")
    else:
        print(f"Endpoint counts matched. Initial and final count is {initial_count}.")

if __name__ == "__main__":
    main()
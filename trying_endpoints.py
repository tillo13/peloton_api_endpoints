import json
import os
import requests
from dotenv import load_dotenv

VERBOSE_MODE = False   # Set to False if you don't want verbose output

# Load environment variables
load_dotenv()

username = os.getenv('PELOTON_USERNAME')
password = os.getenv('PELOTON_PASSWORD')

base_url = 'https://api.onepeloton.com'
login_path = '/auth/login'
workouts_path = '/api/user/{userId}/workouts'
workout_path = '/api/workout/{workoutId}'
ride_path = '/api/ride/{rideId}/details'


def handle_response(response, error_message):
    if response.status_code != 200:
        print(f"{error_message}. Response: {response.json()}")
        return None
    data = response.json()
    if VERBOSE_MODE:
        print(json.dumps(data, indent=4))
    return data


def create_session(username, password):
    login_url = base_url + login_path
    data = {"username_or_email": username, "password": password}
    session = requests.Session()
    response = session.post(login_url, json=data)
    user_data = handle_response(response, "Failed to create session")
    user_id = user_data['user_id'] if user_data else None
    return session, user_id


def get_user_workouts(session, user_id):
    url = base_url + workouts_path.replace("{userId}", user_id)
    response = session.get(url)
    return handle_response(response, "Failed to fetch user workouts")


def get_workout_details(session, workout_id):
    url = base_url + workout_path.replace("{workoutId}", workout_id)
    response = session.get(url)
    return handle_response(response, "Failed to fetch workout details")


def get_ride_details(session, ride_id):
    url = base_url + ride_path.replace("{rideId}", ride_id)
    response = session.get(url)
    return handle_response(response, "Failed to fetch ride details")


def main():
    session, user_id = create_session(username, password)
    if session is None:
        print("Login unsuccessful. Exiting...")
        return
    print("Successfully logged in and session created")

    workouts = get_user_workouts(session, user_id)
    if workouts is None or not workouts['data']:
        print("No workouts fetched. Exiting...")
        return
    print(f"Fetched {len(workouts['data'])} user workouts")

    workout_id = workouts['data'][0]['id']
    workout_details = get_workout_details(session, workout_id)
    if workout_details is None:
        print("No workout details fetched for workout id: "+str(workout_id))
        return
    print(f"Successfully fetched details for workout id: {workout_id}")

    ride_id = workout_details['ride']['id']
    ride_details = get_ride_details(session, ride_id)
    if ride_details is None:
        print("No ride details fetched for ride id: "+str(ride_id))
        return
    print(f"Successfully fetched ride details for ride id: {ride_id}")


if __name__ == "__main__":
    main()
# Peloton Unofficial API Python Wrapper
This Python wrapper unofficially interacts with Peloton's undocumented API, showing how one can programmatically interact with the service where no official API documentation or client libraries exist. 

Given the lack of official support, this wrapper aims to be considerate of their service by keeping network requests to minimum and introducing delay between calls. 

## Pre-Requisites
- Python 3 installed on your machine.
- The necessary dependencies installed via pip:
  - json
  - requests
  - dotenv
  - os
  - colorama
  - time
  - re
- `PELOTON_USERNAME` and `PELOTON_PASSWORD` environment variables correctly setup for session login.

## What it does
The wrapper script performs a series of steps as described below:

1. **Login**: Logs into Peloton using provided credentials(from environment variables) and fetches a session and user ID, which are used in most of the API requests.

2. **Load Endpoints**: Loads endpoints from a file named `base_endpoints.json` which lists all available APIs to be tested.

3. **Preprocess Endpoints**: Pre-processes these endpoints, specifically looking for dynamic variables identifiable by "{...}" (e.g., "userId" in "/api/user/{userId}/image_upload_url"). 

4. **Divide Endpoints**: Divides these pre-processed endpoints into two categories:
   - `ready_to_test`: Endpoints that don't need any more parameters to be filled.
   - `parameters_needed`: Endpoints that still need one or more parameters.

5. **Test Endpoints**: Runs through each endpoint in the `ready_to_test` category, making the appropriate requests, handling responses, and taking note of the results.

6. **Record Test Results**: It then records the test results of these endpoints in a temporary .json file, along with failure details if they failed.

7. **Finalize and Save Results**: Upon completion, it saves the testing results by renaming a temporary .json file to `queried_endpoints.json`. 

8. **Report**: Outputs to the console with the count of successful, failed, and incomplete calls.

## Usage
This script is standalone and easy to run. Ensure that you've set up the necessary environment variables:

```
$ python test_endpoints.py
```
This command will run the script, log into Peloton, process the endpoints, and start testing them while providing console log updates as it progresses.

## Notes
1. It should be remembered that Peloton does **NOT** provide a documented API, and as such, heavy usage or interaction can have potential impacts. 

2. This script outlines a considerate approach to interacting with such APIs, including design elements such as pacing requests (leaving delay between each requests).

3. If you are going to use this script or parts of it, ensure that you remain considerate of the data you are accessing, and use it responsibly.

## Contribution
The script is open to improvements and enhancements. If you have a great idea or notice something that could be made better, pull requests are welcome. 
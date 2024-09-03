# VertTracker API
The VertTracker API is a RESTful API designed to be a convenient tool to help athletes, coaches, and fitness enthusiasts track and analyze vertical jump performance. This API allows users to log their vertical jump measurements, view progress summaries, and gain insights into their performance over time. The VertTracker API computes users' vertical jumps based on their hang times – how long they remain off the ground during their jumps. By simply timing their jumps, users can easily measure their vertical jump performance with minimal setup.

## Usage
Since this API is not deployed and does not have a live database, a sample SQLite database, `sample.db`, that contains sample data has been provided within the `instances` folder. This allows you to test and explore the API endpoints locally.

**1. Run the Application**: To get started, simply execute the `run.py` file. A server will be hosted on `http://127.0.0.1:5000` from which the API endpoints can be called.

**2. Call Endpoints**: Send requests to the API by appending the endpoint URLs to the base URL. Using an API client tool such as Postman is recommended for ease of use.

## Endpoints
### 1. **Register User**
- **URL**: `/api/register`
- **Method**: `POST`
- **Description**: Registers user into the database.
- **Request Content Type**: `application/json`
- **Request Body**: The request body should contain a JSON object with the following fields:
  ```json
  {
    "username": "string",
    "password": "string",
    "tip-toe": 0.07
  }
  ```
  - **Fields**:
    - **username** (string, required): The unique username of the user. Must be from 1 to 20 characters long.
    - **password** (string, required): The password for the user account. Must be from 10 to 80 characters long.
    - **tip-toe** (int, required): The height difference (in meters) between the user's standing reach and tip-toe reach. Must be a positive floating point value. Used to calculate vertical jump height.
- **Responses**:
  - **200 OK**: Returns a JSON object.
    ```json
    {
      "msg": "registration success"
    }
    ```
  - **400 Bad Request**: Indicates a problem with the request body.
  - **500 Internal Server Error**: Indicates a problem with the server.
 


    
### 2. **Login User**
- **URL**: `/api/login`
- **Method**: `POST`
- **Description**: Authenticates a user and returns a JWT access token.
- **Request Content Type**: `application/json`
- **Request Body**: The request body should contain a JSON object with the following fields:
  ```json
  {
    "username": "string",
    "password": "string",
  }
  ```
  - **Fields**:
    - **username** (string, required): The unique username of the user.
    - **password** (string, required): The password for the user account.
- **Responses**:
  - **200 OK**: Returns a JSON object.
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcyNTAzMzU4NSwianRpIjoiZDEwNTM2NzYtMjBlZC00ZjJlLWEyY2YtMDJhMDY0NjQyMmU5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6MSwibmJmIjoxNzI1MDMzNTg1LCJjc3JmIjoiZTAzY2MxYzctNDg4Yy00MDQ2LTliNTItOGRlMjllNWZhMTgxIiwiZXhwIjoxNzI1MDM0NDg1fQ.eEsTkL7NCOO3WOwSw-MOVSj-z0knlY_jkTnDLOlOV5A"
    }
    ```
  - **401 Unauthorized**: Indicates either an incorrect username or password.
  - **500 Internal Server Error**: Indicates a problem with the server.




### 3. **Record Jump**
- **URL**: `/api/record-jump`
- **Method**: `POST`
- **Description**: Records a user's vertical jump measurement in the database.
- **Authorization Required**
  - **Authentication Type**: Bearer Token (JWT)
  - **Header Format**: `Authorization: Bearer <token>`
- **Request Content Type**: `application/json`
- **Request Body**: The request body should contain a JSON object with the following fields:
  ```json
  {
    "variant": "string",
    "hang-time": 0.80,
    "body-weight": 73.0,
    "note": "string"
  }
  ```
  - **Fields**:
    - **variant** (string, required): The jump variant. Must be either `"MAX"` (maximum approach jump) or `"CMJ"` (counter movement jump).
    - **hang-time** (float, required): The hang time – how long the user remains off the ground during their jump – (in seconds). Must be a positive floating point value.
    - **body-weight** (float, required): The body weight (in kilograms) of the user at the time of the jump. Must be a positive floating point value.
    - **note** (string, optional): The user's note about the jump attempt. If omitted, defaults to null.
- **Responses**:
  - **200 OK**: Returns a JSON object.
    ```json
    {
      "msg": "jump recorded successfully"
    }
    ```
  - **400 Bad Request**: Indicates a problem with the request body.
  - **500 Internal Server Error**: Indicates a problem with the server.
 


### 4. **Get Jumps** 
- **URL**: `/api/jumps`
- **Method**: `GET`
- **Description**: Queries the database for the user's jump records based on the query parameters.
- **Authorization Required**
  - **Authentication Type**: Bearer Token (JWT)
  - **Header Format**: `Authorization: Bearer <token>`
- **Parameters**:
  - **variant** (string, optional): The jump variant. Must be either `"MAX"` (maximum approach jump) or `"CMJ"` (counter movement jump). If omitted, queries all jump variants. Must not be omitted when using the `"avg"` aggregation.
  - **aggregation** (string, optional): The aggregation method for aggregating multiple jumps in a single day. Must be either `"avg"` (average) or  `"max"` (maximum). If omitted, queries all jump records without aggregation. The variant must not be omitted when using the `"avg"` aggregation.
  - **height-unit** (string, optional): The unit of measurement for jump height. Must be either `"cm"` (centimeters), `"m"` (meters), or `"in"` (inches). If omitted, defaults to meters.
  - **weight-unit** (string, optional): The unit of measurement for body weight. Must be either `"kg"` (kilograms) or `"lbs"` (pounds). If omitted, defaults to kilograms.
  - **order-by** (string, optional): The order in which the queried jump records are listed. Must be either `"date"` (ascending date), `"weight"` (ascending weight), or `"height"` (ascending jump height). If omitted, defaults to `"date"`.
  - **utc-offset** (int, optional): The UTC offset hours for a timezone. Must be an integer from -12 to 14. If omitted, defaults to UTC+00:00.
- **Responses**:
  - **200 OK**: Returns a list of JSON objects.
    ```json
    [
      {
        "date": "Mon 03 Jun 2024",
        "height": 32.0,
        "variant": "CMJ",
        "weight": 68.0,
        "note": null
      },
      {
        "date": "Fri 25 Aug 2024",
        "height": 28.0,
        "variant": "MAX",
        "weight": 75.5,
        "note": "Jumped well but felt a bit tired"
      },
      {
        "date": "Tue 10 Sep 2024",
        "height": 30.5,
        "variant": "CMJ",
        "weight": 70.0,
        "note": "Good jump with slight improvement"
      }
    ]
    ```
  - **400 Bad Request**: Indicates a problem with the request body.
  - **500 Internal Server Error**: Indicates a problem with the server.


### 5. **Generate Plot** 
- **URL**: `/api/plot`
- **Method**: `GET`
- **Description**: Generates a plot showing the user's jump progress over time.
- **Authorization Required**
  - **Authentication Type**: Bearer Token (JWT)
  - **Header Format**: `Authorization: Bearer <token>`
- **Parameters**:
  - **variant** (string, optional): The jump variant. Must be either `"MAX"` (maximum approach jump) or `"CMJ"` (counter movement jump). If omitted, defaults to `"MAX"`.
  - **aggregation** (string, optional): The aggregation method for aggregating multiple jumps in a single day. Must be either `"avg"` (average) or  `"max"` (maximum). If omitted, defaults to `"max"`.
  - **height-unit** (string, optional): The unit of measurement for jump height. Must be either `"cm"` (centimeters), `"m"` (meters), or `"in"` (inches). If omitted, defaults to meters.
  - **utc-offset** (int, optional): The UTC offset hours for a timezone. Must be an integer from -12 to 14. If omitted, defaults to UTC+00:00.
  - **Responses**:
    - **200 OK**: Returns Content-Type: `image/png`
    ![Sample Response](https://i.ibb.co/ZmtZCtq/3-Un3-CNzy-D.png)
    - **400 Bad Request**: Indicates a problem with the request body.
    - **500 Internal Server Error**: Indicates a problem with the server.




### 6. **Show Summary**
- **URL**: `/api/summary`
- **Method**: `GET`
- **Description**: Provides a summary of the user's vertical jump progress.
- **Authorization Required**
  - **Authentication Type**: Bearer Token (JWT)
  - **Header Format**: `Authorization: Bearer <token>`
- **Parameters**:
  - **height-unit** (string, optional): The unit of measurement for jump height. Must be either `"cm"` (centimeters), `"m"` (meters), or `"in"` (inches). If omitted, defaults to meter.
- **Responses**:
  - **200 OK**: Returns a JSON object.
    ```json
    {
      "num-records": 45,
      "num-days": 30,
      "highest-jump": {
        "height": 79.5,
        "date": "2024-08-15"
      },
      "last-jump": {
        "height": 75.2,
        "date": "2024-08-29"
      },
      "improvement": {
        "6-months": 3.2,
        "12-months": 5.4,
        "24-months": 7.1
      }
    }
    ```
  - **500 Internal Server Error**: Indicates a problem with the server.
  

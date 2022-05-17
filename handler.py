from datetime import datetime
import boto3
from io import BytesIO
import os
import uuid
import json

s3 = boto3.client("s3")
dynamodb = boto3.resource('dynamodb', region_name=str(os.environ['REGION_NAME']))
dbtable = str(os.environ["DYNAMODB_TABLE"])


def workout_log(event, context):
    # parse event
    print("EVENT:::", event)
    workout_event = event["body"]
    workout = json.loads(workout_event)
    # store parameters
    date = workout['date']
    exercise = workout['exercise']
    sets = workout['sets']
    reps = workout['reps']
    # add item to table
    table = dynamodb.Table(dbtable)
    unique_id = str(uuid.uuid4())
    table.put_item(
        Item={
            'id': unique_id,
            'exercise': str(exercise),
            'sets': str(sets),
            'reps': str(reps),
            'createdAt': str(datetime.now())
        }
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': 'Workout added successfully - ' + unique_id
    }


def workout_list(event, context):
    # get all workouts
    table = dynamodb.Table(dbtable)
    response = table.scan()
    data = response['Items']
    # paginate through the results in a loop
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data)
    }


def workout_search(event, context):
    workout_id = event['pathParameters']['id']

    # Set the default error response
    response = {
        "statusCode": 500,
        "body": f"An error occured while getting workout {workout_id}"
    }

    table = dynamodb.Table(dbtable)
    workout = table.get_item(Key={
        'id': workout_id
    })
    #workout = str(workout)
    print(workout)

    if 'Item' not in workout:
        print("workout doesn't exist")
        response = {
            "statusCode": 404,
            'headers': {'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'},
            'body': 'could not find the post'}
    else:
        response = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(workout),
            'isBase64Encoded': False,
        }
    
    return response


def workout_delete(event, context):
    workout_id = event['pathParameters']['id']

    # Set the default error response
    response = {
        "statusCode": 500,
        "body": f"An error occured while deleting workout {workout_id}"
    }

    # check if the workout exists
    table = dynamodb.Table(dbtable)
    workout = table.get_item(Key={
        'id': workout_id
    })
    #workout = str(workout)
    print(workout)

    if 'Item' not in workout:
        print("workout doesn't exist")
        response = {
            "statusCode": 404,
            'headers': {'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'},
            'body': 'could not find the post',
        }
    elif workout_id in workout["Item"]["id"]:
        print("found workout, deleting it")
        table = dynamodb.Table(dbtable)
        response = table.delete_item(Key={
            'id': workout_id
        })
        response_200 = {
            "deleted": True,
            "itemDeletedId": workout_id
        }
        response = {
            "statusCode": 200,
            'headers': {'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(response_200)
        }

    return response


def delete_all_the_things(event, context):
    
    #get the table keys
    table = dynamodb.Table(dbtable)
    tableKeyNames = [key.get("AttributeName") for key in table.key_schema]

    projectionExpression = ", ".join('#' + key for key in tableKeyNames)
    expressionAttrNames = {'#'+key: key for key in tableKeyNames}
    
    counter = 0
    page = table.scan(ProjectionExpression=projectionExpression, ExpressionAttributeNames=expressionAttrNames)
    with table.batch_writer() as batch:
        while page["Count"] > 0:
            counter += page["Count"]
            # Delete items in batches
            for itemKeys in page["Items"]:
                batch.delete_item(Key=itemKeys)
            # Fetch the next page
            if 'LastEvaluatedKey' in page:
                page = table.scan(
                    ProjectionExpression=projectionExpression, ExpressionAttributeNames=expressionAttrNames,
                    ExclusiveStartKey=page['LastEvaluatedKey'])
            else:
                break
    deletions = (f"Deleted {counter}")

    if int(counter) > 0:
        counter_string = str(counter)
        response = {
                "statusCode": 200,
                'headers': {'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'},
                'body': 'we deleted ' + counter_string + ' workout entries'
            }
    else:
        response = {
                "statusCode": 404,
                'headers': {'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'},
                'body': 'nothing to see here'
            }

    return response
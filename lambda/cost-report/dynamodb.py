import os
import boto3
from boto3.dynamodb.conditions import Attr, Key

import utils as u

REGION=os.environ.get('REGION')
COST_REPORT_DDB_TABLE_NAME = os.environ.get("COST_REPORT_DDB_TABLE_NAME")
PARTITION_KEY = "EnvironmentName"
SORT_KEY = "Owner"

def get_all_items(projection_expression=None):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table(COST_REPORT_DDB_TABLE_NAME)
        if projection_expression is None:
            response = table.scan()
        else:
            response = table.scan(ProjectionExpression=projection_expression)
        data = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])
        return data
    except Exception as e:
        print(e)
        print(f"Fetching App env from DynamoDB")
        raise e
        
    
def get_items_by_owner(owner):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table(COST_REPORT_DDB_TABLE_NAME)
        response = table.scan(FilterExpression=Attr('Owner').eq(owner))
        data = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])
        return data
    except Exception as e:
        print(e)
        print(f"Fetching App env from DynamoDB")
        raise e
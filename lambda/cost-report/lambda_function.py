import json
import os
import logging
import boto3

import utils
import dynamodb
import ses

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

AWS_ACCOUNT_ALIAS_MAX_CHAR = 50
REGION =  os.environ.get("REGION")

# iam
iam_client = boto3.client('iam')

# S3
s3 = boto3.resource('s3')
COST_REPORT_S3_BUCKET_NAME = os.environ.get("COST_REPORT_S3_BUCKET_NAME")

# DynamoDB
dynamodb_client = boto3.client('dynamodb')

# CostExplorer
ce_client = boto3.client('ce')

# SES
ses_client = boto3.client('ses',region_name=REGION)


def lambda_handler(event, context):
    # Get a list of App env owners from DynamoDB
    all_items = dynamodb.get_all_items(projection_expression="Owner")
    owners = set([item.get('Owner') for item in all_items ])
    num_owners = len(owners)
    print(f"Got: {num_owners} owners from DynamoDB: {owners}")
    
    # Get AWS account number
    aws_account_id = context.invoked_function_arn.split(":")[4]
    account_alias = utils.get_aws_account_alias(iam_client)
    if len(account_alias) > AWS_ACCOUNT_ALIAS_MAX_CHAR:
      account_alias = account_alias[0:AWS_ACCOUNT_ALIAS_MAX_CHAR]
    aws_account_name = account_alias + '--AcctID-' + aws_account_id 
    print(f"Account account name: {aws_account_name}")

    all_envs_summary = []
    all_envs_to_optimize_ec2 = []
    # Get App env for individual owners
    for owner in owners:
      env_items = dynamodb.get_items_by_owner(owner)
      print("Found: " + str(len(env_items)) + " App envs for: " + owner)
      owner_envs_summary = utils.get_envs_summary(env_items)
      all_envs_summary.extend(owner_envs_summary)
      envs_to_optimize_ec2 = utils.get_envs_to_optimize(env_items)
      if envs_to_optimize_ec2:
        all_envs_to_optimize_ec2.extend(envs_to_optimize_ec2)
      
      ## Generate App env report
      report_path =  ('App-Cost-Report-' + aws_account_name + '--Creator-' + owner + '-' +  utils.get_today_date() + '.xlsx')
      report_file_path = utils.generate_report_by_owner_xls(env_items, report_path)
      
      # Upload report to S3
      s3_report_path = (owner + '/' + report_path)
      s3.meta.client.upload_file(report_file_path, COST_REPORT_S3_BUCKET_NAME, s3_report_path)
      print("S3 Upload Done App ENV for: " + owner )

    ## Generate App env report and upload to S3
    report_path = ('App-Cost-Report-Acct--' + aws_account_name + '--' + utils.get_today_date() + '.xlsx')
    report_file_path = utils.generate_summary_report_xls(all_envs_summary, report_path,  
                                                         all_envs_to_optimize_ec2)
    s3_report_path = 'Summary-Report/' + report_path
    s3.meta.client.upload_file(report_file_path, COST_REPORT_S3_BUCKET_NAME, s3_report_path)
    print("S3 Upload Summary Report for : " + utils.get_today_date() )

    
    # Send SNS Message to SNS Topic subscribers
    subject = "[" + aws_account_name + "] App Cost Report - " +  utils.get_today_date() # subject must be be < 100 chars
    obj_path = "https://s3.console.aws.amazon.com/s3/object/" + COST_REPORT_S3_BUCKET_NAME + "?region=" + REGION + "&prefix=" + s3_report_path
    msg = "Your App AWS Cost Optimization Report is available at the below URL (Please login to AWS Console before clicking it): " + obj_path

    # send email
    ses.send_email(ses_client, subject, report_file_path)
    print("END")
               
    return {
        'statusCode': 200,
        'body': json.dumps('Finished Running AWS Cost Optimization Report Lambda Function!')
    }

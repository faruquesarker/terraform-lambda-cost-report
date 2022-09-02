import datetime
import operator
from socket import ALG_OP_DECRYPT
import xlsxwriter
import logging

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

CREATOR_REPORT_WORKSHEET_NAME = "Creator Report"
SUMMARY_REPORT_WORKSHEET_NAME = "Summary Report"
EC2_RECOMMENDATION_WORKSHEET_NAME = "EC2 Recommendation"
RDS_RECOMMENDATION_WORKSHEET_NAME = "RDS Recommendation"
LB_RECOMMENDATION_WORKSHEET_NAME = "LB Recommendation"

REPORT_FILE_PATH_PREFIX = '/tmp/'

## EC2 Service Constants
EC2_OPTIMIZE_ITEM_PREFIX = "OptimizeIdleEC2"
EC2_INSTANCE_ID = "Instance ID"
EC2_INSTANCE_NAME = "Instance Name"
EC2_INSTANCE_TYPE = "Instance Type"
EC2_REGION = "Region/AZ"
EC2_SAVINGS = "Estimated Monthly Savings"
EC2_LOW_UTIL_DAYS = "Number of Days Low Utilization"
EC2_AVG_NET_IO = "14-Day Average Network I/O"
EC2_AVG_CPU = "14-Day Average CPU Utilization"

## RDS Service Constants
RDS_OPTIMIZE_ITEM_PREFIX = "OptimizeIdleRDS"
RDS_REGION = "Region"
RDS_DB_INSTANCE_NAME = "DB Instance Name"
RDS_MULTI_AZ = "Multi-AZ"
RDS_INSTANCE_TYPE = "Instance Type"
RDS_STORAGE_PROVISINED = "Storage Provisioned (GB)"
RDS_LAST_CONNECTION = "Days Since Last Connection"
RDS_SAVINGS = "Estimated Monthly Savings (On Demand)"

## ELB Service Constants
LB_OPTIMIZE_ITEM_PREFIX = "OptimizeIdleLB"
LB_REGION = "Region"
LB_NAME = "Load Balancer Name"
LB_REASON = "Reason"
LB_SAVINGS = "Estimated Monthly Savings"

def get_aws_account_alias(iam_client):
    try:
        #print("Fetching AWS Account alias..")
        response = iam_client.list_account_aliases()
        alias = response.get('AccountAliases')
        return alias[0] if alias else 'Account Alias Unset'
    except Exception as e:
        print(e)
        print(f"Error fetching AWS Account alias..")
        raise e

def get_today_date():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_month_end_date():
    now = datetime.datetime.now()
    month_end_date = datetime.date(now.year, 1 if now.month==12 else now.month+1, 1) - datetime.timedelta(days=1)
    return month_end_date.strftime("%Y-%m-%d")

def get_last_month_start_date():
    now = datetime.datetime.now()
    month_start_date = datetime.date(now.year-1 if now.month==1 else now.year , 12 if now.month==1 else now.month-1, 1)
    return month_start_date.strftime("%Y-%m-%d")

def setup_xls_workbook(report_file_name, worksheet_name):
    # Create an new Excel file and add a worksheet
    workbook = xlsxwriter.Workbook(REPORT_FILE_PATH_PREFIX + report_file_name)
    worksheet = workbook.add_worksheet(worksheet_name)

    # Widen the first column to make the text clearer.
    worksheet.set_column(0, 5, 40)

    return (workbook, worksheet)

def get_cell_format(workbook):
    cell_format = workbook.add_format()
    cell_format.set_font_size(16)
    cell_format.set_bold()
    return cell_format


def setup_report_header(workbook, worksheet, row_num=0):
    # Add a bold format to use to highlight cells.
    cell_format = get_cell_format(workbook)

    # Write header -> row_num = 0
    header = ['Environment Name', 'Creation Date', 'Creator', 'Current month costs ($)', 'Forecasted month end costs ($)', 'Last month costs ($)']
    for col_num, data in enumerate(header):
        worksheet.write(row_num, col_num, data, cell_format)
    return (workbook, worksheet)

def generate_report_by_creator_xls(env_items, report_file_name ):
    # Initialize xls workbok
    (workbook, worksheet) = setup_xls_workbook(report_file_name, worksheet_name=CREATOR_REPORT_WORKSHEET_NAME)

    bold = workbook.add_format({'bold': True})
    cell_format = get_cell_format(workbook)

    # Sort env items based on current cost
    sorted_env_items = sorted(env_items,  key=operator.itemgetter("Cost.CurrentMonth"), reverse=True)

    # Write each env items
    row_num = 0
    for mpdk_env in sorted_env_items:
        # Setup workbook header
        (workbook, worksheet) = setup_report_header(workbook, worksheet, row_num)
        # Write resources
        # Write the values of env summary
        row_num += 1
        row = [mpdk_env.get('EnvironmentName'), mpdk_env.get('CreationDate'), mpdk_env.get('Creator'), 
               mpdk_env.get('Cost.CurrentMonth'), mpdk_env.get('Cost.ProjectionMonthEnd'), mpdk_env.get('Cost.LastMonth')]
        for col_num, data in enumerate(row):
            worksheet.write(row_num, col_num, data, cell_format)
        
        # Add header/sub-headers for resources
        row_num += 1
        worksheet.write(row_num, 0, "Resources", bold)
        row_num += 1
        row_header = ["Identifier", "Tag: Name", "Service", "Type", "Region", "Tag: Creator", "Tag: Environment_id", 
                      "Tag: Environment_type", "Tag: Expiration", "Tag: Owner", "Tag:Product", "Tag: Version", "Tag: Launched_by", "Tags"]
        for col_num, data in enumerate(row_header):
            worksheet.write(row_num, col_num, data, bold)
        
        # Generate a list of resources for each env item
        resources = []
        for item in mpdk_env:
            if 'Resource' in item:
                resources.append(mpdk_env.get(item))
        for res in resources:
            # Writing data about resources
            identifier = res.get("Identifier")
            tag_name = res.get('Tag.Name')
            service = res.get('Service')
            type = res.get('Type')
            region = res.get('Region')
            creator = mpdk_env.get("Creator")
            environment_id =  res.get('Tag.EnvironmentId', None)
            environment_type =  res.get('Tag.EnvironmentType', None)
            expiration = res.get('Tag.Expiration', None)
            owner = res.get('Tag.Owner', None)
            product = res.get('Tag.Product', None)
            version = res.get('Tag.Version', None)
            launched_by = res.get('TagLaunched_by', None)
            tags = res.get('Tags', None)
            row_data = [identifier, tag_name, service, type, region, creator, environment_id, environment_type, expiration, owner, product, version, launched_by, tags]
            row_num += 1
            for col_num, data in enumerate(row_data):
                worksheet.write(row_num, col_num, data)
            
        # Add an empty line
        row_num += 1
        worksheet.write(row_num, 0, " ")
    workbook.close()
    report_file_path = REPORT_FILE_PATH_PREFIX + report_file_name
    return report_file_path

def get_envs_summary(updated_env_items):
    envs_summary = []
    for mpdk_env in updated_env_items:
        env_summary = {k: v for k, v in mpdk_env.items() if not k.startswith('Resource')}
        envs_summary.append(env_summary)
    return envs_summary

def update_estimated_savings(mpdk_env):
    print(f"Optimize Env details ->")
    total_est_savings_ec2 = total_est_savings_rds = total_est_savings_lb = 0
    for k,v in mpdk_env.items():
        if k.startswith(EC2_OPTIMIZE_ITEM_PREFIX):
            savings = v.get(EC2_SAVINGS)
            if '$' in savings:
                savings = savings[1:] # Get rid of $ prefix
            total_est_savings_ec2 += float(savings)
        elif k.startswith(RDS_OPTIMIZE_ITEM_PREFIX):
            savings = v.get(RDS_SAVINGS)
            if '$' in savings:
                savings = savings[1:] # Get rid of $ prefix
            total_est_savings_rds += float(savings)
        elif k.startswith(LB_OPTIMIZE_ITEM_PREFIX):
            savings = v.get(LB_SAVINGS)
            if '$' in savings:
                savings = savings[1:] # Get rid of $ prefix
            total_est_savings_lb += float(savings)
    if total_est_savings_ec2 > 0:
        mpdk_env[EC2_SAVINGS] = round(total_est_savings_ec2, 2)
    if total_est_savings_rds > 0:
        mpdk_env[RDS_SAVINGS] = round(total_est_savings_rds, 2)
    if total_est_savings_lb > 0:
        mpdk_env[LB_SAVINGS] = round(total_est_savings_lb, 2)
    return mpdk_env
            
def get_envs_to_optimize(env_items):
    envs_to_optimize_ec2 = []
    for mpdk_env in env_items:
        added_to_ec2 = added_to_rds = added_to_lb = False
        for k in list(mpdk_env.keys()):
            if k.startswith(EC2_OPTIMIZE_ITEM_PREFIX) and not added_to_ec2:
                # Get the sum of potential savings
                updated_mpdk_env = update_estimated_savings(mpdk_env) 
                envs_to_optimize_ec2.append(updated_mpdk_env)
                added_to_ec2 = True
            
    return envs_to_optimize_ec2

def write_row(worksheet, data_line_num, row, cell_format=None):
    # Write data
    for col_num, data in enumerate(row):
        if cell_format: 
            worksheet.write(data_line_num, col_num, data, cell_format)
        else:
            worksheet.write(data_line_num, col_num, data)
    return data_line_num + 1

def add_summary_report_worksheet(workbook, worksheet, envs_summary):
    # Setup header
    workbook, worksheet = setup_report_header(workbook, worksheet)
    ## Write data
    current_sum, projected_sum, last_sum = 0.00, 0.00, 0.00
    data_line_num = 1
    sorted_envs_summary = sorted(envs_summary,  key=operator.itemgetter("Cost.CurrentMonth"), reverse=True)
    for mpdk_env in sorted_envs_summary:
        # Writing headers of report file
        row = [mpdk_env.get('EnvironmentName'), mpdk_env.get('CreationDate'), mpdk_env.get('Creator'), 
                mpdk_env.get('Cost.CurrentMonth'), mpdk_env.get('Cost.ProjectionMonthEnd'), mpdk_env.get('Cost.LastMonth')]
        for col_num, data in enumerate(row):
            worksheet.write(data_line_num, col_num, data)
        data_line_num += 1

        # Calculate cost sum
        current = float(mpdk_env.get('Cost.CurrentMonth'))
        if current > 0:
            current_sum += current
        projected = float(mpdk_env.get('Cost.ProjectionMonthEnd'))
        if projected > 0:
            projected_sum += projected
        last = float(mpdk_env.get('Cost.LastMonth'))
        if last > 0 :
            last_sum += last
    worksheet.write(data_line_num, 0, ' ')
    sum_row = ["","","Total",current_sum, projected_sum, last_sum]
    cell_format = get_cell_format(workbook)
    for col_num, data in enumerate(sum_row):
        worksheet.write(data_line_num + 1, col_num, data, cell_format)
    return workbook

def add_ec2_recommendation_worksheet(workbook, all_envs_to_optimize_ec2):
    ## Add Cost Optimization info in another workbook, if any ec2 optimzation found
    if all_envs_to_optimize_ec2:
        worksheet = workbook.add_worksheet(EC2_RECOMMENDATION_WORKSHEET_NAME)
        # Widen the first column to make the text clearer.
        worksheet.set_column(0, 7, 45)
        bold = workbook.add_format({'bold': True})

        # Sort the envs based on potential savings
        sorted_envs_to_optimize = sorted(all_envs_to_optimize_ec2,  key=operator.itemgetter(EC2_SAVINGS), reverse=True)

        data_line_num = 0
        for mpdk_env in sorted_envs_to_optimize:
            # Writing headers
            row = ["Environment: %s" %str(mpdk_env.get('EnvironmentName')), 
                   "Creator: %s" %str(mpdk_env.get('Creator')), 
                   "Total Est. Monthly Savings: $%s" %str(mpdk_env.get(EC2_SAVINGS))
                  ]
            data_line_num = write_row(worksheet, data_line_num, row, get_cell_format(workbook))
            # write sub-headers
            row = [EC2_INSTANCE_ID, EC2_INSTANCE_NAME, EC2_SAVINGS, 
                   EC2_LOW_UTIL_DAYS, EC2_REGION,  EC2_INSTANCE_TYPE,  
                   EC2_AVG_CPU, EC2_AVG_NET_IO]
            data_line_num = write_row(worksheet, data_line_num, row, bold)
            # Write recommendations
            for k,v in mpdk_env.items():
                if EC2_OPTIMIZE_ITEM_PREFIX in k:
                    row = [v.get(EC2_INSTANCE_ID), v.get(EC2_INSTANCE_NAME), 
                           v.get(EC2_SAVINGS), v.get(EC2_LOW_UTIL_DAYS),
                           v.get(EC2_REGION), v.get(EC2_INSTANCE_TYPE),
                           v.get(EC2_AVG_CPU), v.get(EC2_AVG_NET_IO)]
                    data_line_num =  write_row(worksheet, data_line_num, row)
            # add an empty line
            worksheet.write(data_line_num, 0, ' ')
            data_line_num += 1
    return workbook

def generate_summary_report_xls(envs_summary, report_file_name,  envs_optimize_ec2):
    # Initialize xls workbook
    workbook, worksheet = setup_xls_workbook(report_file_name, worksheet_name=SUMMARY_REPORT_WORKSHEET_NAME)
    # Add Symmary report tab
    workbook = add_summary_report_worksheet(workbook, worksheet, envs_summary)

    # Add EC2 Recommendation
    workbook = add_ec2_recommendation_worksheet(workbook, envs_optimize_ec2)

    workbook.close()

    report_file_path = REPORT_FILE_PATH_PREFIX + report_file_name
    return report_file_path
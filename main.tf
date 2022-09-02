## Create necessary Infrastructure for deploying Lambda
# S3 bucket
resource "random_pet" "lambda_bucket_name" {
  prefix = "aws-cost-optimization"
  length = 4
}

resource "aws_s3_bucket" "lambda_bucket" {
  bucket = random_pet.lambda_bucket_name.id

  acl           = "private"
  force_destroy = true

  tags = var.tags
}

# Retrieve DynamoDB table data
data "aws_dynamodb_table" "current" {
  name = var.dynamodb_table_name
}

# IAM policies and roles
resource "aws_iam_policy" "policy_cost_report_lambda_exec_01" {
  name = "terraform-lambda-cost-report-exec-01"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "iam:ListAccountAliases",
          "ses:SendRawEmail",
          "cloudformation:ListStackResources",
          "cloudformation:DescribeStacks",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = ["dynamodb:BatchGetItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchWriteItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DescribeTable",
          "dynamodb:CreateTable",
          "dynamodb:DeleteTable",
        ]
        Effect = "Allow"
        # just a comment
        Resource = "${data.aws_dynamodb_table.current.arn}"
      },
      {
        "Sid" : "ListObjectsInBucket",
        "Effect" : "Allow",
        "Action" : ["s3:ListBucket"],
        "Resource" : "${aws_s3_bucket.lambda_bucket.arn}"
      },
      {
        "Sid" : "AllObjectActions",
        "Effect" : "Allow",
        "Action" : ["s3:*Object"],
        "Resource" : "${aws_s3_bucket.lambda_bucket.arn}/*"
      },
    ]
  })

  tags = var.tags
}

resource "aws_iam_role" "lambda_exec" {
  name = "aws_cost_optimization_cost_report_lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      }
    ]
  })

  managed_policy_arns = [aws_iam_policy.policy_cost_report_lambda_exec_01.arn, ]

  tags = var.tags
}


# Cost-Report Lambda Fn and supporting inf
data "archive_file" "lambda_cost_report" {
  type = "zip"

  source_dir  = "${path.module}/lambda/cost-report"
  output_path = "${path.module}/lambda/cost-report.zip"
}

resource "aws_s3_bucket_object" "lambda_cost_report" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "cost-report.zip"
  source = data.archive_file.lambda_cost_report.output_path

  etag = filemd5(data.archive_file.lambda_cost_report.output_path)

  tags = var.tags
}

resource "aws_lambda_function" "cost_report" {
  function_name = "AWS-Cost-Optimization-Cost-Report"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_bucket_object.lambda_cost_report.key

  runtime = "python3.7"
  handler = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.lambda_cost_report.output_base64sha256

  role = aws_iam_role.lambda_exec.arn

  timeout = 900 # set to max value

  environment {
    variables = {
      "COST_REPORT_DDB_TABLE_NAME"        = data.aws_dynamodb_table.current.name,
      "COST_REPORT_S3_BUCKET_NAME"        = aws_s3_bucket.lambda_bucket.id,
      "COST_REPORT_VERIFIED_ADMIN_EMAILS" = jsonencode(var.verified_admin_emails),
      "COST_REPORT_SENDER_EMAIL_ADDRESS"  = var.sender_email_address
      "REGION"                            = var.aws_region
    }
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "cost_report" {
  name = "/aws/lambda/${aws_lambda_function.cost_report.function_name}"

  retention_in_days = 30

  tags = var.tags
}

## Add Lambda layers to allow Lambda functions accessing additional Python libraries

resource "aws_lambda_layer_version" "python37-xlsxwriter-layer" {
  filename            = "lambda/packages/Python3-xlsxwriter.zip"
  layer_name          = "Python3-xlsxwriter"
  source_code_hash    = filebase64sha256("lambda/packages/Python3-xlsxwriter.zip")
  compatible_runtimes = ["python3.6", "python3.7"]
}


#####  Scheduled Tasks #####
## Add Scheduled Tasks for Cost-Report lambda functions
resource "aws_cloudwatch_event_rule" "cost_report_event" {
  name                = "cost-report-event"
  description         = "Cost Optimization Cost Report Lambda - Fires at a given time"
  schedule_expression = var.cost_report_event_schedule
}

resource "aws_cloudwatch_event_target" "run_cost_report" {
  rule      = aws_cloudwatch_event_rule.cost_report_event.name
  target_id = "cost_report"
  arn       = aws_lambda_function.cost_report.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_cost_report" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_report.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cost_report_event.arn
}

resource "aws_ses_email_identity" "cost_report_ses_email_subscription" {
  count = length(var.admin_emails)
  email = var.admin_emails[count.index]
}
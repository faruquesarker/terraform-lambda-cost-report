variable "aws_region" {
  description = "Default AWS region for all resources."

  type    = string
  default = "eu-west-1"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table where resource info are stored"

  type    = string
  default = "AWSCostOptimization"
}


variable "tags" {
  description = "A map of tags to add to the resources"
  type        = map(string)
  default     = {}
}

variable "cost_report_event_schedule" {
  description = "CRON or rate expression for scheduling Cost-Report Lambda function"

  type    = string
  default = "cron(0 4 ? * SUN *)"
}

variable "admin_emails" {
  description = "Admin email addresses to send notifications"

  type = list(any)
}

variable "verified_admin_emails" {
  description = "Admin email addresses already verified by the subscribers"

  type = list(any)
}

variable "sender_email_address" {
  description = "Verified Email addresses to be used as sender"
  type        = string
}

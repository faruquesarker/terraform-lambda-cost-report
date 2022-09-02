import os
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Email addresses must be verified with Amazon SES.
SENDER = "AWS Cost Report <" +  os.environ.get('COST_REPORT_SENDER_EMAIL_ADDRESS') + ">"
RAW_RECIPIENTS = os.environ.get('COST_REPORT_VERIFIED_ADMIN_EMAILS')[1:-1]
RECIPIENTS = []
RECIPIENTS.extend([x for x in RAW_RECIPIENTS.split(",")])
RECIPIENTS = [x[1:-1] for x in RECIPIENTS]
# Testing verified emails
#RECIPIENTS = ['faruques@amdocs.com','isaacbe@amdocs.com']


# Specify a configuration set. If you do not want to use a configuration
# set, comment the following variable, and the 
# ConfigurationSetName=CONFIGURATION_SET argument below.
#CONFIGURATION_SET = "ConfigSet"

def send_email(ses_client, subject, attachment):
    print(f"Sending emails: from {SENDER}  to: {RECIPIENTS}")
    # The email body for recipients with non-HTML email clients.
    body_text = "Hello,\r\nPlease see the attached file for AWS MS360 cost report."

    # The HTML body of the email.
    BODY_HTML = """\
    <html>
    <head></head>
    <body>
    <h1>Hello!</h1>
    <p>Please see the attached file for MS360 AWS cost report.</p>
    </body>
    </html>
    """

    # The character encoding for the email.
    CHARSET = "utf-8"

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = subject 
    msg['From'] = SENDER 
    msg['To'] = ", ".join(RECIPIENTS)

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # Encode the text and HTML content and set the character encoding. This step is
    # necessary if you're sending a message with characters outside the ASCII range.
    textpart = MIMEText(body_text.encode(CHARSET), 'plain', CHARSET)
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)

    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    # Define the attachment part and encode it using MIMEApplication.
    att = MIMEApplication(open(attachment, 'rb').read())

    # Add a header to tell the email client to treat this part as an attachment,
    # and to give the attachment a name.
    att.add_header('Content-Disposition','attachment',filename=os.path.basename(attachment))

    # Attach the multipart/alternative child container to the multipart/mixed
    # parent container.
    msg.attach(msg_body)

    # Add the attachment to the parent container.
    msg.attach(att)
    #print(msg)
    try:
        #Provide the contents of the email.
        response = ses_client.send_raw_email(
            Source=SENDER,
            Destinations=RECIPIENTS,
            RawMessage={
                'Data':msg.as_string(),
            },
            #ConfigurationSetName=CONFIGURATION_SET
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
import boto3
import datetime
import dateutil
import os


def lambda_handler(event, context):
    region_name = os.environ['AWS_REGION']

    dc = boto3.client('directconnect', region_name=region_name)
    cw = boto3.client('cloudwatch', region_name=region_name)

    virtualInterfaces = dc.describe_virtual_interfaces(
        connectionId=event['connectionId']
    )['virtualInterfaces']

    for vi in virtualInterfaces:
        state = None
        if vi['virtualInterfaceState'] == 'available':
            state = 1
        else:
            state = 0

        cw.put_metric_data(
            Namespace='AWS/DX',
            MetricData=[
                {
                    'MetricName': 'BGPStatus',
                    'Dimensions': [{
                        'Name': 'VirtualInterfaceId',
                        'Value': vi['virtualInterfaceId']
                    }],
                    'Timestamp': datetime.datetime.now(dateutil.tz.tzlocal()),
                    'Value': state
                }
            ]
        )

    return True

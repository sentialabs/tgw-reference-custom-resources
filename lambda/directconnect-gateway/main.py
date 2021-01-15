import boto3
from crhelper import CfnResource


helper = CfnResource(sleep_on_delete=30)
dc = boto3.client('directconnect')


def lambda_handler(event, context):
    helper(event, context)


@helper.create
def create_dc_gateway(event, context):
    rp = event['ResourceProperties']

    # create direct connect gateway
    dc_gw = dc.create_direct_connect_gateway(
        directConnectGatewayName=(
            f'{rp["stack_name"]}DirectConnectGateway-{rp["environment"]}'
        ),
        amazonSideAsn=int(rp['direct_connect_gw_asn'])
    )

    helper.Data.update(
        {
            'DirectConnectGatewayId':
                dc_gw['directConnectGateway']['directConnectGatewayId']
        }
    )

    return dc_gw['directConnectGateway']['directConnectGatewayId']


@helper.update
def update_dc_gateway(event, context):
    rp = event['ResourceProperties']
    old_rp = event['OldResourceProperties']

    direct_connect_gw_id = event['PhysicalResourceId']

    if (
        rp['direct_connect_gw_asn'] != old_rp['direct_connect_gw_asn']
        or rp['stack_name'] != old_rp['stack_name']
        or rp['environment'] != old_rp['environment']
    ):
        # create direct connect gateway
        dc_gw = dc.create_direct_connect_gateway(
            directConnectGatewayName=(
                f'{rp["stack_name"]}DirectConnectGateway-{rp["environment"]}'
            ),
            amazonSideAsn=int(rp['direct_connect_gw_asn'])
        )

        # TODO The bellow will only work if there are no associations
        # delete old direct connect gateway
        dc_gw_nr_of_asoc = len(dc.describe_direct_connect_gateway_associations(
                directConnectGatewayId=direct_connect_gw_id
            )['directConnectGatewayAssociations']
        )
        if dc_gw_nr_of_asoc == 0:
            dc.delete_direct_connect_gateway(
                directConnectGatewayId=direct_connect_gw_id
            )

        # update direct_connect_gw_id var
        direct_connect_gw_id = (
            dc_gw['directConnectGateway']['directConnectGatewayId']
        )

        helper.Data.update(
            {
                'DirectConnectGatewayId':
                    direct_connect_gw_id
            }
        )

    return direct_connect_gw_id


@helper.poll_create
@helper.poll_update
def poll_gateway_creation_update(event, context):
    direct_connect_gw_id = event['CrHelperData']['DirectConnectGatewayId']

    dc_gw = dc.describe_direct_connect_gateways(
        directConnectGatewayId=direct_connect_gw_id
    )['directConnectGateways'][0]
    if dc_gw['directConnectGatewayState'] == 'available':
        return direct_connect_gw_id

    return False


@helper.delete
def delete_dc_gateway(event, context):
    direct_connect_gw_id = event['PhysicalResourceId']

    # delete direct connect gateway
    dc.delete_direct_connect_gateway(
        directConnectGatewayId=direct_connect_gw_id
    )

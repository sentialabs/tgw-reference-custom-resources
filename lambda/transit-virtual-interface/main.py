import boto3
from crhelper import CfnResource


helper = CfnResource(sleep_on_delete=30)
dc = boto3.client('directconnect')


def lambda_handler(event, context):
    helper(event, context)


@helper.create
def create_dc_resource_configuration(event, context):
    rp = event['ResourceProperties']

    dcc = dc.describe_connections(
        connectionId=rp['connectionId']
    )

    # Creaate Transit Virtual Interface
    tvi = dc.create_transit_virtual_interface(
        connectionId=rp['connectionId'],
        newTransitVirtualInterface={
            'virtualInterfaceName':
                f'{rp["stack_name"]}'
                f'TransitVirtualInterface-{rp["environment"]}',
            'vlan': dcc['connections'][0]['vlan'],
            'asn': int(rp['transit_virtual_interface_bgp_asn']),
            'addressFamily': 'ipv4',
            'directConnectGatewayId': rp['direct_connect_gw_id'],
        }
    )

    transit_virtual_interface_id = (
        tvi['virtualInterface']['virtualInterfaceId']
    )

    helper.Data.update(
        {
            'TransitVirtualInterfaceId':
                transit_virtual_interface_id
        }
    )

    return transit_virtual_interface_id


@helper.update
def update_dc_resource_configuration(event, context):
    transit_virtual_interface_id = event['PhysicalResourceId']

    helper.Data.update(
        {
            'TransitVirtualInterfaceId':
                transit_virtual_interface_id
        }
    )

    return transit_virtual_interface_id


@helper.delete
def delete_dc_resource_configuration(event, context):
    transit_virtual_interface_id = event['PhysicalResourceId']

    # delete direct connect gateway
    dc.delete_virtual_interface(
        virtualInterfaceId=transit_virtual_interface_id
    )


@helper.poll_create
@helper.poll_update
def cu_polling(event, context):
    rp = event['ResourceProperties']

    transit_virtual_interface_id = (
        event['CrHelperData']['TransitVirtualInterfaceId']
    )

    tvi = dc.describe_virtual_interfaces(
        connectionId=rp['connectionId'],
        virtualInterfaceId=transit_virtual_interface_id
    )['virtualInterfaces'][0]
    if tvi['virtualInterfaceState'] != 'pending':
        return transit_virtual_interface_id

    return False


@helper.poll_delete
def d_polling(event, context):
    rp = event['ResourceProperties']

    transit_virtual_interface_id = event['PhysicalResourceId']
    tvi_state_blacklist = ['deleted']

    tvis = dc.describe_virtual_interfaces(
        connectionId=rp['connectionId'],
        virtualInterfaceId=transit_virtual_interface_id
    )['virtualInterfaces']
    tvi_nr = len(
        [f for f in tvis if f['virtualInterfaceState'] not in tvi_state_blacklist]  # noqa: E501
    )
    if tvi_nr == 0:
        return True

    return False

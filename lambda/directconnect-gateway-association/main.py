import boto3
from crhelper import CfnResource


helper = CfnResource(sleep_on_delete=30)
dc = boto3.client('directconnect')


def lambda_handler(event, context):
    helper(event, context)


@helper.create
def create_dc_resource_configuration(event, context):
    rp = event['ResourceProperties']

    __allowedPrefixesToDirectConnectGateway = []
    for prefix in rp['allowed_prefixes_to_dc_gateway']:
        __allowedPrefixesToDirectConnectGateway.append(
            {
                'cidr': prefix
            }
        )

    dc_gw_association = dc.create_direct_connect_gateway_association(
        directConnectGatewayId=rp['direct_connect_gw_id'],
        gatewayId=rp['transit_gateway_id'],
        addAllowedPrefixesToDirectConnectGateway=(
            __allowedPrefixesToDirectConnectGateway
        )
    )

    association_id = (
        dc_gw_association['directConnectGatewayAssociation']['associationId']
    )

    helper.Data.update(
        {
            'DirectConnectGatewayAssociationId':
                association_id
        }
    )

    return association_id


@helper.update
def update_dc_resource_configuration(event, context):
    rp = event['ResourceProperties']
    old_rp = event['OldResourceProperties']

    direct_connect_gw_association_id = event['PhysicalResourceId']

    allowed_prefixes = rp['allowed_prefixes_to_dc_gateway']
    old_allowed_prefixes = old_rp['allowed_prefixes_to_dc_gateway']

    if (
        allowed_prefixes != old_allowed_prefixes
    ):

        __allowedPrefixesToDirectConnectGateway = []
        __disallowedPrefixesToDirectConnectGateway = []
        __allowedPrefixes = list(
            set(allowed_prefixes) - set(old_allowed_prefixes)
        )
        __disallowedPrefixes = list(
            set(old_allowed_prefixes) - set(allowed_prefixes)
        )
        for prefix in __allowedPrefixes:
            __allowedPrefixesToDirectConnectGateway.append(
                {
                    'cidr': prefix
                }
            )
        for prefix in __disallowedPrefixes:
            __disallowedPrefixesToDirectConnectGateway.append(
                {
                    'cidr': prefix
                }
            )

        dc_gw_association = dc.update_direct_connect_gateway_association(
            associationId=direct_connect_gw_association_id,
            addAllowedPrefixesToDirectConnectGateway=(
                __allowedPrefixesToDirectConnectGateway
            ),
            removeAllowedPrefixesToDirectConnectGateway=(
                __disallowedPrefixesToDirectConnectGateway
            )
        )

        # update direct_connect_gw_association_id var
        direct_connect_gw_association_id = (
            dc_gw_association['directConnectGatewayAssociation']['associationId']  # noqa: E501
        )

    helper.Data.update(
        {
            'DirectConnectGatewayAssociationId':
                direct_connect_gw_association_id
        }
    )

    return direct_connect_gw_association_id


@helper.delete
def delete_dc_resource_configuration(event, context):
    direct_connect_gw_association_id = event['PhysicalResourceId']

    # delete direct connect gateway
    dc.delete_direct_connect_gateway_association(
        associationId=direct_connect_gw_association_id
    )


@helper.poll_create
@helper.poll_update
def cu_polling(event, context):
    direct_connect_gw_association_id = (
        event['CrHelperData']['DirectConnectGatewayAssociationId']
    )

    dc_gw_assoc = dc.describe_direct_connect_gateway_associations(
        associationId=direct_connect_gw_association_id
    )['directConnectGatewayAssociations'][0]
    if dc_gw_assoc['associationState'] == 'associated':
        return direct_connect_gw_association_id

    return False


@helper.poll_delete
def d_polling(event, context):
    rp = event['ResourceProperties']
    direct_connect_gw_association_id = event['PhysicalResourceId']

    dc_gw_assoc_nr = len(dc.describe_direct_connect_gateway_associations(
            associationId=direct_connect_gw_association_id,
            directConnectGatewayId=rp['direct_connect_gw_id']
        )['directConnectGatewayAssociations']
    )
    if dc_gw_assoc_nr == 0:
        return True

    return False

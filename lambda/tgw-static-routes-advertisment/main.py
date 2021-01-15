import boto3
import logging
import os


def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    region = os.environ['AWS_REGION']

    ec2 = boto3.client('ec2', region_name=region)

    cidr_blocks = event['cidr_blocks']
    tgw_route_table_id = event['tgw_route_table_id']

    for cidr_block in cidr_blocks:
        # find all routes that belong in a specific CIDR block or its subnets
        routes = ec2.search_transit_gateway_routes(
            TransitGatewayRouteTableId=tgw_route_table_id,
            Filters=[
                {
                    'Name': 'route-search.subnet-of-match',
                    'Values': [
                        cidr_block,
                    ]
                },
                {
                    'Name': 'attachment.resource-type',
                    'Values': [
                        'vpc',
                    ]
                }
            ]
        )

        # array with the CIDR blocks that were identified
        cidr_blocks_for_routes = (
            [d['DestinationCidrBlock'] for d in routes['Routes']]
        )

        # if a static route does not already exis
        if len(cidr_blocks_for_routes) > 0:
            if cidr_block not in cidr_blocks_for_routes:
                tgw_attachements = (
                    [d['TransitGatewayAttachments'] for d in routes['Routes']]
                )
                tgw_vpc_attachements = (
                    [d for d in tgw_attachements if d[0]['ResourceType'] in ['vpc']]  # noqa: E501
                )
                # identify attachment id for VPC
                tgw_attach_id = tgw_vpc_attachements[0][0]['TransitGatewayAttachmentId']  # noqa: E501

                logger.info('Creating route for: %s' % str(cidr_block))

                ec2.create_transit_gateway_route(
                    DestinationCidrBlock=cidr_block,
                    TransitGatewayRouteTableId=tgw_route_table_id,
                    TransitGatewayAttachmentId=tgw_attach_id
                )

    ####################
    # start - cleanup
    # find all static routes to vpcs
    all_static_routes = ec2.search_transit_gateway_routes(
        TransitGatewayRouteTableId=tgw_route_table_id,
        Filters=[
            {
                'Name': 'type',
                'Values': [
                    'static',
                ]
            },
            {
                'Name': 'attachment.resource-type',
                'Values': [
                    'vpc',
                ]
            }
        ]
    )

    # array with the CIDR blocks that were identified
    all_cidr_blocks_for_static_routes = (
        [d['DestinationCidrBlock'] for d in all_static_routes['Routes']]
    )

    for cidr_block in all_cidr_blocks_for_static_routes:
        if cidr_block not in cidr_blocks:
            logger.info('Deleting route for: %s' % str(cidr_block))
            ec2.delete_transit_gateway_route(
                DestinationCidrBlock=cidr_block,
                TransitGatewayRouteTableId=tgw_route_table_id
            )
    ####################
    # end - cleanup
    ####################

import boto3
from botocore.exceptions import ClientError

client = boto3.client('apigateway', region_name='ap-south-1')
rest_api_id = 'q5ufgq5sc5'
resource_id = 't7ii32'
method = 'OPTIONS'

print('=== put_method ===')
try:
    client.put_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=method,
        authorizationType='NONE',
        requestParameters={'method.request.header.Origin': False},
    )
    print('put_method ok')
except ClientError as e:
    print('put_method error', e)

print('=== put_integration ===')
try:
    client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=method,
        type='MOCK',
        requestTemplates={'application/json': '{"statusCode": 200}'},
        passthroughBehavior='WHEN_NO_MATCH',
    )
    print('put_integration ok')
except ClientError as e:
    print('put_integration error', e)

print('=== put_method_response ===')
try:
    client.put_method_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=method,
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': False,
            'method.response.header.Access-Control-Allow-Methods': False,
            'method.response.header.Access-Control-Allow-Headers': False,
        },
    )
    print('put_method_response ok')
except ClientError as e:
    print('put_method_response error', e)

print('=== put_integration_response ===')
try:
    client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=method,
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': '"*"',
            'method.response.header.Access-Control-Allow-Methods': '"GET,POST,OPTIONS"',
            'method.response.header.Access-Control-Allow-Headers': '"Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"',
        },
    )
    print('put_integration_response ok')
except ClientError as e:
    print('put_integration_response error', e)

print('=== create_deployment ===')
try:
    response = client.create_deployment(
        restApiId=rest_api_id,
        stageName='prod',
        description='CORS fix deployment'
    )
    print('create_deployment ok', response.get('id'))
except ClientError as e:
    print('create_deployment error', e)

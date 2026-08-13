import boto3
from botocore.exceptions import ClientError

client = boto3.client('apigateway', region_name='ap-south-1')
rest_api_id = 'q5ufgq5sc5'
resource_id = 't7ii32'
method = 'OPTIONS'

print('=== put_integration_response ===')
try:
    resp = client.put_integration_response(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod=method,
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': "' * '",
            'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
        },
    )
    print('put_integration_response ok')
    print(resp)
except ClientError as e:
    print('put_integration_response error', e)

print('=== create_deployment ===')
try:
    resp = client.create_deployment(restApiId=rest_api_id, stageName='prod', description='Fix CORS mapping 3')
    print('deployment ok', resp.get('id'))
except ClientError as e:
    print('create_deployment error', e)

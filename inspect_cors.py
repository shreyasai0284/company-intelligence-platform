import boto3

client = boto3.client('apigateway', region_name='ap-south-1')
rest_api_id = 'q5ufgq5sc5'
resource_id = 't7ii32'
method = 'OPTIONS'

print('METHOD_RESPONSE')
try:
    mr = client.get_method_response(restApiId=rest_api_id, resourceId=resource_id, httpMethod=method, statusCode='200')
    print(mr)
except Exception as e:
    print('METHOD_RESPONSE_ERR', type(e).__name__, e)

print('INTEGRATION_RESPONSE')
try:
    ir = client.get_integration_response(restApiId=rest_api_id, resourceId=resource_id, httpMethod=method, statusCode='200')
    print(ir)
except Exception as e:
    print('INTEGRATION_RESPONSE_ERR', type(e).__name__, e)

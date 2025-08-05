import json
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.query_engine import QueryEngine
from models.schemas import QueryRequest, QueryResponse

# Initialize query engine
query_engine = QueryEngine()

def handler(event, context):
    try:
        # Parse request
        if event['httpMethod'] != 'POST':
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # Check authorization
        headers = event.get('headers', {})
        auth_header = headers.get('authorization', '')
        if not auth_header.startswith('Bearer 16bf0d621ee347f1a4b56589f04b1d3430e0b93e3a4faa109f64b4789400e9d8'):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Parse body
        body = json.loads(event['body'])
        request = QueryRequest(**body)
        
        # Process query
        import asyncio
        response = asyncio.run(query_engine.process_query(request))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response.dict())
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
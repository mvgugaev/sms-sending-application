from unittest.mock import patch


class MockResponseData:

    def __init__(self, method: str):
        self.method = method

    def json(self):
        mock_mthod_response_data = {
            'send': {
                'id': 204, 
                'cnt': 1,
            },
            'status': {
                'status': 1,
                'last_date': '28.12.2019 19:20:22',
                'last_timestamp': 1577550022,
            },
        }
        return mock_mthod_response_data.get(
            self.method,
            {},
        )


def mock_request_smsc(request_smsc):
    async def fake_request_smsc(method: str, *args):
        with patch('asks.get', return_value=MockResponseData(method)):
            return await request_smsc(method, *args)
    
    return fake_request_smsc
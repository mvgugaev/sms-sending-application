import random
from unittest.mock import patch


class MockResponseData:
    """
        Replace asks response, allow call .json()
        and get status_code. 
        Generate random message for each object.
    """

    def __init__(self, method: str):
        self.method = method
        self.status_code = 200
        self.sms_id = random.randint(1, 300)

    def json(self) -> dict:
        mock_mthod_response_data = {
            'send': {
                'id': self.sms_id, 
                'cnt': 1,
            },
            'status': {
                'status': 1,
                'last_date': '10.09.2021 19:20:22',
                'last_timestamp': 1577550022,
            },
        }
        return mock_mthod_response_data.get(
            self.method,
            {},
        )


def mock_request_smsc(request_smsc):
    """
        Mock request_smsc function and return
        fake with patched asks.get method.
    """
    async def fake_request_smsc(method: str, *args):
        with patch('asks.get', return_value=MockResponseData(method)):
            return await request_smsc(method, *args)
    
    return fake_request_smsc

import asks


REQUEST_DATA = {
    'url': 'https://smsc.ru/sys/',
}


class SmscApiError(Exception):
    pass


def check_payload(required_params: tuple, payload: dict):
    for required_param in required_params:
        if required_param not in payload:
            raise SmscApiError(f'Field {required_param} is required.')
        
        if not isinstance(required_param, str):
            raise SmscApiError(f'Field {required_param} must be string.')


async def request_smsc(method: str, login: str, password: str, payload: dict):
    """Send request to SMSC.ru service.
    
    Args:
        method (str): API method. E.g. 'send' or 'status'.
        login (str): Login for account on SMSC.
        password (str): Password for account on SMSC.
        payload (dict): Additional request params, override default ones.
    Returns:
        dict: Response from SMSC API.
    Raises:
        SmscApiError: If SMSC API response status is not 200 or it has `"ERROR" in response.
        
    Examples:
        >>> request_smsc("send", "my_login", "my_password", {"phones": "+79123456789"})
        {"cnt": 1, "id": 24}
        >>> request_smsc("status", "my_login", "my_password", {"phone": "+79123456789", "id": "24"})
        {'status': 1, 'last_date': '28.12.2019 19:20:22', 'last_timestamp': 1577550022}
    """
    if method not in {'send', 'status'}:
        raise SmscApiError('Incorrect method.')
    
    if not login or not password:
        raise SmscApiError('Login and password are required.')
    
    request_base_url = f'{REQUEST_DATA["url"]}{method}.php?login={login}&psw={password}'

    response = {}
    if method == 'send':
        check_payload(('phones', 'message'), payload)
        response = await asks.get(
            f'{request_base_url}&phones={payload["phones"]}&mes={payload["message"]}&fmt=3'
        )
    else:
        check_payload(('phone', 'id'), payload)
        response = await asks.get(
            f'{request_base_url}&phone={payload["phone"]}&id={payload["id"]}&fmt=3'
        )

    if response.status_code != 200:
        raise SmscApiError('Incorrect response status.')

    return response.json()

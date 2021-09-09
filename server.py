import trio
import json
from quart import render_template, request, websocket
from quart_trio import QuartTrio
from functools import partial, wraps
from request import request_smsc, SmscApiError
from mock import mock_request_smsc


app = QuartTrio(__name__)


AUTH_DATA = {
    'login': 'devman',
    'password': 'Duok4oshvav',
}


@app.route('/')
async def index():
    return await render_template('index.html')


async def parse_form_data(request):
    """
        Кастомная функция парсинга форм, 
        существует пока разработчики не включат 
        исправление бага в новый релиз.
        issue: https://gitlab.com/pgjones/quart-trio/-/issues/23
    """
    parser = request.make_form_data_parser()
    data, _ = await parser.parse(
        request.body,
        request.mimetype,
        request.content_length,
        request.mimetype_params,
    )
    return data


@app.route('/send/', methods=['POST'])
async def create():
    form = await parse_form_data(request)
    global request_smsc
    request_smsc = mock_request_smsc(request_smsc)

    try:
        send_response = await request_smsc(
            'send',
            AUTH_DATA['login'],
            AUTH_DATA['password'],
            {
                'phones': '79653535285',
                'message': form['text'],
            },
        )

        status_response = await request_smsc(
            'status',
            AUTH_DATA['login'],
            AUTH_DATA['password'],
            {
                'phone': '79653535285',
                'id': send_response['id'],
            },
        )

        if status_response.get('status', 0) != 1:
            return {
                'errorMessage': 'Сообщение не доставлено',
            }
    except SmscApiError:
        return {
            'errorMessage': 'Потеряно соединение с SMSC.ru',
        }

    return {
        'status': 'ok',
    }


@app.websocket('/ws')
async def ws():
    while True:
        for i in range(101):
            data = {
                "msgType": "SMSMailingStatus",
                "SMSMailings": [
                    {
                    "timestamp": 1123131392.734,
                    "SMSText": "Сегодня гроза! Будьте осторожны!",
                    "mailingId": "1",
                    "totalSMSAmount": 100,
                    "deliveredSMSAmount": i,
                    "failedSMSAmount": 0,
                    },
                ],
            }
            await websocket.send(json.dumps(data))
            await trio.sleep(1)


app.run(port=5000)

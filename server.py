import trio
import json
import aioredis
import trio_asyncio
from database import Database
from quart import render_template, request, websocket
from quart_trio import QuartTrio
from request import request_smsc, SmscApiError
from hypercorn.trio import serve
from hypercorn.config import Config as HyperConfig
from mock import mock_request_smsc


app = QuartTrio(__name__)


REQUEST_DATA = {
    'phone': '79653535285',
    'login': 'devman',
    'password': 'Duok4oshvav',
}

REDIS_URL = 'redis://localhost'


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
    phone, text = REQUEST_DATA['phone'], form['text']

    try:
        send_response = await request_smsc(
            'send',
            REQUEST_DATA['login'],
            REQUEST_DATA['password'],
            {
                'phones': phone,
                'message': text,
            },
        )

        status_response = await request_smsc(
            'status',
            REQUEST_DATA['login'],
            REQUEST_DATA['password'],
            {
                'phone': phone,
                'id': send_response['id'],
            },
        )

        if status_response.get('status', 0) != 1:
            return {
                'errorMessage': 'Сообщение не доставлено',
            }
        
        redis = await trio_asyncio.aio_as_trio(aioredis.create_redis_pool)(
            REDIS_URL,
            encoding='utf-8',
        )

        try:
            db = Database(redis)

            await trio_asyncio.aio_as_trio(db.add_sms_mailing)(
                send_response['id'],
                phone,
                text,
            )
            sms_ids = await trio_asyncio.aio_as_trio(db.list_sms_mailings)()
            print('Registered mailings ids', sms_ids)
        finally:
            redis.close()
            await trio_asyncio.aio_as_trio(redis.wait_closed)

    except SmscApiError:
        return {
            'errorMessage': 'Потеряно соединение с SMSC.ru',
        }

    return {
        'status': 'ok',
    }


@app.websocket('/ws')
async def ws():
    redis = await trio_asyncio.aio_as_trio(aioredis.create_redis_pool)(
        REDIS_URL,
        encoding='utf-8',
    )

    try:
        redis_db = Database(redis)

        while True:
            sms_ids = await trio_asyncio.aio_as_trio(redis_db.list_sms_mailings)()
            sms_mailings = await trio_asyncio.aio_as_trio(redis_db.get_sms_mailings)(*sms_ids)
            while True:
                response_data = {
                    "msgType": "SMSMailingStatus",
                    "SMSMailings": [
                        {
                            "timestamp": mailing['created_at'],
                            "SMSText": mailing['text'],
                            "mailingId": str(mailing['sms_id']),
                            "totalSMSAmount": mailing['phones_count'],
                            "deliveredSMSAmount": 0,
                            "failedSMSAmount": 0,
                        } for mailing in sms_mailings
                    ],
                }
                await websocket.send(json.dumps(response_data))
                await trio.sleep(2)
    finally:
        redis.close()
        await trio_asyncio.aio_as_trio(redis.wait_closed)


async def run_server():
    async with trio_asyncio.open_loop() as _:
        config = HyperConfig()
        config.bind = [f"127.0.0.1:5000"]
        config.use_reloader = True
        await serve(app, config)


def main():
    trio.run(run_server)


if __name__ == '__main__':
    main()

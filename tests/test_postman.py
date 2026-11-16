"""Valida a sequência HTTP da coleção, sem executar seu JavaScript."""
from datetime import datetime
import json
from pathlib import Path
import re
from uuid import uuid4
from zoneinfo import ZoneInfo


def test_postman_http_sequence(setup):
    client, _, _, _ = setup
    path = Path(__file__).parents[1] / 'docs/Segredo_Gelado.postman_collection.json'
    collection = json.loads(path.read_text(encoding='utf-8'))
    values = {'username': 'admin', 'password': 'TesteSeguro123!', 'baseUrl': '',
              'externalId': str(uuid4()), 'driverUsername': 'demo_' + uuid4().hex[:12],
              'driverPassword': uuid4().hex,
              'today': datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()}
    def replace(text):
        return re.sub(r'\{\{(\w+)\}\}', lambda match: str(values[match.group(1)]), text)
    for index, item in enumerate(collection['item'], start=1):
        request = item['request']
        auth = request.get('auth', collection['auth'])
        headers = {}
        if auth['type'] == 'bearer':
            headers['Authorization'] = 'Bearer ' + replace(auth['bearer'][0]['value'])
        kwargs = {'headers': headers}
        body = request.get('body')
        if body:
            if body['mode'] == 'raw': kwargs['json'] = json.loads(replace(body['raw']))
            else: kwargs['data'] = {x['key']: replace(x['value']) for x in body['urlencoded']}
        response = client.request(request['method'], replace(request['url']), **kwargs)
        script = '\n'.join(next(x['script']['exec'] for x in item['event'] if x['listen'] == 'test'))
        expected = int(re.search(r'to\.have\.status\((\d+)\)', script)[1])
        assert response.status_code == expected, (item['name'], response.status_code, response.text)
        result = response.json()
        if index == 1: values['token'] = result['access_token']
        elif index == 2: values['offerId'] = next(x['id'] for x in result if x['balls'] == 3)
        elif index == 3:
            for name, key in [('Chocolate', 'chocolateId'), ('Morango', 'morangoId'), ('Caixinha', 'packageId')]:
                values[key] = next(x['id'] for x in result if x['name'] == name)
        elif index == 7: values['orderId'] = result['id']
        elif index == 19: values['driverId'] = result['id']
        elif index == 20: values['driverToken'] = result['access_token']
        elif index == 23: values['deliveryId'] = result['id']
        elif index == 26: values['donationItemId'] = next(x['id'] for x in result if x['order_id'] == values['orderId'])

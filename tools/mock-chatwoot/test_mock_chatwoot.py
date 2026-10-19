#!/usr/bin/env python3
"""
Test unitario del mock de Chatwoot y simulación del flujo de agrupación de conversaciones.
"""
import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from mock_chatwoot import ChatwootMockHandler, reset_state, STATE

PORT = 13005
BASE_URL = f"http://127.0.0.1:{PORT}"


def request(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Content-Type': 'application/json', 'api-access-token': 'test'}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))


def main():
    server = ThreadingHTTPServer(('127.0.0.1', PORT), ChatwootMockHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    print("=== 1. Health check ===")
    status, data = request('GET', '/health')
    assert status == 200 and data['status'] == 'ok'
    print("OK health:", data)

    print("\n=== 2. Inboxes ===")
    status, data = request('GET', '/api/v1/accounts/1/inboxes')
    assert status == 200 and len(data['payload']) == 1
    assert data['payload'][0]['id'] == 4
    print("OK inboxes:", data['payload'][0]['name'])

    print("\n=== 3. Crear contacto ===")
    status, data = request('POST', '/api/v1/accounts/1/contacts', {
        'name': 'Cliente Test',
        'identifier': '595981111111@s.whatsapp.net',
        'phone_number': '+595981111111'
    })
    assert status == 200
    cid = data['payload']['contact']['id']
    assert cid == 1
    print(f"OK contact id={cid}")

    print("\n=== 4. Buscar contacto ===")
    status, data = request('GET', '/api/v1/accounts/1/contacts/search?q=595981111111')
    assert status == 200 and len(data['payload']) == 1
    print("OK search found contact:", data['payload'][0]['name'])

    print("\n=== 5. Conversaciones del contacto (inicialmente 0) ===")
    status, data = request('GET', f"/api/v1/accounts/1/contacts/{cid}/conversations")
    assert status == 200 and len(data['payload']) == 0
    print("OK convs count = 0")

    print("\n=== 6. Crear conversación para el contacto ===")
    status, data = request('POST', '/api/v1/accounts/1/conversations', {
        'source_id': '595981111111@s.whatsapp.net',
        'inbox_id': 4,
        'contact_id': cid,
        'status': 'open',
    })
    assert status == 200
    conv_id = data['id']
    print(f"OK created conv id={conv_id}")

    print("\n=== 7. Simular 5 mensajes: verificar que reutilizan la misma conversación ===")
    for i in range(1, 6):
        status, convs_data = request('GET', f"/api/v1/accounts/1/contacts/{cid}/conversations")
        convList = convs_data.get('payload', [])
        open_conv = next((c for c in convList if c.get('inbox_id') == 4 and c.get('status') != 'resolved'), None)
        assert open_conv is not None, "Debe encontrar la conversación abierta"
        target_conv_id = open_conv['id']
        assert target_conv_id == conv_id, "No debe crear conversaciones duplicadas"

        status, msg_data = request('POST', f"/api/v1/accounts/1/conversations/{target_conv_id}/messages", {
            'content': f"Mensaje {i}",
            'message_type': 'incoming',
            'content_attributes': {'source': 'dashwhat2'}
        })
        assert status == 200 and msg_data['id'] == i

    status, dump = request('GET', '/_mock/dump')
    assert len(dump['conversations']) == 1, f"Esperada 1 conversación, se encontraron {len(dump['conversations'])}"
    assert len(dump['messages']) == 5, f"Esperados 5 mensajes, se encontraron {len(dump['messages'])}"
    print(f"OK: 5 mensajes recibidos y agrupados en EXACTAMENTE 1 conversación (ID {conv_id})!")

    server.shutdown()
    print("\nTODOS LOS TESTS PASARON EXITOSAMENTE.")


if __name__ == '__main__':
    main()

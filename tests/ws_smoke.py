import asyncio
import json
import os

import websockets

HOST = os.environ.get("PP_HOST", "127.0.0.1:8000")
BASE = f"http://{HOST}/api/v1"
WS = f"ws://{HOST}/api/v1/ws/results"


async def main() -> None:
    import httpx

    async with httpx.AsyncClient(base_url=BASE) as client:
        personero = (await client.post("/auth/login/dni", json={"dni": "12345678"})).json()
        token = personero["access_token"]
        tid = personero["scopes"][0]["table_id"]
        headers = {"Authorization": f"Bearer {token}"}

        ctx = (await client.get(f"/tables/{tid}", headers=headers)).json()
        parties = [p["id"] for p in ctx["parties"]][:3]
        record = ctx.get("record")
        if record is None:
            print("No hay registro para editar; ejecute primero un POST de votos.")
            return
        rec_id = record["id"]

        async with websockets.connect(WS) as ws:
            entries = []
            for cat in ("GOBERNADOR", "CONSEJERO", "PROVINCIA", "DISTRITO"):
                entries += [
                    {"category": cat, "vote_type": "VALIDO", "party_id": parties[0], "quantity": 31},
                    {"category": cat, "vote_type": "VALIDO", "party_id": parties[1], "quantity": 18},
                    {"category": cat, "vote_type": "VALIDO", "party_id": parties[2], "quantity": 100},
                    {"category": cat, "vote_type": "NULO", "quantity": 10},
                    {"category": cat, "vote_type": "BLANCO", "quantity": 11},
                ]
            body = {"total_asistentes": 170, "comment": "ws test", "entries": entries}
            rec = (await client.put(f"/votes/{rec_id}", json=body, headers=headers)).json()
            print("update status:", rec["record"]["status"] if rec.get("record") else rec)
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                print("WS event:", data["event"], "table:", data["table_id"])
            except asyncio.TimeoutError:
                print("WS: no se recibio mensaje")


asyncio.run(main())

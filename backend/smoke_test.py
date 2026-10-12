"""Smoke test de la API (requiere backend en :8005). Uso: python smoke_test.py"""
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

B = "http://127.0.0.1:8005"


def show(name, r):
    try:
        body = r.json()
    except Exception:
        body = r.text[:120]
    print(f"{r.status_code}  {name:28} {str(body)[:110]}")


r = requests.post(f"{B}/auth/login", data={"username": "admin", "password": "Admin123!"})
show("login", r)
H = {"Authorization": "Bearer " + r.json()["access_token"]}

print("\n-- sin token (esperado 401)")
for p in ("/admin/contracts", "/dba/instances?contract_id=1", "/dba/status"):
    show(p, requests.get(B + p))

print("\n-- contratos / instancias")
contracts = requests.get(f"{B}/admin/contracts", headers=H)
show("/admin/contracts", contracts)
inst_id = None
for c in contracts.json():
    ins = requests.get(f"{B}/dba/instances", params={"contract_id": c["id"]}, headers=H)
    show(f"/dba/instances c={c['id']}", ins)
    if ins.json() and inst_id is None:
        inst_id = ins.json()[0]["id"]

print("\n-- acciones SIN instancia (esperado type=error 'No hay instancia')")
for p in ("status", "cpu", "discos", "datalog", "tempdb", "whoisactive", "bloqueos", "jobs", "alwayson", "performance"):
    show(p, requests.get(f"{B}/dba/{p}", headers=H))

if inst_id:
    print(f"\n-- acciones CON instancia {inst_id}")
    show("select", requests.post(f"{B}/dba/instances/select", params={"instance_id": inst_id}, headers=H))
    for p in ("status", "cpu", "discos", "datalog", "tempdb", "whoisactive", "bloqueos", "jobs", "alwayson", "performance"):
        show(p, requests.get(f"{B}/dba/{p}", headers=H))

print("\n-- misc")
show("history/cpu", requests.get(f"{B}/dba/history/cpu", params={"contract_id": 1}, headers=H))
show("cancelar spid=abc", requests.post(f"{B}/dba/cancelar", json={"spid": "1; DROP TABLE x"}, headers=H))
show("profile/me", requests.get(f"{B}/auth/profile/me", headers=H))
show("chat soporte", requests.post(f"{B}/chat/message", json={"message": "soporte prueba de humo"}, headers=H))
show("chat matar sin instancia", requests.post(f"{B}/chat/message", json={"message": "matar 55"}, headers=H))
show("users/all", requests.get(f"{B}/admin/users/all", headers=H))

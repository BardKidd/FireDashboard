def test_end_to_end(client):
    r = client.post("/api/holdings", json={"symbol": "0050", "shares": 1000, "date": "2025-06-02"})
    assert r.status_code == 201, r.text
    assert r.json()["symbol"] == "0050.TW"
    h = client.get("/api/holdings").json()
    row = next(x for x in h["rows"] if x["symbol"] == "0050.TW")
    assert row["shares"] == 1000 and row["market"] == "TW"

    r = client.post("/api/logs", json={"symbol": "0050.TW", "date": "2025-07-01", "kind": "buy", "delta": 500})
    assert r.status_code == 201
    r = client.post("/api/logs", json={"symbol": "0050.TW", "date": "2025-05-01", "kind": "sell", "delta": 10})
    assert r.status_code == 400  # would go negative
    assert client.post("/api/logs", json={"symbol": "CASH-TWD", "date": "2025-07-01", "kind": "deposit", "delta": 50000}).status_code == 201

    cfg = client.get("/api/config").json()
    cfg["birth_month"] = 6
    assert client.put("/api/config", json=cfg).status_code == 200
    cfg["fx_mode"], cfg["custom_fx_rate"] = "custom", None
    assert client.put("/api/config", json=cfg).status_code == 400

    s = client.get("/api/summary").json()
    assert s["time_to_coast"]["status"] in {"achieved", "reachable", "unreachable"}
    assert "0050.TW" in s["missing_prices"]
    assert client.get("/api/projection").json()["series"]
    assert client.delete("/api/holdings/0050.TW").json() == {"archived": True}


def test_game_endpoints(client):
    g = client.get("/api/game").json()
    assert g["checkin"]["today"] is False and g["level"]["level"] == 1
    r = client.post("/api/game/checkin", json={"note": "hi"})
    assert r.status_code == 200, r.text
    assert client.post("/api/game/checkin", json={}).status_code == 400
    rid = client.post("/api/game/rewards", json={"name": "電影", "cost": 25}).json()["id"]
    assert client.post(f"/api/game/rewards/{rid}/redeem").status_code == 201
    assert client.post(f"/api/game/rewards/{rid}/redeem").status_code == 400  # 30 - 25 = 5 left
    g = client.get("/api/game").json()
    assert g["stars"]["balance"] == 5 and g["checkin"]["today"] is True
    assert client.delete(f"/api/game/redemptions/{g['redemptions'][0]['id']}").status_code == 200
    assert client.put("/api/game/settings", json={"theme": "gold"}).status_code == 400
    assert client.get("/api/collect").json()["holdings"] == []


def test_status_ignores_sold_archived_holdings(client, db):
    from app.models import FetchStatus

    client.post("/api/holdings", json={"symbol": "QLD", "shares": 10, "date": "2025-06-02"})
    client.post("/api/holdings", json={"symbol": "SSO", "shares": 5, "date": "2025-06-02"})
    assert client.post("/api/logs", json={"symbol": "QLD", "date": "2025-07-01", "kind": "sell", "delta": -10}).status_code == 201
    assert client.delete("/api/holdings/QLD").json() == {"archived": True}
    db.add_all([
        FetchStatus(symbol="QLD", last_success_date="2025-07-01"),  # frozen since the sale
        FetchStatus(symbol="SSO", last_success_date="2025-07-10"),
        FetchStatus(symbol="USDTWD=X", last_success_date="2025-07-10"),
    ])
    db.commit()
    st = client.get("/api/status").json()
    assert st["last_success_date"] == "2025-07-10"
    assert "QLD" not in [r["symbol"] for r in st["symbols"]]

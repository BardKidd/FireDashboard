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

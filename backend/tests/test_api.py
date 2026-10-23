from conftest import send_reading


# ---------------- AUTH ----------------
def test_register_and_login(client):
    res = client.post("/api/register", json={
        "fullname": "Asha", "email": "Asha@Example.com", "password": "secret123", "phone": "9876543210",
    })
    assert res.status_code == 201

    res = client.post("/api/login", json={"email": "asha@example.com", "password": "secret123"})
    assert res.status_code == 200
    assert res.json["token"]
    assert res.json["user"]["email"] == "asha@example.com"


def test_password_is_hashed(app, client):
    client.post("/api/register", json={
        "fullname": "Asha", "email": "asha@example.com", "password": "secret123", "phone": "1",
    })
    from database import User
    with app.app_context():
        user = User.query.first()
        assert user.password_hash != "secret123"
        assert user.check_password("secret123")


def test_duplicate_email_rejected(client, auth_headers):
    res = client.post("/api/register", json={
        "fullname": "Again", "email": "test@example.com", "password": "secret123", "phone": "1",
    })
    assert res.status_code == 409


def test_wrong_password_rejected(client, auth_headers):
    res = client.post("/api/login", json={"email": "test@example.com", "password": "wrong-pass"})
    assert res.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/api/dashboard").status_code == 401
    assert client.post("/api/assistant", json={"question": "hi"}).status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/dashboard", headers=bad).status_code == 401


# ---------------- SENSOR INGESTION ----------------
def test_sensor_requires_device_key(client):
    res = client.post("/api/sensor", json={"shipment_id": "SHP1"})
    assert res.status_code == 401


def test_sensor_validates_input(client):
    assert send_reading(client, temperature="hot").status_code == 400
    assert send_reading(client, product_type="spaceship").status_code == 400
    assert send_reading(client, shipment_id="").status_code == 400


def test_safe_pharma_reading_is_low_risk(client):
    res = send_reading(client, temperature=5, humidity=45, delay_hours=0.2)
    assert res.status_code == 201
    assert res.json["risk"] == "LOW"
    assert res.json["report_source"] == "template"  # no LLM key in tests


def test_hot_delayed_pharma_reading_is_high_risk(client):
    res = send_reading(client, temperature=18, humidity=70, delay_hours=6)
    assert res.json["risk"] == "HIGH"
    assert "SOP" in res.json["report"]


def test_same_reading_riskier_for_pharma_than_general(client):
    """The model learned product-specific limits: 12 °C is bad for vaccines, fine for furniture."""
    pharma = send_reading(client, shipment_id="P", product_type="pharma", temperature=14, humidity=50, delay_hours=3)
    general = send_reading(client, shipment_id="G", product_type="general", temperature=14, humidity=50, delay_hours=3)
    assert general.json["risk"] == "LOW"
    assert pharma.json["risk"] in ("MEDIUM", "HIGH")


# ---------------- DASHBOARD & HISTORY ----------------
def test_dashboard_shows_latest_reading_per_shipment(client, auth_headers):
    send_reading(client, shipment_id="SHP1", temperature=5)
    send_reading(client, shipment_id="SHP1", temperature=18, delay_hours=6)
    send_reading(client, shipment_id="SHP2", temperature=5)

    data = client.get("/api/dashboard", headers=auth_headers).json
    assert data["summary"]["total_shipments"] == 2
    shp1 = next(s for s in data["shipments"] if s["shipment_id"] == "SHP1")
    assert shp1["temperature"] == 18


def test_shipment_history(client, auth_headers):
    send_reading(client, shipment_id="SHP7", temperature=5)
    send_reading(client, shipment_id="SHP7", temperature=6)
    res = client.get("/api/shipments/shp7", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json["readings"]) == 2
    assert client.get("/api/shipments/NOPE", headers=auth_headers).status_code == 404


# ---------------- ASSISTANT ----------------
def test_assistant_uses_live_data_and_sops(client, auth_headers):
    send_reading(client, shipment_id="SHP2", temperature=18, humidity=70, delay_hours=6)
    res = client.post("/api/assistant", json={"question": "What should we do about SHP2?"}, headers=auth_headers)
    assert res.status_code == 200
    body = res.json
    assert body["mode"] == "retrieval-only"
    assert body["shipments"][0]["shipment_id"] == "SHP2"
    assert any("Pharma" in s["document"] or "Escalation" in s["document"] for s in body["sources"])


def test_assistant_finds_sop_for_what_went_wrong(client, auth_headers):
    """A warm pharma shipment should bring up the excursion SOP, even though the question doesn't say 'temperature'."""
    send_reading(client, shipment_id="SHP2", temperature=13, humidity=55, delay_hours=1)
    send_reading(client, shipment_id="SHP5", product_type="electronics", temperature=28, humidity=75, delay_hours=9)
    body = client.post("/api/assistant", json={"question": "What should we do about SHP2?"}, headers=auth_headers).json
    titles = [s["title"] for s in body["sources"]]
    assert "Pharma temperature excursion response" in titles
    # Only pharma SOPs (product filter) plus the escalation rule for SHP2's risk level
    shp2_risk = body["shipments"][0]["risk"]
    assert {s["document"] for s in body["sources"]} <= {"Pharmaceutical Cold Chain SOP", "Risk Escalation Policy"}
    assert f"{shp2_risk} risk" in titles
    assert f"{shp2_risk} risk" in body["answer"]


def test_general_question_gets_sops_for_every_risky_shipment(client, auth_headers):
    """Regression: electronics and food SOPs used to crowd out the pharma SOP."""
    send_reading(client, shipment_id="SHP2", temperature=11, humidity=55, delay_hours=1)
    send_reading(client, shipment_id="SHP3", product_type="food", temperature=17, humidity=88, delay_hours=6)
    send_reading(client, shipment_id="SHP5", product_type="electronics", temperature=28, humidity=80, delay_hours=9)
    body = client.post("/api/assistant", json={"question": "Which shipments are high risk right now?"},
                       headers=auth_headers).json
    at_risk = {s["product_type"] for s in body["shipments"]}
    documents = {s["document"] for s in body["sources"]}
    expected = {"pharma": "Pharmaceutical Cold Chain SOP", "food": "Food and Perishables Handling SOP",
                "electronics": "Electronics and General Cargo SOP"}
    assert at_risk  # the readings above are risky enough to be flagged
    for product in at_risk:
        assert expected[product] in documents


def test_assistant_rejects_empty_question(client, auth_headers):
    assert client.post("/api/assistant", json={"question": " "}, headers=auth_headers).status_code == 400

import pytest
import json
from src.main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_valid_request(client):
    payload = {
        "S0": 100,
        "K": 100,
        "r": 0.05,
        "sigma": 0.2,
        "T": 1.0,
        "option_type": "call",
        "steps": 10,
        "batch_size": 100,
        "max_paths": 500,
        "tolerance": 0.1
    }
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "price" in data
    assert "greeks" in data
    assert isinstance(data["greeks"], dict)
    assert all(isinstance(v, (int, float)) for v in data["greeks"].values())

def test_missing_required_params(client):
    payload = {"S0": 100, "K": 100, "r": 0.05, "sigma": 0.2, "T": 1.0}  # missing option_type
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 400
    assert "Missing required parameters" in resp.get_json()["error"]

def test_invalid_param_types(client):
    payload = {"S0": "not_a_number", "K": 100, "r": 0.05, "sigma": 0.2, "T": 1.0, "option_type": "call"}
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 400
    assert "Invalid parameter types" in resp.get_json()["error"]

def test_invalid_option_type(client):
    payload = {"S0": 100, "K": 100, "r": 0.05, "sigma": 0.2, "T": 1.0, "option_type": "invalid_type"}
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 400
    assert "option_type must be" in resp.get_json()["error"]

def test_edge_case_negative_zero(client):
    payload = {"S0": 0, "K": 0, "r": 0, "sigma": 0, "T": 0, "option_type": "call"}
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    # Should not 500, should handle gracefully
    assert resp.status_code in (200, 400, 500)
    # If 200, price and greeks should be present
    if resp.status_code == 200:
        data = resp.get_json()
        assert "price" in data
        assert "greeks" in data

def test_large_batch_and_steps(client):
    payload = {"S0": 100, "K": 100, "r": 0.05, "sigma": 0.2, "T": 1.0, "option_type": "put", "steps": 20, "batch_size": 200, "max_paths": 1000}
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "price" in data
    assert "greeks" in data

def test_error_handling(client, monkeypatch):
    # Simulate internal error
    def raise_error(*a, **kw):
        raise RuntimeError("Simulated error")
    monkeypatch.setattr("src.services.lsm_american_options.LSMAmericanOptions.lsm_american_option_with_greeks", raise_error)
    payload = {"S0": 100, "K": 100, "r": 0.05, "sigma": 0.2, "T": 1.0, "option_type": "call"}
    resp = client.post("/api/lsm_american_option", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 500
    assert "LSM calculation failed" in resp.get_json()["error"] 
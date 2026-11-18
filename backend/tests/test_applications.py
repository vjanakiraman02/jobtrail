API = "/api/v1/applications"


def make(client, **overrides):
    payload = {"company": "Example Bank", "title": "Software Engineer", **overrides}
    return client.post(API, json=payload)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_defaults_to_saved(client):
    response = make(client, location="New York, NY", url="https://example.com/jobs/1")
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["status"] == "saved"
    assert body["company"] == "Example Bank"
    assert body["created_at"]


def test_list_is_newest_first_and_paginates(client):
    for n in range(3):
        make(client, company=f"Company {n}")
    companies = [a["company"] for a in client.get(API).json()]
    assert companies == ["Company 2", "Company 1", "Company 0"]
    page = client.get(API, params={"limit": 1, "offset": 1}).json()
    assert [a["company"] for a in page] == ["Company 1"]


def test_filter_by_status(client):
    make(client, company="A", status="applied")
    make(client, company="B", status="saved")
    applied = client.get(API, params={"status": "applied"}).json()
    assert [a["company"] for a in applied] == ["A"]


def test_get_one_and_404(client):
    created = make(client).json()
    assert client.get(f"{API}/{created['id']}").json()["title"] == "Software Engineer"
    assert client.get(f"{API}/9999").status_code == 404


def test_patch_updates_only_sent_fields(client):
    created = make(client, notes="keep me").json()
    response = client.patch(
        f"{API}/{created['id']}", json={"status": "interview", "applied_on": "2026-10-01"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interview"
    assert body["applied_on"] == "2026-10-01"
    assert body["notes"] == "keep me"
    assert body["company"] == "Example Bank"


def test_patch_rejects_null_for_required_fields(client):
    created = make(client).json()
    assert client.patch(f"{API}/{created['id']}", json={"company": None}).status_code == 422


def test_delete(client):
    created = make(client).json()
    assert client.delete(f"{API}/{created['id']}").status_code == 204
    assert client.get(f"{API}/{created['id']}").status_code == 404
    assert client.delete(f"{API}/{created['id']}").status_code == 404


def test_validation_errors(client):
    assert make(client, company="").status_code == 422
    assert make(client, status="ghosted").status_code == 422
    assert make(client, url="javascript:alert(1)").status_code == 422

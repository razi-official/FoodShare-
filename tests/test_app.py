from io import BytesIO

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "foodshare.sqlite"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/",
        data={"email": "user@example.com", "password": "mypassword"},
        follow_redirects=True,
    )


def test_protected_routes_redirect_to_signin(client):
    response = client.get("/home")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_default_user_can_sign_in(client):
    response = login(client)

    assert response.status_code == 200
    assert b"Start" in response.data


def test_donation_is_persisted_and_listed(client):
    login(client)

    response = client.post(
        "/donate",
        data={
            "donor-name": "Aminah",
            "location": "Campus Cafe",
            "contact": "0123456789",
            "food-type": "Rice",
            "quantity": "5",
            "donation-date": "2026-06-04",
            "expiry-date": "2026-06-05",
        },
        follow_redirects=True,
    )
    listing = client.get("/listings")

    assert response.status_code == 200
    assert b"Donation submitted." in response.data
    assert b"Aminah" in listing.data
    assert b"Rice" in listing.data


def test_bad_quantity_is_rejected(client):
    login(client)

    response = client.post(
        "/request",
        data={
            "requester-name": "Student",
            "contact": "0123456789",
            "type-request": "Meals",
            "quantity": "0",
        },
    )

    assert response.status_code == 400
    assert b"Quantity must be a positive number." in response.data


def test_invalid_upload_extension_is_rejected(client):
    login(client)

    response = client.post(
        "/donate",
        data={
            "donor-name": "Aminah",
            "location": "Campus Cafe",
            "contact": "0123456789",
            "food-type": "Rice",
            "quantity": "5",
            "donation-date": "2026-06-04",
            "image-upload": (BytesIO(b"not an image"), "bad.exe"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert b"Only gif, jpg, jpeg, png, and webp images are allowed." in response.data

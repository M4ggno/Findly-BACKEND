"""Testes do upload e processamento de fotos."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.urls import reverse
from PIL import Image

from apps.items.models import ItemPhoto, ItemStatus
from services import photo_service

pytestmark = pytest.mark.django_db


def upload_url(item) -> str:
    return reverse("items:found-item-upload-photo", args=[item.public_code])


def delete_url(item, photo: ItemPhoto) -> str:
    return reverse("items:found-item-delete-photo", args=[item.public_code, photo.pk])


def test_upload_requires_authentication(api_client, found_item, photo_upload):
    response = api_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )
    assert response.status_code == 401


def test_owner_uploads_photo(auth_client, common_user, found_item, photo_upload):
    response = auth_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["uploaded_by"] == common_user.id
    assert data["image"].endswith(".jpg")

    photo = ItemPhoto.objects.get(pk=data["id"])
    assert photo.item == found_item
    assert f"items/{found_item.public_code}/" in photo.image.name
    assert Path(photo.image.path).exists()


def test_upload_strips_exif(auth_client, found_item, photo_upload):
    response = auth_client.post(
        upload_url(found_item),
        {"image": photo_upload(with_exif=True)},
        format="multipart",
    )

    assert response.status_code == 201
    photo = ItemPhoto.objects.get(pk=response.json()["id"])
    with Image.open(photo.image.path) as image:
        assert len(image.getexif()) == 0


def test_upload_resizes_large_image(auth_client, found_item, photo_upload):
    response = auth_client.post(
        upload_url(found_item),
        {"image": photo_upload(size=(2400, 1200))},
        format="multipart",
    )

    assert response.status_code == 201
    photo = ItemPhoto.objects.get(pk=response.json()["id"])
    with Image.open(photo.image.path) as image:
        assert max(image.size) <= photo_service.MAX_DIMENSION


def test_upload_rejects_unsupported_extension(auth_client, found_item, photo_upload):
    response = auth_client.post(
        upload_url(found_item),
        {"image": photo_upload(name="foto.gif", content_type="image/gif")},
        format="multipart",
    )

    assert response.status_code == 400
    assert "image" in response.json()


def test_upload_rejects_oversized_file(
    auth_client, found_item, photo_upload, monkeypatch
):
    monkeypatch.setattr(photo_service, "MAX_UPLOAD_BYTES", 10)

    response = auth_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )

    assert response.status_code == 400
    assert "image" in response.json()


def test_other_user_cannot_upload(other_client, found_item, photo_upload):
    response = other_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )

    assert response.status_code == 403


def test_owner_cannot_upload_after_terminal_status(
    auth_client, found_item, photo_upload
):
    found_item.status = ItemStatus.DEVOLVIDO
    found_item.save(update_fields=["status"])

    response = auth_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )

    assert response.status_code == 403


def test_operator_can_upload_to_any_item(operator_client, found_item, photo_upload):
    response = operator_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )

    assert response.status_code == 201


def test_owner_deletes_photo(auth_client, found_item, photo_upload):
    created = auth_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )
    photo = ItemPhoto.objects.get(pk=created.json()["id"])
    file_path = Path(photo.image.path)

    response = auth_client.delete(delete_url(found_item, photo))

    assert response.status_code == 204
    assert not ItemPhoto.objects.filter(pk=photo.pk).exists()
    assert not file_path.exists()


def test_other_user_cannot_delete_photo(
    other_client, auth_client, found_item, photo_upload
):
    created = auth_client.post(
        upload_url(found_item), {"image": photo_upload()}, format="multipart"
    )
    photo = ItemPhoto.objects.get(pk=created.json()["id"])

    response = other_client.delete(delete_url(found_item, photo))

    assert response.status_code == 403
    assert ItemPhoto.objects.filter(pk=photo.pk).exists()

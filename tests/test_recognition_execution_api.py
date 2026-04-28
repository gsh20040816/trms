from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from trms_backend.infrastructure.storage import LocalMaterialFileStorage
from trms_backend.main import create_app

from test_tasks_api import valid_task_payload


def make_client(tmp_path):
    return TestClient(
        create_app(
            f"sqlite:///{tmp_path}/test.db",
            material_file_storage=LocalMaterialFileStorage(tmp_path / "material-storage"),
        )
    )


def create_task(client: TestClient) -> str:
    task = client.post("/api/tasks", json=valid_task_payload()).json()
    client.patch(f"/api/tasks/{task['id']}/status", json={"target_status": "open"})
    return task["id"]


def upload_material(
    client: TestClient,
    task_id: str,
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    response = client.post(
        f"/api/tasks/{task_id}/materials",
        data={
            "submitter_id": "2250001",
            "channel": "web",
            "material_type": "invoice",
        },
        files={"files": (filename, content, content_type)},
    )
    assert response.status_code == 201
    return response.json()["items"][0]["id"]


def latest_recognition_task_id(client: TestClient, material_id: str) -> str:
    response = client.get(f"/api/materials/{material_id}/recognition-tasks")
    assert response.status_code == 200
    return response.json()["items"][-1]["id"]


def build_text_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=144)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT\n/F1 12 Tf\n72 100 Td\n(Invoice INV-001 Tongji University) Tj\n0 -16 Td\n"
        b"(Amount 123.45) Tj\nET\n"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_blank_pdf_bytes(*, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if encrypted:
        writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_image_only_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    image_stream = DecodedStreamObject()
    image_stream.set_data(bytes([255, 255, 255]))
    image_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    image_ref = writer._add_object(image_stream)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): image_ref}),
        }
    )
    content_stream = DecodedStreamObject()
    content_stream.set_data(b"q\n100 0 0 100 0 0 cm\n/Im0 Do\nQ\n")
    page[NameObject("/Contents")] = writer._add_object(content_stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_execute_recognition_task_extracts_pdf_text_into_preparation_payload(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "text-invoice.pdf"
    sample_path.write_bytes(build_text_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "failed"
    assert item["failure"] == {
        "stage": "ai",
        "reason": "llm_provider_not_configured",
    }
    preparation = item["raw_response"]["preparation"]
    assert preparation["material_id"] == material_id
    assert preparation["original_filename"] == sample_path.name
    assert preparation["content_type"] == "application/pdf"
    assert preparation["recognition_input"] == {
        "source": "pdf_text",
        "text": "Invoice INV-001 Tongji University\nAmount 123.45",
        "page_count": 1,
        "text_character_count": 47,
    }


def test_execute_recognition_task_marks_image_upload_as_ocr_not_configured(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "invoice-scan.png"
    sample_path.write_bytes(b"fake-image-scan")
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="image/png",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "failed"
    assert item["failure"] == {
        "stage": "ocr",
        "reason": "ocr_not_configured",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id


def test_execute_recognition_task_marks_image_only_pdf_as_ocr_not_configured(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "image-only.pdf"
    sample_path.write_bytes(build_image_only_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")

    assert response.status_code == 200
    assert response.json()["item"]["failure"] == {
        "stage": "ocr",
        "reason": "ocr_not_configured",
    }


def test_execute_recognition_task_records_pdf_parse_failure_for_corrupted_pdf(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "broken.pdf"
    sample_path.write_bytes(b"not a pdf")
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["failure"] == {
        "stage": "pdf",
        "reason": "pdf_parse_failed",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id


def test_execute_recognition_task_records_blank_pdf(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "blank.pdf"
    sample_path.write_bytes(build_blank_pdf_bytes())
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["failure"] == {
        "stage": "pdf",
        "reason": "blank_pdf",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id


def test_execute_recognition_task_records_encrypted_pdf(tmp_path):
    client = make_client(tmp_path)
    sample_path = tmp_path / "encrypted.pdf"
    sample_path.write_bytes(build_blank_pdf_bytes(encrypted=True))
    task_id = create_task(client)
    material_id = upload_material(
        client,
        task_id,
        filename=sample_path.name,
        content=sample_path.read_bytes(),
        content_type="application/pdf",
    )
    recognition_task_id = latest_recognition_task_id(client, material_id)

    response = client.post(f"/api/recognition-tasks/{recognition_task_id}/execute")

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["failure"] == {
        "stage": "pdf",
        "reason": "encrypted_pdf",
    }
    assert item["raw_response"]["preparation"]["material_id"] == material_id

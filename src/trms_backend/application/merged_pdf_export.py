from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageSequence
from pypdf import PdfReader, PdfWriter

from trms_backend.domain.exports import MergedPdfExportPlan, MergedPdfSourceMaterialError
from trms_backend.domain.materials import MaterialRecord


def render_merged_pdf_bytes(
    *,
    export_plan: MergedPdfExportPlan,
    materials_by_id: dict[str, MaterialRecord],
    material_bytes_by_id: dict[str, bytes],
) -> bytes:
    writer = PdfWriter()

    for item in export_plan.ordered_items:
        if item.material_id is None:
            continue

        material = materials_by_id.get(item.material_id)
        if material is None:
            raise MergedPdfSourceMaterialError(item.material_id, "metadata is missing")

        raw_content = material_bytes_by_id.get(item.material_id)
        if raw_content is None:
            raise MergedPdfSourceMaterialError(item.material_id, "file content is missing from storage")

        for page in _iter_source_pdf_pages(material=material, raw_content=raw_content):
            writer.add_page(page)

    if len(writer.pages) == 0:
        raise ValueError("merged pdf export requires at least one readable material")

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _iter_source_pdf_pages(
    *,
    material: MaterialRecord,
    raw_content: bytes,
):
    if material.content_type == "application/pdf":
        reader = PdfReader(BytesIO(raw_content), strict=True)
        for page in reader.pages:
            yield page
        return

    if material.content_type in {"image/jpeg", "image/png", "image/webp"}:
        image_pdf = _render_image_pdf(raw_content)
        reader = PdfReader(BytesIO(image_pdf), strict=True)
        for page in reader.pages:
            yield page
        return

    raise MergedPdfSourceMaterialError(
        material.id,
        f"has unsupported content type {material.content_type or '<missing>'}",
    )


def _render_image_pdf(raw_content: bytes) -> bytes:
    with Image.open(BytesIO(raw_content)) as image:
        frames = [_normalize_image_frame(frame.copy()) for frame in ImageSequence.Iterator(image)]
        if not frames:
            frames = [_normalize_image_frame(image.copy())]

    first_frame = frames[0]
    extra_frames = frames[1:]
    buffer = BytesIO()
    try:
        first_frame.save(buffer, format="PDF", save_all=bool(extra_frames), append_images=extra_frames)
        return buffer.getvalue()
    finally:
        for frame in frames:
            frame.close()


def _normalize_image_frame(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        rgba_image.close()
        image.close()
        return background

    if image.mode != "RGB":
        converted = image.convert("RGB")
        image.close()
        return converted
    return image

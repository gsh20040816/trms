from trms_backend.application.metrics import MetricsCollector, NoOpMetricsCollector
from trms_backend.domain.invoice_validation import validate_invoice
from trms_backend.domain.invoices import (
    InvoiceRepository,
    ValidationRepository,
    ValidationResult,
)
from trms_backend.domain.materials import MaterialRecord, MaterialRepository
from trms_backend.domain.recognitions import RecognitionTaskRecord, RecognitionTaskRepository
from trms_backend.domain.tasks import TaskRepository


def _load_supporting_materials(
    invoice_id: str,
    *,
    invoice_repository: InvoiceRepository,
    material_repository: MaterialRepository,
) -> list[MaterialRecord]:
    supporting_materials = []
    for link in invoice_repository.list_supporting_material_links(invoice_id):
        material = material_repository.get(link.material_id)
        if material is not None:
            supporting_materials.append(material)
    return supporting_materials


def _load_supporting_material_recognitions(
    supporting_materials: list[MaterialRecord],
    *,
    recognition_task_repository: RecognitionTaskRepository,
) -> dict[str, RecognitionTaskRecord | None]:
    return {
        material.id: recognition_task_repository.get_latest_effective_by_material(material.id)
        for material in supporting_materials
    }


def refresh_invoice_validations(
    invoice_id: str,
    *,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    metrics_collector: MetricsCollector | None = None,
) -> list[ValidationResult] | None:
    invoice = invoice_repository.get(invoice_id)
    if invoice is None:
        return None
    task = task_repository.get(invoice.task_id)
    if task is None:
        return None

    invoice_material_recognition = recognition_task_repository.get_latest_effective_by_material(
        invoice.material_id
    )
    supporting_materials = _load_supporting_materials(
        invoice.id,
        invoice_repository=invoice_repository,
        material_repository=material_repository,
    )
    supporting_material_recognitions = _load_supporting_material_recognitions(
        supporting_materials,
        recognition_task_repository=recognition_task_repository,
    )
    stored_results = validation_repository.replace_for_invoice(
        invoice.id,
        validate_invoice(
            invoice,
            task,
            invoice_repository.find_duplicate_invoice_id(
                invoice.task_id,
                invoice.invoice_number,
                invoice.id,
            ),
            invoice_material_recognition,
            supporting_materials=supporting_materials,
            supporting_material_recognitions=supporting_material_recognitions,
        ),
    )
    (metrics_collector or NoOpMetricsCollector()).record_validation_results(results=stored_results)
    return stored_results


def refresh_validations_for_material(
    material_id: str,
    *,
    task_repository: TaskRepository,
    material_repository: MaterialRepository,
    invoice_repository: InvoiceRepository,
    validation_repository: ValidationRepository,
    recognition_task_repository: RecognitionTaskRepository,
    metrics_collector: MetricsCollector | None = None,
) -> dict[str, list[ValidationResult]]:
    affected_invoice_ids: list[str] = []
    primary_invoice = invoice_repository.get_by_material(material_id)
    if primary_invoice is not None:
        affected_invoice_ids.append(primary_invoice.id)
    for invoice in invoice_repository.list_by_supporting_material(material_id):
        if invoice.id not in affected_invoice_ids:
            affected_invoice_ids.append(invoice.id)

    refreshed: dict[str, list[ValidationResult]] = {}
    for invoice_id in affected_invoice_ids:
        results = refresh_invoice_validations(
            invoice_id,
            task_repository=task_repository,
            material_repository=material_repository,
            invoice_repository=invoice_repository,
            validation_repository=validation_repository,
            recognition_task_repository=recognition_task_repository,
            metrics_collector=metrics_collector,
        )
        if results is not None:
            refreshed[invoice_id] = results
    return refreshed

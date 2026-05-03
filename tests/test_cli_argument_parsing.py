import pytest

from trms_cli.cli import CliError, build_parser, resolve_confirm_expense_action


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            ["login", "--base-url", "http://example.com/api", "--member-id", "2250001", "--json"],
            {
                "command": "login",
                "base_url": "http://example.com/api",
                "member_id": "2250001",
                "json_output": True,
                "handler_name": "run_login_command",
            },
        ),
        (
            ["tasks", "--json"],
            {
                "command": "tasks",
                "json_output": True,
                "handler_name": "run_tasks_command",
            },
        ),
        (
            [
                "submit",
                "--task-id",
                "task-123",
                "--material-type",
                "invoice",
                "ticket.pdf",
                "receipt.png",
                "--json",
            ],
            {
                "command": "submit",
                "task_id": "task-123",
                "material_type": "invoice",
                "file_paths": ["ticket.pdf", "receipt.png"],
                "json_output": True,
                "handler_name": "run_submit_command",
            },
        ),
        (
            ["status", "--task-id", "task-123", "--json"],
            {
                "command": "status",
                "task_id": "task-123",
                "json_output": True,
                "handler_name": "run_status_command",
            },
        ),
        (
            ["missing-materials", "--task-id", "task-123", "--json"],
            {
                "command": "missing-materials",
                "task_id": "task-123",
                "json_output": True,
                "handler_name": "run_missing_materials_command",
            },
        ),
        (
            [
                "split",
                "--invoice-id",
                "invoice-001",
                "--member",
                "2250001:6000",
                "--member",
                "2250002:6345",
                "--json",
            ],
            {
                "command": "split",
                "invoice_id": "invoice-001",
                "members": ["2250001:6000", "2250002:6345"],
                "json_output": True,
                "handler_name": "run_split_command",
            },
        ),
        (
            ["confirm-expense", "--task-id", "task-123", "--json"],
            {
                "command": "confirm-expense",
                "task_id": "task-123",
                "split_id": None,
                "split_version": None,
                "status": None,
                "dispute_reason": None,
                "json_output": True,
                "handler_name": "run_confirm_expense_command",
            },
        ),
        (
            [
                "confirm-expense",
                "--task-id",
                "task-123",
                "--split-id",
                "split-001",
                "--split-version",
                "2",
                "--status",
                "disputed",
                "--dispute-reason",
                "amount mismatch",
            ],
            {
                "command": "confirm-expense",
                "task_id": "task-123",
                "split_id": "split-001",
                "split_version": 2,
                "status": "disputed",
                "dispute_reason": "amount mismatch",
                "json_output": False,
                "handler_name": "run_confirm_expense_command",
            },
        ),
    ],
)
def test_build_parser_accepts_supported_cli_commands(argv, expected):
    args = build_parser().parse_args(argv)

    for field_name, expected_value in expected.items():
        if field_name == "handler_name":
            assert args.handler.__name__ == expected_value
            continue
        assert getattr(args, field_name) == expected_value


@pytest.mark.parametrize(
    "argv",
    [
        ["login"],
        ["submit", "--task-id", "task-123", "--material-type", "invoice"],
        ["split", "--invoice-id", "invoice-001"],
    ],
)
def test_build_parser_rejects_missing_required_arguments(argv):
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(argv)

    assert excinfo.value.code == 2


def test_confirm_expense_defaults_to_list_mode_when_submit_arguments_absent():
    args = build_parser().parse_args(["confirm-expense", "--task-id", "task-123"])

    assert resolve_confirm_expense_action(args) == "list"


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ["confirm-expense", "--task-id", "task-123", "--split-id", "split-001"],
            "split version must be a positive integer when submitting expense confirmation",
        ),
        (
            [
                "confirm-expense",
                "--task-id",
                "task-123",
                "--split-id",
                "split-001",
                "--split-version",
                "1",
            ],
            "status is required when submitting expense confirmation",
        ),
        (
            [
                "confirm-expense",
                "--task-id",
                "task-123",
                "--split-id",
                "split-001",
                "--split-version",
                "1",
                "--status",
                "disputed",
            ],
            "dispute reason is required when submitting disputed confirmation",
        ),
        (
            [
                "confirm-expense",
                "--task-id",
                "task-123",
                "--split-id",
                "split-001",
                "--split-version",
                "1",
                "--status",
                "confirmed",
                "--dispute-reason",
                "should not be here",
            ],
            "dispute reason is only allowed with disputed status",
        ),
    ],
)
def test_confirm_expense_submit_argument_validation(argv, message):
    args = build_parser().parse_args(argv)

    with pytest.raises(CliError, match=message):
        resolve_confirm_expense_action(args)


def test_confirm_expense_submit_argument_validation_accepts_complete_payload():
    args = build_parser().parse_args(
        [
            "confirm-expense",
            "--task-id",
            "task-123",
            "--split-id",
            "split-001",
            "--split-version",
            "1",
            "--status",
            "disputed",
            "--dispute-reason",
            "  amount mismatch  ",
        ]
    )

    assert resolve_confirm_expense_action(args) == "submit"

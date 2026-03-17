from reqstool_python_decorators.decorators.decorators import SVCs

from requirements_example import RequirementsExample


@SVCs("SVC_010")
def test_greeting_message():
    example = RequirementsExample()
    result = example.greet("World")
    assert result == "Welcome, World!"


@SVCs("SVC_020")
def test_calculate_total():
    example = RequirementsExample()
    items = [{"price": 10.0}, {"price": 20.0}]
    assert example.calculate_total(items) == 30.0


@SVCs("SVC_030")
def test_export_report_design():
    pass


@SVCs("SVC_040")
def test_email_validation():
    example = RequirementsExample()
    assert example.validate_email("user@example.com")
    assert not example.validate_email("invalid")


@SVCs("SVC_050")
def test_sms_notification():
    example = RequirementsExample()
    example.send_sms("+1234567890", "Test alert")

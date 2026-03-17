from reqstool_python_decorators.decorators.decorators import Requirements, SVCs


@Requirements("REQ_PASS")
class RequirementsExample:
    """Example class implementing requirements."""

    @Requirements("REQ_MANUAL_FAIL")
    def calculate_total(self, items):
        return sum(item["price"] for item in items)

    @Requirements("REQ_FAILING_TEST")
    def validate_email(self, email):
        return "@" in email and "." in email.split("@")[1]

    @Requirements("REQ_SKIPPED_TEST")
    def send_sms(self, phone, message):
        raise NotImplementedError("SMS gateway removed")

    @Requirements("REQ_MISSING_TEST")
    def log_action(self, user, action):
        print(f"AUDIT: {user} performed {action}")

    @Requirements("REQ_OBSOLETE")
    def legacy_greet(self, name):
        return f"Hello, {name}!"

    def greet(self, name):
        return f"Welcome, {name}!"

"""
Custom exception classes for the PARSE API.
Exception handlers in main.py map these to proper HTTP error responses.
"""


class ProjectNotFound(Exception):
    """Raised when a project ID does not exist."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        super().__init__(f"Project not found: {project_id}")


class FeatureNotFound(Exception):
    """Raised when a feature_id is not in the grammar/typo registry."""

    def __init__(self, feature_id: str, registry: str = "registry"):
        self.feature_id = feature_id
        self.registry = registry
        super().__init__(f"Feature not found in {registry}: {feature_id}")


class RunNotFound(Exception):
    """Raised when a run ID does not exist."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        super().__init__(f"Run not found: {run_id}")


class ParseError(Exception):
    """Raised when parsing (e.g. upload or LLM output) fails."""

    def __init__(self, message: str):
        super().__init__(message)


class LLMError(Exception):
    """Raised when an LLM provider call fails (e.g. rate limit, API error)."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)

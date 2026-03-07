class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


class ModelLoadError(Exception):
    """Raised when model loading or training workflow fails."""


class PredictionError(Exception):
    """Raised when realtime or batch inference fails."""


class StorageError(Exception):
    """Raised when object storage interaction fails."""


class DatabaseError(Exception):
    """Raised when database interaction fails."""


class DriftDetectionError(Exception):
    """Raised when drift detection pipeline fails."""
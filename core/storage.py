from whitenoise.storage import CompressedManifestStaticFilesStorage as Base


class StaticStorage(Base):
    """
    Custom static files storage with non-strict manifest.
    This prevents 500 errors when some static files are missing from manifest.
    """
    manifest_strict = False


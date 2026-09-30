from backend.models import CanonicalModel, ID


class RegistryQuery(CanonicalModel):
    registry_revision: ID | None = None

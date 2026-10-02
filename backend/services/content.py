"""Frozen schematic and scene metadata, independent of numerical availability."""
from backend.models.content import MechanismContent, SceneList, ScenePreset
from backend.registry import content_registry


class ContentService:
    registry_revision = f"content-registry-v{content_registry.CONTENT_VERSION}"
    data_revision = f"content-schematic-v{content_registry.CONTENT_VERSION}"

    def list_scenes(self) -> SceneList:
        return content_registry.load_scenes()

    def get_scene(self, scene_id: int) -> ScenePreset:
        return content_registry.get_scene(scene_id)

    def load_mechanism(self) -> MechanismContent:
        return content_registry.load_mechanism()

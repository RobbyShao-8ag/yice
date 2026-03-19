"""
DataLoader for the yice decision system.

Loads and validates JSON data files at startup:
- hexagrams.json - 64 hexagrams with gua辞 and image
- lines.json - 386 yao lines with analysis
- yao_attributes.json - attribute mappings for each yao position
- scene_mapping.json - scene to hexagram mapping
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from core.errors import DataError

logger = logging.getLogger(__name__)

# Default data directory
DEFAULT_DATA_DIR = "data"

# Required fields for each data type
HEXAGRAM_REQUIRED_FIELDS = ["id", "name", "gua_ci", "image", "judgement"]
LINE_REQUIRED_FIELDS = ["id", "hexagram_id", "position", "yao_name", "text"]
YAO_ATTR_REQUIRED_FIELDS = ["position", "na_jia_gan", "na_jia_zhi", "wuxing", "liu_qin", "is_shi", "is_ying", "is_fei", "is_fu"]
SCENE_REQUIRED_FIELDS = ["hexagram_id", "hexagram_name"]


@dataclass
class DataLoaderConfig:
    """Configuration for DataLoader."""

    data_dir: str = DEFAULT_DATA_DIR
    hexagrams_path: Optional[str] = None
    lines_path: Optional[str] = None
    yao_attrs_path: Optional[str] = None
    scene_mapping_path: Optional[str] = None
    validate: bool = False  # Enable completeness validation


class DataLoader:
    """Loads and validates JSON data files for the yice system.

    Responsible for:
    - Loading hexagrams, lines, yao_attributes, scene_mapping
    - Validating data integrity (IDs, references, required fields)
    - Sorting lines by hexagram_id
    - Handling errors gracefully with fallback to defaults
    """

    def __init__(self, config: Optional[DataLoaderConfig] = None):
        self._config = config or DataLoaderConfig()
        self._data_dir = self._config.data_dir

        # Initialize data containers
        self._hexagrams: dict[int, dict[str, Any]] = {}
        self._lines: list[dict[str, Any]] = []
        self._yao_attributes: dict[int, dict[str, Any]] = {}
        self._scene_mapping: dict[str, dict[str, Any]] = {}

        # Load all data
        self._load_all()

    def _get_path(self, filename: str, custom_path: Optional[str]) -> Optional[str]:
        """Get file path - use custom path if provided, otherwise construct from data_dir."""
        if custom_path:
            return custom_path
        if self._data_dir:
            return os.path.join(self._data_dir, filename)
        return None

    def _load_json_file(self, filename: str, custom_path: Optional[str] = None) -> dict:
        """Load a JSON file with error handling.

        Args:
            filename: Name of the JSON file
            custom_path: Optional custom path to file

        Returns:
            Loaded JSON data as dict

        Raises:
            DataError: If file cannot be loaded
        """
        path = self._get_path(filename, custom_path)

        if not path:
            raise DataError(f"No path specified for {filename}")

        if not os.path.exists(path):
            raise DataError(f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Loaded {filename} from {path}")
                return data
        except json.JSONDecodeError as e:
            raise DataError(f"Invalid JSON in {path}: {e}")
        except Exception as e:
            raise DataError(f"Failed to load {path}: {e}")

    def _load_hexagrams(self) -> None:
        """Load and validate hexagrams data."""
        path = self._get_path("hexagrams.json", self._config.hexagrams_path)

        if not path or not os.path.exists(path):
            logger.warning("hexagrams.json not found, using empty data")
            self._hexagrams = {}
            return

        try:
            data = self._load_json_file("hexagrams.json", self._config.hexagrams_path)

            # Validate structure
            if not isinstance(data, dict):
                raise DataError("hexagrams.json must be a dictionary")

            # Check for duplicate IDs
            seen_ids = set()
            for hex_id, hex_data in data.items():
                hex_id_int = int(hex_id)
                if hex_id_int in seen_ids:
                    raise DataError(f"Duplicate hexagram ID: {hex_id}")
                seen_ids.add(hex_id_int)

                # Validate required fields
                for field in HEXAGRAM_REQUIRED_FIELDS:
                    if field not in hex_data:
                        raise DataError(
                            f"Hexagram {hex_id} missing required field: {field}"
                        )

            self._hexagrams = {int(k): v for k, v in data.items()}

        except DataError:
            raise
        except Exception as e:
            raise DataError(f"Failed to load hexagrams: {e}")

    def _load_lines(self) -> None:
        """Load and validate lines data."""
        path = self._get_path("lines.json", self._config.lines_path)

        if not path or not os.path.exists(path):
            logger.warning("lines.json not found, using empty data")
            self._lines = []
            return

        try:
            data = self._load_json_file("lines.json", self._config.lines_path)

            # Validate structure
            if not isinstance(data, list):
                raise DataError("lines.json must be a list")

            # Check for duplicate IDs
            seen_ids = set()
            for line in data:
                line_id = line.get("id")
                if line_id in seen_ids:
                    raise DataError(f"Duplicate line ID: {line_id}")
                seen_ids.add(line_id)

                # Validate required fields
                for field in LINE_REQUIRED_FIELDS:
                    if field not in line:
                        raise DataError(
                            f"Line {line_id} missing required field: {field}"
                        )

                # Validate hexagram_id reference
                hex_id = line.get("hexagram_id")
                if hex_id not in self._hexagrams:
                    logger.warning(
                        f"Line {line_id} references non-existent hexagram_id: {hex_id}"
                    )

            # Sort lines by hexagram_id
            self._lines = sorted(data, key=lambda x: x.get("hexagram_id", 0))

        except DataError:
            raise
        except Exception as e:
            raise DataError(f"Failed to load lines: {e}")

    def _load_yao_attributes(self) -> None:
        """Load and validate yao_attributes data."""
        path = self._get_path("yao_attributes.json", self._config.yao_attrs_path)

        if not path or not os.path.exists(path):
            logger.warning("yao_attributes.json not found, using empty data")
            self._yao_attributes = {}
            return

        try:
            data = self._load_json_file(
                "yao_attributes.json", self._config.yao_attrs_path
            )

            # Handle both list and dict formats
            if isinstance(data, list):
                # List format: convert to dict keyed by "hexagram_id-position"
                for attrs in data:
                    line_id = attrs.get("line_id", "")
                    hex_id = attrs.get("hexagram_id")
                    pos = attrs.get("position")
                    if hex_id and pos:
                        key = f"{hex_id}-{pos}"
                        self._yao_attributes[key] = attrs
            elif isinstance(data, dict):
                # Dict format: convert keys to int if possible
                for k, v in data.items():
                    try:
                        int_key = int(k)
                        self._yao_attributes[int_key] = v
                    except (ValueError, TypeError):
                        # Keep as-is for non-numeric keys
                        self._yao_attributes[k] = v
            else:
                raise DataError("yao_attributes.json must be a list or dictionary")

            # Validate required fields on first record if data exists
            if self._yao_attributes:
                first_record = next(iter(self._yao_attributes.values()))
                for field in YAO_ATTR_REQUIRED_FIELDS:
                    if field not in first_record:
                        raise DataError(
                            f"Yao attribute missing required field: {field}"
                        )

        except DataError:
            raise
        except Exception as e:
            raise DataError(f"Failed to load yao_attributes: {e}")

    def _load_scene_mapping(self) -> None:
        """Load and validate scene_mapping data."""
        path = self._get_path("scene_mapping.json", self._config.scene_mapping_path)

        if not path or not os.path.exists(path):
            logger.warning("scene_mapping.json not found, using empty data")
            self._scene_mapping = {}
            return

        try:
            data = self._load_json_file(
                "scene_mapping.json", self._config.scene_mapping_path
            )

            # Validate structure
            if not isinstance(data, dict):
                raise DataError("scene_mapping.json must be a dictionary")

            for scene_key, scene_data in data.items():
                # Validate required fields
                for field in SCENE_REQUIRED_FIELDS:
                    if field not in scene_data:
                        raise DataError(
                            f"Scene '{scene_key}' missing required field: {field}"
                        )

                # Validate hexagram_id reference
                hex_id = scene_data.get("hexagram_id")
                if hex_id not in self._hexagrams:
                    logger.warning(
                        f"Scene '{scene_key}' references non-existent hexagram_id: {hex_id}"
                    )

            self._scene_mapping = data

        except DataError:
            raise
        except Exception as e:
            raise DataError(f"Failed to load scene_mapping: {e}")

    def _load_all(self) -> None:
        """Load all data files in proper order."""
        self._hexagrams = {}
        self._yao_attributes = {}
        self._scene_mapping = {}
        self._lines = []

        # Load hexagrams first (other data depends on it)
        self._load_hexagrams()

        # Load other data
        self._load_yao_attributes()
        self._load_scene_mapping()

        # Lines must be loaded after hexagrams (for validation)
        self._load_lines()

        # Validate data completeness if enabled
        if self._config.validate:
            self._validate_completeness()

    @property
    def hexagrams(self) -> dict[int, dict[str, Any]]:
        """Get loaded hexagrams data."""
        return self._hexagrams

    @property
    def lines(self) -> list[dict[str, Any]]:
        """Get loaded lines data (sorted by hexagram_id)."""
        return self._lines

    @property
    def yao_attributes(self) -> dict[int, dict[str, Any]]:
        """Get loaded yao_attributes data."""
        return self._yao_attributes

    @property
    def scene_mapping(self) -> dict[str, dict[str, Any]]:
        """Get loaded scene_mapping data."""
        return self._scene_mapping

    def get_hexagram(self, hexagram_id: int) -> Optional[dict[str, Any]]:
        """Get a specific hexagram by ID."""
        return self._hexagrams.get(hexagram_id)

    def get_lines_for_hexagram(self, hexagram_id: int) -> list[dict[str, Any]]:
        """Get all lines for a specific hexagram."""
        return [line for line in self._lines if line.get("hexagram_id") == hexagram_id]

    def get_yao_attribute(self, position: int) -> Optional[dict[str, Any]]:
        """Get yao attribute for a specific position (1-6).
        
        Note: Keys in _yao_attributes may be int or str depending on data source.
        This method checks both for compatibility.
        """
        # Try int key first
        result = self._yao_attributes.get(position)
        if result is not None:
            return result
        # Fall back to str key
        return self._yao_attributes.get(str(position))

    def get_scene(self, scene_key: str) -> Optional[dict[str, Any]]:
        """Get scene data for a specific key."""
        return self._scene_mapping.get(scene_key)

    # Expected counts for validation
    EXPECTED_HEXAGRAM_COUNT = 64
    EXPECTED_LINE_COUNT = 386  # 64 * 6 + 2 (乾卦和坤卦的用九/用六)
    MIN_SCENE_COUNT = 50

    def _validate_completeness(self) -> None:
        """Validate data completeness after loading.

        Only validates when data files exist and have content.
        Skip validation for missing files (handled by existing warnings).

        Raises:
            DataError: If data is incomplete or invalid
        """
        # Skip validation if no hexagrams loaded (file missing)
        if not self._hexagrams:
            return

        errors: list[str] = []

        # Validate hexagrams: must have exactly 64 records with IDs 1-64
        hex_count = len(self._hexagrams)
        if hex_count != self.EXPECTED_HEXAGRAM_COUNT:
            errors.append(
                f"hexagrams.json: expected {self.EXPECTED_HEXAGRAM_COUNT} records, "
                f"found {hex_count}"
            )
        else:
            # Check for continuous IDs 1-64
            missing_ids = set(range(1, 65)) - set(self._hexagrams.keys())
            if missing_ids:
                errors.append(
                    f"hexagrams.json: missing hexagram IDs: {sorted(missing_ids)}"
                )

        # Validate lines: must have 386 records (64*6 + 2)
        # Only validate if lines file exists (has content)
        if self._lines:
            line_count = len(self._lines)
            if line_count != self.EXPECTED_LINE_COUNT:
                errors.append(
                    f"lines.json: expected {self.EXPECTED_LINE_COUNT} records, "
                    f"found {line_count}"
                )
            else:
                # Check all lines reference valid hexagram_id
                invalid_refs = []
                for line in self._lines:
                    hex_id = line.get("hexagram_id")
                    if hex_id not in self._hexagrams:
                        invalid_refs.append(
                            f"line id={line.get('id')}: invalid hexagram_id={hex_id}"
                        )
                if invalid_refs:
                    errors.append(
                        f"lines.json: {len(invalid_refs)} lines reference invalid hexagram_ids: "
                        f"{invalid_refs[:5]}{'...' if len(invalid_refs) > 5 else ''}"
                    )

        # Validate scene_mapping: minimum 50 scene keys
        # Only validate if scene_mapping file exists (has content)
        if self._scene_mapping:
            scene_count = len(self._scene_mapping)
            if scene_count < self.MIN_SCENE_COUNT:
                errors.append(
                    f"scene_mapping.json: expected at least {self.MIN_SCENE_COUNT} scenes, "
                    f"found {scene_count}"
                )

        if errors:
            raise DataError(
                "Data validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    def reload(self) -> None:
        """Reload all data files."""
        self._load_all()


# =============================================================================
# Module-level data access functions
# =============================================================================

import os
from typing import Any, Optional

# Default data directory
_DATA_DIR = "data"

# Module-level caches
_yao_attributes_data: Optional[list[dict[str, Any]]] = None
_shi_ying_data: Optional[list[dict[str, Any]]] = None
_hexagram_relations_data: Optional[list[dict[str, Any]]] = None

# Pre-built lookups
_yao_attributes_by_key: Optional[dict[str, dict[str, Any]]] = None
_shi_ying_by_hexagram_id: Optional[dict[int, dict[str, Any]]] = None


def _get_data_path(filename: str) -> str:
    """Get path to data file."""
    return os.path.join(_DATA_DIR, filename)


def load_yao_attributes() -> list[dict[str, Any]]:
    """Load yao_attributes data from JSON file.
    
    Returns:
        List of yao attribute records.
    """
    global _yao_attributes_data, _yao_attributes_by_key
    
    if _yao_attributes_data is not None:
        return _yao_attributes_data
    
    path = _get_data_path("yao_attributes.json")
    if not os.path.exists(path):
        _yao_attributes_data = []
        return _yao_attributes_data
    
    with open(path, "r", encoding="utf-8") as f:
        _yao_attributes_data = json.load(f)
    
    # Build lookup by line_id
    _yao_attributes_by_key = {
        record["line_id"]: record for record in _yao_attributes_data
    }
    
    return _yao_attributes_data


def get_yao_attributes(hexagram_id: int, position: int) -> Optional[dict[str, Any]]:
    """Get yao attributes for given hexagram and position.
    
    Args:
        hexagram_id: Hexagram ID (1-64)
        position: Yao position (1-6)
    
    Returns:
        Yao attribute record or None if not found.
    """
    global _yao_attributes_by_key
    
    if _yao_attributes_by_key is None:
        load_yao_attributes()
    
    key = f"{hexagram_id}-{position}"
    return _yao_attributes_by_key.get(key)


def load_shi_ying() -> list[dict[str, Any]]:
    """Load shi-ying data from JSON file.
    
    Returns:
        List of shi-ying records.
    """
    global _shi_ying_data, _shi_ying_by_hexagram_id
    
    if _shi_ying_data is not None:
        return _shi_ying_data
    
    path = _get_data_path("shi_ying.json")
    if not os.path.exists(path):
        _shi_ying_data = []
        return _shi_ying_data
    
    with open(path, "r", encoding="utf-8") as f:
        _shi_ying_data = json.load(f)
    
    # Build lookup by hexagram_id
    _shi_ying_by_hexagram_id = {
        record["hexagram_id"]: record for record in _shi_ying_data
    }
    
    return _shi_ying_data


def get_shi_ying(hexagram_id: int) -> Optional[dict[str, Any]]:
    """Get shi-ying info for given hexagram.
    
    Args:
        hexagram_id: Hexagram ID (1-64)
    
    Returns:
        Shi-ying record or None if not found.
    """
    global _shi_ying_by_hexagram_id
    
    if _shi_ying_by_hexagram_id is None:
        load_shi_ying()
    
    return _shi_ying_by_hexagram_id.get(hexagram_id)


def load_hexagram_relations() -> list[dict[str, Any]]:
    """Load hexagram_relations data from JSON file.
    
    Returns:
        List of hexagram relation records.
    """
    global _hexagram_relations_data
    
    if _hexagram_relations_data is not None:
        return _hexagram_relations_data
    
    path = _get_data_path("hexagram_relations.json")
    if not os.path.exists(path):
        _hexagram_relations_data = []
        return _hexagram_relations_data
    
    with open(path, "r", encoding="utf-8") as f:
        _hexagram_relations_data = json.load(f)
    
    return _hexagram_relations_data


def get_hexagram_relations(hexagram_id: int, relation_type: str) -> list[dict[str, Any]]:
    """Get all relations of given type for hexagram.
    
    Args:
        hexagram_id: Source hexagram ID (1-64)
        relation_type: Relation type (错卦/综卦/交卦/互卦)
    
    Returns:
        List of matching relation records.
    """
    data = load_hexagram_relations()
    return [
        r for r in data 
        if r.get("source_id") == hexagram_id and r.get("relation_type") == relation_type
    ]


def reload_all() -> None:
    """Reload all module-level cached data."""
    global _yao_attributes_data, _shi_ying_data, _hexagram_relations_data
    global _yao_attributes_by_key, _shi_ying_by_hexagram_id
    
    _yao_attributes_data = None
    _shi_ying_data = None
    _hexagram_relations_data = None
    _yao_attributes_by_key = None
    _shi_ying_by_hexagram_id = None

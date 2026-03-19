#!/usr/bin/env python3
"""
Data generation script for yice I Ching decision system.

Generates hexagram, line, and scene mapping data using LLM.
Supports validation of generated data and adds new fields:
- xiang_ci (象辞)
- symbolism (卦象象征)
- gua_zhu_position (卦主爻位)

Usage:
    python scripts/generate_data.py --stage all     # Generate all data
    python scripts/generate_data.py --stage 1      # Generate hexagrams only
    python scripts/generate_data.py --stage 2      # Generate lines only
    python scripts/generate_data.py --stage 3      # Generate scene mapping only
    python scripts/generate_data.py --validate     # Validate existing data
"""

import argparse
import json
import logging
import os
import re
import sys
from typing import Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Import for stage 4-6 (use inline to avoid circular imports)
import importlib.util
from core.llm_client import LLMClient, LLMConfig, load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = "data"

# Required fields for each data type (from data_loader.py)
HEXAGRAM_REQUIRED_FIELDS = [
    "id",
    "name",
    "gua_ci",
    "image",
    "judgement",
    "xiang_ci",
    "symbolism",
    "gua_zhu_position",  # New fields
]
LINE_REQUIRED_FIELDS = ["id", "hexagram_id", "position", "yao_name", "text"]
SCENE_REQUIRED_FIELDS = ["hexagram_id", "hexagram_name"]

# Trigram mapping for symbolism generation
TRIGRAMS = {
    1: {"name": "乾", "symbolism": "天", "nature": "刚健"},
    2: {"name": "坤", "symbolism": "地", "nature": "柔顺"},
    3: {"name": "震", "symbolism": "雷", "nature": "震动"},
    4: {"name": "巽", "symbolism": "风", "nature": "入"},
    5: {"name": "坎", "symbolism": "水", "nature": "险陷"},
    6: {"name": "离", "symbolism": "火", "nature": "光明"},
    7: {"name": "艮", "symbolism": "山", "nature": "静止"},
    8: {"name": "兑", "symbolism": "泽", "nature": "喜悦"},
}

# Traditional gua_zhu positions for each hexagram (1-64)
# Based on traditional "卦主" theory - main yao position for each hexagram
# These are the positions that typically carry the main meaning
GUA_ZHU_TRADITIONAL = {
    1: 5,
    2: 2,
    3: 1,
    4: 2,
    5: 5,
    6: 2,
    7: 2,
    8: 5,
    9: 5,
    10: 2,
    11: 5,
    12: 2,
    13: 5,
    14: 5,
    15: 2,
    16: 5,
    17: 5,
    18: 3,
    19: 5,
    20: 2,
    21: 5,
    22: 2,
    23: 2,
    24: 1,
    25: 5,
    26: 5,
    27: 1,
    28: 5,
    29: 2,
    30: 5,
    31: 2,
    32: 5,
    33: 2,
    34: 5,
    35: 3,
    36: 5,
    37: 5,
    38: 2,
    39: 2,
    40: 2,
    41: 3,
    42: 5,
    43: 5,
    44: 5,
    45: 5,
    46: 5,
    47: 2,
    48: 2,
    49: 5,
    50: 3,
    51: 1,
    52: 3,
    53: 4,
    54: 2,
    55: 5,
    56: 3,
    57: 4,
    58: 2,
    59: 2,
    60: 2,
    61: 5,
    62: 4,
    63: 5,
    64: 3,
}


class ValidationError(Exception):
    """Raised when data validation fails."""

    pass


def ensure_data_dir() -> None:
    """Ensure data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json_file(filepath: str) -> Any:
    """Load JSON file."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(filepath: str, data: Any) -> None:
    """Save data to JSON file."""
    ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_llm_config(config_path: str, provider: str = "minimax") -> LLMConfig:
    """Load LLM configuration from nested models.json structure.

    Args:
        config_path: Path to config file (models.json).
        provider: Provider name to use (default: minimax).

    Returns:
        LLMConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle nested structure: data["providers"][provider]
    if "providers" in data:
        provider_config = data["providers"].get(provider)
        if not provider_config:
            raise ValueError(f"Provider '{provider}' not found in config")

        return LLMConfig(
            provider=provider,
            api_key=provider_config["api_key"],
            base_url=provider_config.get("base_url", "https://api.openai.com"),
            model=provider_config.get("default_model", "gpt-3.5-turbo"),
            timeout=provider_config.get("timeout", 60),
            max_retries=provider_config.get("max_retries", 3),
        )

    # Fallback to flat structure (for backward compatibility)
    required = ["provider", "api_key", "model"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Missing required config fields: {missing}")

    return LLMConfig(
        provider=data["provider"],
        api_key=data["api_key"],
        base_url=data.get("base_url", "https://api.openai.com"),
        model=data["model"],
        timeout=data.get("timeout", 60),
        max_retries=data.get("max_retries", 3),
    )


# ===================== VALIDATION FUNCTIONS =====================


def validate_hexagram_schema(hexagram_data: dict[str, Any], hex_id: str) -> list[str]:
    """
    Validate hexagram has required fields and correct types.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Check required fields
    for field in HEXAGRAM_REQUIRED_FIELDS:
        if field not in hexagram_data:
            errors.append(f"Hexagram {hex_id}: missing required field '{field}'")

    # Validate hexagram_id is in range 1-64
    if "id" in hexagram_data:
        hex_id_val = hexagram_data.get("id")
        if not isinstance(hex_id_val, int) or not (1 <= hex_id_val <= 64):
            errors.append(
                f"Hexagram {hex_id}: id must be integer 1-64, got {hex_id_val}"
            )

    # Validate gua_zhu_position is in range 1-6
    if "gua_zhu_position" in hexagram_data:
        pos = hexagram_data.get("gua_zhu_position")
        if not isinstance(pos, int) or not (1 <= pos <= 6):
            errors.append(f"Hexagram {hex_id}: gua_zhu_position must be 1-6, got {pos}")

    return errors


def validate_line_schema(line: dict[str, Any]) -> list[str]:
    """
    Validate line has required fields and correct types.

    Returns list of validation errors (empty if valid).
    """
    errors = []
    line_id = line.get("id", "unknown")

    # Check required fields
    for field in LINE_REQUIRED_FIELDS:
        if field not in line:
            errors.append(f"Line {line_id}: missing required field '{field}'")

    # Validate hexagram_id reference
    if "hexagram_id" in line:
        hex_id = line.get("hexagram_id")
        if not isinstance(hex_id, int) or not (1 <= hex_id <= 64):
            errors.append(f"Line {line_id}: hexagram_id must be 1-64, got {hex_id}")

    # Validate position is 1-6
    if "position" in line:
        pos = line.get("position")
        if not isinstance(pos, int) or not (1 <= pos <= 6):
            errors.append(f"Line {line_id}: position must be 1-6, got {pos}")

    return errors


def validate_cross_file_references(
    hexagrams: dict[str, Any],
    lines: list[dict[str, Any]],
    scene_mapping: dict[str, Any],
) -> list[str]:
    """
    Validate cross-file references.

    - lines.json hexagram_id must exist in hexagrams.json
    - scene_mapping.json hexagram_id must exist in hexagrams.json

    Returns list of validation errors.
    """
    errors = []

    # Build set of valid hexagram IDs
    valid_ids = set(int(k) for k in hexagrams.keys())

    # Validate lines references
    for line in lines:
        line_id = line.get("id", "unknown")
        hex_id = line.get("hexagram_id")
        if hex_id is not None and hex_id not in valid_ids:
            errors.append(
                f"Line {line_id}: references non-existent hexagram_id {hex_id}"
            )

    # Validate scene_mapping references
    for scene_key, scene_data in scene_mapping.items():
        hex_id = scene_data.get("hexagram_id")
        if hex_id is not None and hex_id not in valid_ids:
            errors.append(
                f"Scene '{scene_key}': references non-existent hexagram_id {hex_id}"
            )

    return errors


def detect_duplicates(
    hexagrams: dict[str, Any], lines: list[dict[str, Any]]
) -> list[str]:
    """
    Detect duplicate data.

    - Duplicate hexagram_id
    - Duplicate line id

    Returns list of validation errors.
    """
    errors = []

    # Check duplicate hexagram IDs
    seen_hex_ids = set()
    for hex_id_str in hexagrams.keys():
        hex_id = int(hex_id_str)
        if hex_id in seen_hex_ids:
            errors.append(f"Duplicate hexagram_id: {hex_id}")
        seen_hex_ids.add(hex_id)

    # Check duplicate line IDs
    seen_line_ids = set()
    for line in lines:
        line_id = line.get("id")
        if line_id in seen_line_ids:
            errors.append(f"Duplicate line id: {line_id}")
        seen_line_ids.add(line_id)

    return errors


def validate_all_data() -> bool:
    """
    Validate all existing data files.

    Returns True if validation passes, False otherwise.
    """
    logger.info("Validating existing data...")

    hexagrams_path = os.path.join(DATA_DIR, "hexagrams.json")
    lines_path = os.path.join(DATA_DIR, "lines.json")
    scene_mapping_path = os.path.join(DATA_DIR, "scene_mapping.json")

    # Load data
    hexagrams = load_json_file(hexagrams_path) or {}
    lines = load_json_file(lines_path) or []
    scene_mapping = load_json_file(scene_mapping_path) or {}

    all_errors = []

    # Schema validation for hexagrams
    for hex_id, hex_data in hexagrams.items():
        errors = validate_hexagram_schema(hex_data, hex_id)
        all_errors.extend(errors)

    # Schema validation for lines
    for line in lines:
        errors = validate_line_schema(line)
        all_errors.extend(errors)

    # Cross-file reference validation
    ref_errors = validate_cross_file_references(hexagrams, lines, scene_mapping)
    all_errors.extend(ref_errors)

    # Duplicate detection
    dup_errors = detect_duplicates(hexagrams, lines)
    all_errors.extend(dup_errors)

    if all_errors:
        logger.error(f"Validation failed with {len(all_errors)} errors:")
        for error in all_errors:
            logger.error(f"  - {error}")
        return False

    logger.info("Validation passed!")
    return True


# ===================== DATA GENERATION FUNCTIONS =====================


def get_trigram_id(trigram_name: str) -> int:
    """Get trigram ID by name."""
    trigram_map = {
        "乾": 1,
        "坤": 2,
        "震": 3,
        "巽": 4,
        "坎": 5,
        "离": 6,
        "艮": 7,
        "兑": 8,
    }
    return trigram_map.get(trigram_name, 1)


def generate_xiang_ci(hexagram: dict[str, Any]) -> str:
    """
    Generate xiang_ci (象辞) - The Image Commentary from 象传.

    Format: "{上卦}{下卦}，{卦名}。{君子以...}"
    """
    upper = hexagram.get("upper_trigram", "乾")
    lower = hexagram.get("lower_trigram", "乾")
    name = hexagram.get("name", "卦")
    image = hexagram.get("image", "")

    # Extract "君子以..." part from image if available
    junzi_part = ""
    if "君子以" in image:
        junzi_part = image[image.find("君子以") :]
    else:
        junzi_part = f"君子以{image}" if image else "君子以自强不息"

    return f"{upper}{lower}，{name}。{junzi_part}"


def generate_symbolism(hexagram: dict[str, Any]) -> str:
    """
    Generate symbolism (卦象象征) - Natural symbolism.

    Format: "{上卦名}为{上卦象}，{下卦名}为{下卦象}"
    E.g., "乾为天，坤为地"
    """
    upper = hexagram.get("upper_trigram", "乾")
    lower = hexagram.get("lower_trigram", "坤")

    upper_id = get_trigram_id(upper)
    lower_id = get_trigram_id(lower)

    upper_symbolism = TRIGRAMS.get(upper_id, {}).get("symbolism", "天")
    lower_symbolism = TRIGRAMS.get(lower_id, {}).get("symbolism", "地")

    return f"{upper}为{upper_symbolism}，{lower}为{lower_symbolism}"


def get_gua_zhu_position(hexagram_id: int) -> int:
    """
    Get gua_zhu_position (卦主爻位) - Main yao position for the hexagram.

    Uses traditional theory to determine which yao carries the main meaning.
    """
    return GUA_ZHU_TRADITIONAL.get(hexagram_id, 5)


def generate_hexagram_data(client: Optional[LLMClient]) -> dict[int, dict[str, Any]]:
    """
    Generate hexagram data for all 64 hexagrams.

    Uses LLM to generate base data, then adds new fields locally.
    """
    logger.info("Generating hexagram data...")

    hexagrams_path = os.path.join(DATA_DIR, "hexagrams.json")
    existing_data = load_json_file(hexagrams_path)

    if existing_data:
        logger.info(f"Found existing hexagrams.json with {len(existing_data)} entries")
        hexagrams = {int(k): v for k, v in existing_data.items()}
    else:
        logger.info("No existing hexagrams.json found, generating from scratch...")
        hexagrams = {}

    required_base_fields = ["name", "gua_ci", "image", "judgement"]

    for hex_id in range(1, 65):
        needs_regeneration = hex_id not in hexagrams
        if hex_id in hexagrams:
            existing = hexagrams[hex_id]
            missing = [
                f
                for f in required_base_fields
                if f not in existing or not existing.get(f)
            ]
            if missing:
                logger.info(
                    f"Hexagram {hex_id} missing fields {missing}, regenerating..."
                )
                needs_regeneration = True
            else:
                logger.info(
                    f"Hexagram {hex_id} already complete, adding derived fields..."
                )

        if needs_regeneration:
            hexagram = _generate_single_hexagram(client, hex_id)
        else:
            hexagram = hexagrams[hex_id]

        hexagram["id"] = hex_id
        hexagram["xiang_ci"] = generate_xiang_ci(hexagram)
        hexagram["symbolism"] = generate_symbolism(hexagram)
        hexagram["gua_zhu_position"] = get_gua_zhu_position(hex_id)

        hexagrams[hex_id] = hexagram

        if hex_id % 10 == 0:
            logger.info(f"Generated {hex_id}/64 hexagrams...")
            save_json_file(os.path.join(DATA_DIR, "hexagrams.json"), hexagrams)
            logger.info(f"Saved progress to hexagrams.json")

    return hexagrams


def _generate_single_hexagram(
    client: Optional[LLMClient], hex_id: int
) -> dict[str, Any]:
    """
    Generate a single hexagram's basic data via LLM.

    Calls LLM to generate proper hexagram data with all required fields.
    """
    if client is None:
        logger.warning(
            f"No LLM client available for hexagram {hex_id}, using placeholder"
        )
        return _get_placeholder_hexagram(hex_id)

    system_prompt = """你是一位精通周易的专家。请根据用户提供的卦序号，生成该卦的详细信息。

请以JSON格式返回，包含以下字段：
- number: 卦序号 (整数)
- name: 卦名 (如"乾"、"坤"等)
- symbol: Unicode卦象符号
- upper_trigram: 上卦名 (如"乾"、"坤"、"震"等)
- lower_trigram: 下卦名
- gua_ci: 卦辞原文
- image: 大象辞 (象传原文，如"天行健，君子以自强不息")
- judgement: 彖辞或卦辞解释

注意：所有内容必须准确引用传统周易原文，不可编造。"""

    user_prompt = f"""请生成周易第{hex_id}卦的详细信息，以JSON格式返回。只返回JSON，不要其他文字。"""

    try:
        response = client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        json_str = _extract_json_from_response(response)
        if not json_str:
            logger.error(f"No JSON found in LLM response for hexagram {hex_id}")
            return _get_placeholder_hexagram(hex_id)

        hexagram_data = json.loads(json_str)

        required_fields = [
            "number",
            "name",
            "symbol",
            "upper_trigram",
            "lower_trigram",
            "gua_ci",
            "image",
            "judgement",
        ]
        for field in required_fields:
            if field not in hexagram_data:
                logger.warning(
                    f"LLM response missing field '{field}' for hexagram {hex_id}"
                )
                hexagram_data[field] = _get_placeholder_hexagram(hex_id).get(field, "")

        logger.info(
            f"Generated hexagram {hex_id}: {hexagram_data.get('name', 'unknown')}"
        )
        return hexagram_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response for hexagram {hex_id}: {e}")
        return _get_placeholder_hexagram(hex_id)
    except Exception as e:
        logger.error(f"LLM call failed for hexagram {hex_id}: {e}")
        return _get_placeholder_hexagram(hex_id)


def _extract_json_from_response(response: str) -> Optional[str]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    if not response:
        return None

    json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
    if json_match:
        return json_match.group(1).strip()

    brace_match = re.search(r"\{[\s\S]*\}", response)
    if brace_match:
        return brace_match.group(0)

    return response if response.strip().startswith("{") else None


def _get_placeholder_hexagram(hex_id: int) -> dict[str, Any]:
    """Return placeholder hexagram data when LLM is unavailable."""
    return {
        "number": hex_id,
        "name": f"卦{hex_id}",
        "symbol": "䷀",
        "upper_trigram": "乾",
        "lower_trigram": "乾",
        "gua_ci": "元亨利贞",
        "image": "天行健，君子以自强不息",
        "judgement": "元亨利贞",
    }


def generate_line_data(
    client: Optional[LLMClient], hexagrams: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Generate line data for all hexagrams.

    Each hexagram has 6 lines (positions 1-6), plus optional 用九/用六.
    """
    logger.info("Generating line data...")

    lines_path = os.path.join(DATA_DIR, "lines.json")
    existing_lines = load_json_file(lines_path) or []

    # Build map of existing lines by hexagram_id and position
    existing_map = {}
    for line in existing_lines:
        key = f"{line.get('hexagram_id')}-{line.get('position')}"
        existing_map[key] = line

    lines = []
    line_id_counter = 1

    for hex_id in range(1, 65):
        hex_name = hexagrams.get(hex_id, {}).get("name", f"卦{hex_id}")

        for pos in range(1, 7):
            key = f"{hex_id}-{pos}"

            if key in existing_map:
                lines.append(existing_map[key])
            else:
                # Generate line data (placeholder)
                line = _generate_single_line(line_id_counter, hex_id, pos, hex_name)
                lines.append(line)
                line_id_counter += 1

    # Add 用九 for hexagrams 1-30 (yang hexagrams)
    # Add 用六 for hexagrams 31-64 (yin hexagrams)
    # (Simplified - full implementation would add these)

    logger.info(f"Generated {len(lines)} lines")
    return lines


def _generate_single_line(
    line_id: int, hex_id: int, position: int, hex_name: str
) -> dict[str, Any]:
    """Generate a single line's data."""
    # Position to yao name mapping
    yao_names = {
        1: "初九",
        2: "九二",
        3: "九三",
        4: "九四",
        5: "九五",
        6: "上九",
    }
    yin_yao_names = {
        1: "初六",
        2: "六二",
        3: "六三",
        4: "六四",
        5: "六五",
        6: "上六",
    }

    # Simplified - determine yin/yang from hex_id
    is_yin = hex_id % 2 == 0
    yao_name = yin_yao_names[position] if is_yin else yao_names[position]

    return {
        "id": f"{hex_id}-{position}",
        "hexagram_id": hex_id,
        "position": position,
        "yao_name": yao_name,
        "text": f"{yao_name}的爻辞",
    }


def generate_scene_mapping() -> dict[str, dict[str, Any]]:
    """
    Generate scene mapping data.

    This is typically done manually, but we provide a basic structure.
    """
    logger.info("Generating scene mapping...")

    scene_path = os.path.join(DATA_DIR, "scene_mapping.json")
    existing_mapping = load_json_file(scene_path)

    if existing_mapping:
        logger.info(
            f"Found existing scene_mapping.json with {len(existing_mapping)} entries"
        )
        return existing_mapping

    # Basic scene mappings (can be expanded manually)
    scene_mapping = {
        "创业-早期-积累": {"hexagram_id": 3, "hexagram_name": "屯"},
        "创业-成长-突破": {"hexagram_id": 1, "hexagram_name": "乾"},
        "职场-晋升-积累": {"hexagram_id": 46, "hexagram_name": "升"},
        "投资-评估-谨慎": {"hexagram_id": 40, "hexagram_name": "解"},
        "人际-纠纷-谨慎": {"hexagram_id": 6, "hexagram_name": "讼"},
    }

    logger.info(f"Generated {len(scene_mapping)} scene mappings")
    return scene_mapping


# ===================== MAIN FUNCTIONS =====================


def run_validation(llm_config_path: str) -> None:
    """Run data validation."""
    if validate_all_data():
        logger.info("All validations passed!")
    else:
        logger.error("Validation failed!")
        sys.exit(1)


def run_stage_4() -> None:
    """Generate shi_ying.json (Stage 4)
    
    Requires: hexagrams.json with binary_code, palace fields
    """
    logger.info("Running Stage 4: Generate shi_ying.json")
    
    # Validate dependencies
    hexagrams = load_json_file(os.path.join(DATA_DIR, "hexagrams.json"))
    if not hexagrams:
        logger.error("hexagrams.json not found. Run Stage 1 first.")
        return
    for hex_id in range(1, 65):
        hex_data = hexagrams.get(str(hex_id), {})
        for field in ["binary_code", "palace"]:
            if field not in hex_data:
                logger.error(f"Cannot run Stage 4: hexagrams.json missing '{field}' field")
                return
    
    # Import and run generate_shi_ying
    spec = importlib.util.spec_from_file_location(
        "generate_shi_ying", 
        os.path.join(os.path.dirname(__file__), "generate_shi_ying.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    records = module.generate_shi_ying()
    
    output_path = os.path.join(DATA_DIR, "shi_ying.json")
    save_json_file(output_path, records)
    logger.info(f"✓ Generated {len(records)} records to shi_ying.json")


def run_stage_5() -> None:
    """Generate yao_attributes.json (Stage 5)
    
    Requires: hexagrams.json + shi_ying.json
    """
    logger.info("Running Stage 5: Generate yao_attributes.json")
    
    # Validate dependencies
    hexagrams = load_json_file(os.path.join(DATA_DIR, "hexagrams.json"))
    if not hexagrams:
        logger.error("hexagrams.json not found. Run Stage 1 first.")
        return
    for hex_id in range(1, 65):
        hex_data = hexagrams.get(str(hex_id), {})
        for field in ["binary_code", "lower_trigram", "upper_trigram"]:
            if field not in hex_data:
                logger.error(f"Cannot run Stage 5: hexagrams.json missing '{field}' field")
                return
    
    shi_ying_path = os.path.join(DATA_DIR, "shi_ying.json")
    if not os.path.exists(shi_ying_path):
        logger.error("Cannot run Stage 5: shi_ying.json not found. Run Stage 4 first.")
        return
    
    # Import and run generate_yao_attributes
    spec = importlib.util.spec_from_file_location(
        "generate_yao_attributes",
        os.path.join(os.path.dirname(__file__), "generate_yao_attributes.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    records = module.generate_all_yao_attributes()
    
    output_path = os.path.join(DATA_DIR, "yao_attributes.json")
    save_json_file(output_path, records)
    logger.info(f"✓ Generated {len(records)} records to yao_attributes.json")


def run_stage_6() -> None:
    """Generate hexagram_relations.json (Stage 6)
    
    Requires: hexagrams.json with binary_code field
    """
    logger.info("Running Stage 6: Generate hexagram_relations.json")
    
    # Validate dependencies
    hexagrams = load_json_file(os.path.join(DATA_DIR, "hexagrams.json"))
    if not hexagrams:
        logger.error("hexagrams.json not found. Run Stage 1 first.")
        return
    hex_data = hexagrams.get("1", {})
    if "binary_code" not in hex_data:
        logger.error("Cannot run Stage 6: hexagrams.json missing 'binary_code' field")
        return
    
    # Import and run hexagram_relations generation
    from core.hexagram_relations import get_cuo_gua, get_zong_gua, get_jiao_gua, get_hu_gua
    
    records = []
    for hex_id in range(1, 65):
        # 错卦
        target = get_cuo_gua(hex_id)
        records.append({"source_id": hex_id, "target_id": target, "relation_type": "错卦"})
        
        # 综卦
        target = get_zong_gua(hex_id)
        if target is not None:
            records.append({"source_id": hex_id, "target_id": target, "relation_type": "综卦"})
        
        # 交卦
        target = get_jiao_gua(hex_id)
        records.append({"source_id": hex_id, "target_id": target, "relation_type": "交卦"})
        
        # 互卦
        target = get_hu_gua(hex_id)
        records.append({"source_id": hex_id, "target_id": target, "relation_type": "互卦"})
    
    output_path = os.path.join(DATA_DIR, "hexagram_relations.json")
    save_json_file(output_path, records)
    logger.info(f"✓ Generated {len(records)} records to hexagram_relations.json")


def run_generation(stage: int, llm_config_path: str) -> None:
    """Run data generation."""
    # Load LLM config
    try:
        config = load_llm_config(llm_config_path)
        client = LLMClient(config)
    except FileNotFoundError:
        logger.warning(
            f"Config file {llm_config_path} not found, using placeholder data"
        )
        client = None
    except Exception as e:
        logger.warning(f"Failed to load LLM config: {e}, using placeholder data")
        client = None

    ensure_data_dir()

    # Stage 1: Generate hexagrams
    if stage in (1, 0):  # 0 = all
        hexagrams = generate_hexagram_data(client)
        save_json_file(os.path.join(DATA_DIR, "hexagrams.json"), hexagrams)
        logger.info(f"Saved {len(hexagrams)} hexagrams")

    # Stage 2: Generate lines (requires hexagrams)
    if stage in (2, 0):
        hexagrams = load_json_file(os.path.join(DATA_DIR, "hexagrams.json")) or {}
        hexagrams = {int(k): v for k, v in hexagrams.items()}
        lines = generate_line_data(client, hexagrams)
        save_json_file(os.path.join(DATA_DIR, "lines.json"), lines)
        logger.info(f"Saved {len(lines)} lines")

    # Stage 3: Generate scene mapping
    if stage in (3, 0):
        scene_mapping = generate_scene_mapping()
        save_json_file(os.path.join(DATA_DIR, "scene_mapping.json"), scene_mapping)
        logger.info(f"Saved {len(scene_mapping)} scene mappings")

    # Stage 4: Generate shi_ying
    if stage in (4, 0):
        run_stage_4()

    # Stage 5: Generate yao_attributes
    if stage in (5, 0):
        run_stage_5()

    # Stage 6: Generate hexagram_relations
    if stage in (6, 0):
        run_stage_6()

    logger.info("Data generation complete!")

    # Run validation after generation
    if validate_all_data():
        logger.info("Post-generation validation passed!")
    else:
        logger.warning("Post-generation validation had issues")


def main():
    parser = argparse.ArgumentParser(description="Generate or validate yice data files")
    parser.add_argument(
        "--stage",
        type=int,
        default=0,
        choices=[0, 1, 2, 3, 4, 5, 6],
        help="Generation stage: 0=all, 1=hexagrams, 2=lines, 3=scene_mapping, 4=shi_ying, 5=yao_attributes, 6=hexagram_relations",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate existing data, don't generate",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="models.json",
        help="Path to LLM config file (default: models.json)",
    )

    args = parser.parse_args()

    if args.validate:
        run_validation(args.config)
    else:
        run_generation(args.stage, args.config)


if __name__ == "__main__":
    main()
# ===================== STAGE 4-6 FUNCTIONS =====================


def validate_dependencies(required_fields: list[str], data_file: str) -> bool:
    """Validate that required fields exist in hexagrams.json"""
    hexagrams_path = os.path.join(DATA_DIR, "hexagrams.json")
    hexagrams = load_json_file(hexagrams_path)
    
    if not hexagrams:
        logger.error(f"hexagrams.json not found")
        return False
    
    errors = []
    for hex_id in range(1, 65):
        hex_data = hexagrams.get(str(hex_id), {})
        for field in required_fields:
            if field not in hex_data:
                errors.append(f"Hexagram {hex_id} missing field: {field}")
    
    if errors:
        logger.error(f"Dependency validation failed: {errors[:5]}...")
        return False
    
    logger.info(f"✓ Dependencies validated: {data_file}")
    return True



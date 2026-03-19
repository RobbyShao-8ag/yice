"""Tests for DataLoader with edge case coverage."""

import json
import os
import tempfile

import pytest

from core.data_loader import DataLoader, DataLoaderConfig
from core.errors import DataError


class TestDataLoaderConfig:
    """Tests for DataLoaderConfig."""

    def test_config_defaults(self):
        """Test DataLoaderConfig default values."""
        config = DataLoaderConfig()
        assert config.data_dir == "data"
        assert config.hexagrams_path is None
        assert config.lines_path is None
        assert config.yao_attrs_path is None
        assert config.scene_mapping_path is None
        assert config.validate is False

    def test_config_custom(self):
        """Test DataLoaderConfig with custom values."""
        config = DataLoaderConfig(
            data_dir="/custom/data",
            hexagrams_path="/path/hexagrams.json",
            lines_path="/path/lines.json",
            yao_attrs_path="/path/yao.json",
            scene_mapping_path="/path/scene.json",
        )
        assert config.data_dir == "/custom/data"
        assert config.hexagrams_path == "/path/hexagrams.json"


class TestDataLoaderMissingFiles:
    """Tests for handling missing files."""

    def test_missing_hexagrams_file(self):
        """Test loading when hexagrams.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert loader.hexagrams == {}

    def test_missing_lines_file(self):
        """Test loading when lines.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert loader.lines == []

    def test_missing_yao_attributes_file(self):
        """Test loading when yao_attributes.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert loader.yao_attributes == {}

    def test_missing_scene_mapping_file(self):
        """Test loading when scene_mapping.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert loader.scene_mapping == {}

    def test_no_path_specified(self):
        """Test DataLoader handles empty data_dir gracefully."""
        config = DataLoaderConfig(data_dir="")
        loader = DataLoader(config)
        assert loader.hexagrams == {}
        assert loader.lines == []


class TestDataLoaderCorruptedJSON:
    """Tests for handling corrupted JSON files."""

    def test_invalid_json_syntax(self):
        """Test loading file with invalid JSON syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                f.write("{invalid json syntax")

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="Invalid JSON"):
                DataLoader(config)

    def test_empty_json_file(self):
        """Test loading empty JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                f.write("")

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="Invalid JSON"):
                DataLoader(config)

    def test_wrong_json_structure_hexagrams(self):
        """Test loading hexagrams.json with wrong structure (list instead of dict)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump([{"id": 1}], f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="must be a dictionary"):
                DataLoader(config)

    def test_wrong_json_structure_lines(self):
        """Test loading lines.json with wrong structure (dict instead of list)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lines_path = os.path.join(tmpdir, "lines.json")
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump({"1": {"id": 1}}, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="must be a list"):
                DataLoader(config)

    def test_missing_required_field(self):
        """Test loading hexagram with missing required field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    # Missing: gua_ci, image, judgement
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="missing required field"):
                DataLoader(config)


class TestDataLoaderDuplicateIDs:
    """Tests for handling duplicate IDs."""

    def test_duplicate_hexagram_ids(self):
        """Test loading hexagrams - Python json keeps last value for duplicate keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            # Python json.load keeps only last value for duplicate keys
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert len(loader.hexagrams) == 1

    def test_duplicate_line_ids(self):
        """Test loading lines with duplicate IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": 1,
                    "hexagram_id": 1,
                    "position": 1,
                    "yao_name": "初九",
                    "text": "test",
                },
                {
                    "id": 1,
                    "hexagram_id": 1,
                    "position": 2,
                    "yao_name": "九二",
                    "text": "test2",
                },
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="Duplicate line ID"):
                DataLoader(config)


class TestDataLoaderUnsortedLines:
    """Tests for handling unsorted lines."""

    def test_unsorted_lines_get_sorted(self):
        """Test that unsorted lines are sorted by hexagram_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                },
                "2": {
                    "id": 2,
                    "name": "坤为地",
                    "gua_ci": "元亨",
                    "image": "地势坤",
                    "judgement": "吉",
                },
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": 2,
                    "hexagram_id": 2,
                    "position": 1,
                    "yao_name": "初六",
                    "text": "test",
                },
                {
                    "id": 1,
                    "hexagram_id": 1,
                    "position": 1,
                    "yao_name": "初九",
                    "text": "test",
                },
                {
                    "id": 3,
                    "hexagram_id": 1,
                    "position": 2,
                    "yao_name": "九二",
                    "text": "test",
                },
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            lines = loader.lines
            assert len(lines) == 3
            assert lines[0]["hexagram_id"] == 1
            assert lines[1]["hexagram_id"] == 1
            assert lines[2]["hexagram_id"] == 2


class TestDataLoaderInvalidReferences:
    """Tests for handling invalid references."""

    def test_line_references_nonexistent_hexagram(self):
        """Test lines referencing non-existent hexagram_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": 1,
                    "hexagram_id": 999,
                    "position": 1,
                    "yao_name": "初九",
                    "text": "test",
                }
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert len(loader.lines) == 1

    def test_scene_mapping_references_invalid_hexagram(self):
        """Test scene_mapping referencing non-existent hexagram."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            scene_path = os.path.join(tmpdir, "scene_mapping.json")
            scene_data = {
                "创业": {
                    "hexagram_id": 999,
                    "hexagram_name": "不存在",
                    "keywords": ["创业"],
                }
            }
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert "创业" in loader.scene_mapping


class TestDataLoaderValidData:
    """Tests for valid data loading."""

    def test_valid_hexagrams_loading(self):
        """Test loading valid hexagrams data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                },
                "2": {
                    "id": 2,
                    "name": "坤为地",
                    "gua_ci": "元亨",
                    "image": "地势坤",
                    "judgement": "吉",
                },
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            assert len(loader.hexagrams) == 2
            assert 1 in loader.hexagrams
            assert 2 in loader.hexagrams
            assert loader.hexagrams[1]["name"] == "乾为天"

    def test_valid_lines_loading(self):
        """Test loading valid lines data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": 1,
                    "hexagram_id": 1,
                    "position": 1,
                    "yao_name": "初九",
                    "text": "test",
                }
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            assert len(loader.lines) == 1
            assert loader.lines[0]["yao_name"] == "初九"

    def test_valid_yao_attributes_loading(self):
        """Test loading valid yao_attributes data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yao_path = os.path.join(tmpdir, "yao_attributes.json")
            yao_data = {
                "1": {
                    "position": 1,
                    "na_jia_gan": "甲",
                    "na_jia_zhi": "子",
                    "wuxing": "水",
                    "liu_qin": "子孙",
                    "is_shi": False,
                    "is_ying": False,
                    "is_fei": False,
                    "is_fu": False,
                },
                "2": {
                    "position": 2,
                    "na_jia_gan": "甲",
                    "na_jia_zhi": "寅",
                    "wuxing": "木",
                    "liu_qin": "妻财",
                    "is_shi": False,
                    "is_ying": False,
                    "is_fei": False,
                    "is_fu": False,
                },
            }
            with open(yao_path, "w", encoding="utf-8") as f:
                json.dump(yao_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            assert len(loader.yao_attributes) == 2
            assert 1 in loader.yao_attributes
            assert loader.yao_attributes[1]["wuxing"] == "水"

    def test_valid_scene_mapping_loading(self):
        """Test loading valid scene_mapping data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                },
                "5": {
                    "id": 5,
                    "name": "需卦",
                    "gua_ci": "有孚",
                    "image": "云上于天",
                    "judgement": "吉",
                },
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            scene_path = os.path.join(tmpdir, "scene_mapping.json")
            scene_data = {
                "创业": {
                    "hexagram_id": 5,
                    "hexagram_name": "需卦",
                    "keywords": ["创业", "起步"],
                }
            }
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            assert "创业" in loader.scene_mapping
            assert loader.scene_mapping["创业"]["hexagram_id"] == 5


class TestDataLoaderGetters:
    """Tests for getter methods."""

    def test_get_hexagram(self):
        """Test get_hexagram method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            hex = loader.get_hexagram(1)
            assert hex is not None
            assert hex["name"] == "乾为天"

            missing = loader.get_hexagram(999)
            assert missing is None

    def test_get_lines_for_hexagram(self):
        """Test get_lines_for_hexagram method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": 1,
                    "hexagram_id": 1,
                    "position": 1,
                    "yao_name": "初九",
                    "text": "test",
                },
                {
                    "id": 2,
                    "hexagram_id": 1,
                    "position": 2,
                    "yao_name": "九二",
                    "text": "test",
                },
                {
                    "id": 3,
                    "hexagram_id": 2,
                    "position": 1,
                    "yao_name": "初六",
                    "text": "test",
                },
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            hex1_lines = loader.get_lines_for_hexagram(1)
            assert len(hex1_lines) == 2

            hex2_lines = loader.get_lines_for_hexagram(2)
            assert len(hex2_lines) == 1

            missing = loader.get_lines_for_hexagram(999)
            assert len(missing) == 0

    def test_get_yao_attribute(self):
        """Test get_yao_attribute method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yao_path = os.path.join(tmpdir, "yao_attributes.json")
            yao_data = {
                "1": {
                    "position": 1,
                    "na_jia_gan": "甲",
                    "na_jia_zhi": "子",
                    "wuxing": "水",
                    "liu_qin": "子孙",
                    "is_shi": False,
                    "is_ying": False,
                    "is_fei": False,
                    "is_fu": False,
                }
            }
            with open(yao_path, "w", encoding="utf-8") as f:
                json.dump(yao_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            attr = loader.get_yao_attribute(1)
            assert attr is not None
            assert attr["wuxing"] == "水"

            missing = loader.get_yao_attribute(999)
            assert missing is None

    def test_get_scene(self):
        """Test get_scene method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "5": {
                    "id": 5,
                    "name": "需卦",
                    "gua_ci": "有孚",
                    "image": "云上于天",
                    "judgement": "吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            scene_path = os.path.join(tmpdir, "scene_mapping.json")
            scene_data = {
                "创业": {
                    "hexagram_id": 5,
                    "hexagram_name": "需卦",
                    "keywords": ["创业"],
                }
            }
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            scene = loader.get_scene("创业")
            assert scene is not None
            assert scene["hexagram_id"] == 5

            missing = loader.get_scene("不存在")
            assert missing is None


class TestDataLoaderReload:
    """Tests for reload functionality."""

    def test_reload(self):
        """Test reload method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)
            assert len(loader.hexagrams) == 1

            hexagram_data["2"] = {
                "id": 2,
                "name": "坤为地",
                "gua_ci": "元亨",
                "image": "地势坤",
                "judgement": "吉",
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            loader.reload()
            assert len(loader.hexagrams) == 2


class TestDataLoaderCustomPaths:
    """Tests for custom path loading."""

    def test_custom_hexagrams_path(self):
        """Test loading with custom hexagrams_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "my_hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(hexagrams_path=custom_path)
            loader = DataLoader(config)

            assert len(loader.hexagrams) == 1
            assert loader.hexagrams[1]["name"] == "乾为天"

    def test_custom_lines_path(self):
        """Test loading with custom lines_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = os.path.join(tmpdir, "hexagrams.json")
            hex_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hex_path, "w", encoding="utf-8") as f:
                json.dump(hex_data, f)

            custom_path = os.path.join(tmpdir, "my_lines.json")
            lines_data = [
                {
                    "id": 1,
                    "hexagram_id": 1,
                    "position": 1,
                    "yao_name": "初九",
                    "text": "test",
                }
            ]
            with open(custom_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(lines_path=custom_path)
            loader = DataLoader(config)

            assert len(loader.lines) == 1


class TestDataLoaderFileErrors:
    """Tests for file reading errors."""

    def test_file_read_permission_error(self):
        """Test handling of file read permission errors."""
        if os.name == "nt":
            pytest.skip("Permission test not reliable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            os.chmod(hexagrams_path, 0o000)

            config = DataLoaderConfig(data_dir=tmpdir)
            try:
                with pytest.raises(DataError, match="Failed to load"):
                    DataLoader(config)
            finally:
                os.chmod(hexagrams_path, 0o644)


class TestDataLoaderEdgeCases:
    """Tests for edge cases."""

    def test_hexagram_id_string_key(self):
        """Test hexagram with string ID key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                },
                "2": {
                    "id": 2,
                    "name": "坤为地",
                    "gua_ci": "元亨",
                    "image": "地势坤",
                    "judgement": "吉",
                },
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            loader = DataLoader(config)

            assert 1 in loader.hexagrams
            assert 2 in loader.hexagrams

    def test_line_missing_required_field(self):
        """Test lines with missing required field raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hex_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hex_data, f)

            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": 1,
                    "hexagram_id": 1,
                    # Missing: position, yao_name, text
                }
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="missing required field"):
                DataLoader(config)

    def test_yao_attribute_missing_required_field(self):
        """Test yao_attributes with missing required field raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yao_path = os.path.join(tmpdir, "yao_attributes.json")
            yao_data = {"1": {"position": 1}}
            with open(yao_path, "w", encoding="utf-8") as f:
                json.dump(yao_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="missing required field"):
                DataLoader(config)

    def test_scene_mapping_missing_required_field(self):
        """Test scene_mapping with missing required field raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hex_data = {
                "1": {
                    "id": 1,
                    "name": "乾为天",
                    "gua_ci": "元亨利贞",
                    "image": "天行健",
                    "judgement": "大吉",
                }
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hex_data, f)

            scene_path = os.path.join(tmpdir, "scene_mapping.json")
            scene_data = {
                "创业": {
                    "keywords": ["创业"]
                    # Missing: hexagram_id, hexagram_name
                }
            }
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f)

            config = DataLoaderConfig(data_dir=tmpdir)
            with pytest.raises(DataError, match="missing required field"):
                DataLoader(config)


class TestDataLoaderValidation:
    """Tests for data completeness validation."""

    def test_incomplete_hexagrams_count(self):
        """Test validation fails when hexagrams count != 64."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                str(i): {
                    "id": i,
                    "name": f"卦{i}",
                    "gua_ci": "test",
                    "image": "test",
                    "judgement": "test",
                }
                for i in range(1, 11)  # Only 10 hexagrams
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir, validate=True)
            with pytest.raises(DataError, match="expected 64 records"):
                DataLoader(config)

    def test_missing_hexagram_ids(self):
        """Test validation fails when hexagram IDs are not continuous 1-64."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            # Create 64 hexagrams but with some IDs outside 1-64 range
            hexagram_data = {}
            # First 49 with correct IDs
            for i in range(1, 50):
                hexagram_data[str(i)] = {
                    "id": i,
                    "name": f"卦{i}",
                    "gua_ci": "test",
                    "image": "test",
                    "judgement": "test",
                }
            # Add 15 more with IDs > 64 (these are invalid)
            for i in range(50, 65):
                hexagram_data[str(100 + i)] = {
                    "id": 100 + i,
                    "name": f"卦{100 + i}",
                    "gua_ci": "test",
                    "image": "test",
                    "judgement": "test",
                }
            # Total 64 hexagrams but missing 1-64
            assert len(hexagram_data) == 64

            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            config = DataLoaderConfig(data_dir=tmpdir, validate=True)
            with pytest.raises(DataError, match="missing hexagram IDs"):
                DataLoader(config)

    def test_incomplete_lines_count(self):
        """Test validation fails when lines count != 386."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create full hexagrams
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                str(i): {
                    "id": i,
                    "name": f"卦{i}",
                    "gua_ci": "test",
                    "image": "test",
                    "judgement": "test",
                }
                for i in range(1, 65)
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            # Only 10 lines
            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = [
                {
                    "id": i,
                    "hexagram_id": 1,
                    "position": i,
                    "yao_name": f"爻{i}",
                    "text": "test",
                }
                for i in range(1, 11)
            ]
            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir, validate=True)
            with pytest.raises(DataError, match="expected 386 records"):
                DataLoader(config)

    def test_lines_invalid_hexagram_reference(self):
        """Test validation fails when lines reference invalid hexagram_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create full 64 hexagrams
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                str(i): {
                    "id": i,
                    "name": f"卦{i}",
                    "gua_ci": "test",
                    "image": "test",
                    "judgement": "test",
                }
                for i in range(1, 65)
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            # Create 386 lines (64*6=384 + 2用爻) with one invalid reference
            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = []
            line_id = 1
            for hex_id in range(1, 65):
                for pos in range(1, 7):
                    # Add invalid reference at first line of hex 1
                    if hex_id == 1 and pos == 1:
                        lines_data.append(
                            {
                                "id": line_id,
                                "hexagram_id": 999,  # Invalid
                                "position": pos,
                                "yao_name": f"爻{pos}",
                                "text": "test",
                            }
                        )
                    else:
                        lines_data.append(
                            {
                                "id": line_id,
                                "hexagram_id": hex_id,
                                "position": pos,
                                "yao_name": f"爻{pos}",
                                "text": "test",
                            }
                        )
                    line_id += 1
            # Add 用九 and 用六
            lines_data.append(
                {
                    "id": 385,
                    "hexagram_id": 1,
                    "position": 7,
                    "yao_name": "用九",
                    "text": "test",
                }
            )
            lines_data.append(
                {
                    "id": 386,
                    "hexagram_id": 2,
                    "position": 7,
                    "yao_name": "用六",
                    "text": "test",
                }
            )

            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            config = DataLoaderConfig(data_dir=tmpdir, validate=True)
            with pytest.raises(DataError, match="invalid hexagram_id"):
                DataLoader(config)

    def test_insufficient_scene_mapping(self):
        """Test validation fails when scene_mapping has fewer than 50 scenes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                str(i): {
                    "id": i,
                    "name": f"卦{i}",
                    "gua_ci": "test",
                    "image": "test",
                    "judgement": "test",
                }
                for i in range(1, 65)
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            scene_path = os.path.join(tmpdir, "scene_mapping.json")
            scene_data = {
                f"场景{i}": {
                    "hexagram_id": 1,
                    "hexagram_name": "测试",
                    "keywords": [f"关键词{i}"],
                }
                for i in range(10)  # Only 10 scenes
            }
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f)

            config = DataLoaderConfig(data_dir=tmpdir, validate=True)
            with pytest.raises(DataError, match="expected at least 50 scenes"):
                DataLoader(config)

    def test_validation_passes_with_complete_data(self):
        """Test validation passes with complete valid data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 64 hexagrams
            hexagrams_path = os.path.join(tmpdir, "hexagrams.json")
            hexagram_data = {
                str(i): {
                    "id": i,
                    "name": f"卦{i}",
                    "gua_ci": "卦辞",
                    "image": "卦象",
                    "judgement": "吉",
                }
                for i in range(1, 65)
            }
            with open(hexagrams_path, "w", encoding="utf-8") as f:
                json.dump(hexagram_data, f)

            # Create 386 lines (64 * 6 = 384 + 2 用爻)
            lines_path = os.path.join(tmpdir, "lines.json")
            lines_data = []
            line_id = 1
            for hex_id in range(1, 65):
                for pos in range(1, 7):
                    lines_data.append(
                        {
                            "id": line_id,
                            "hexagram_id": hex_id,
                            "position": pos,
                            "yao_name": f"爻{pos}",
                            "text": "爻辞",
                        }
                    )
                    line_id += 1
            # Add 用九 and 用六 (lines 385 and 386)
            lines_data.append(
                {
                    "id": 385,
                    "hexagram_id": 1,
                    "position": 7,
                    "yao_name": "用九",
                    "text": "用九",
                }
            )
            lines_data.append(
                {
                    "id": 386,
                    "hexagram_id": 2,
                    "position": 7,
                    "yao_name": "用六",
                    "text": "用六",
                }
            )

            with open(lines_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f)

            # Create 50+ scenes
            scene_path = os.path.join(tmpdir, "scene_mapping.json")
            scene_data = {
                f"场景{i}": {
                    "hexagram_id": (i % 64) + 1,
                    "hexagram_name": f"卦{(i % 64) + 1}",
                    "keywords": [f"关键词{i}"],
                }
                for i in range(60)
            }
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene_data, f)

            config = DataLoaderConfig(data_dir=tmpdir, validate=True)
            loader = DataLoader(config)
            assert len(loader.hexagrams) == 64
            assert len(loader.lines) == 386
            assert len(loader.scene_mapping) == 60

"""Tests for image media-type detection and upload-url content_type validation."""
import pytest

from tools.classify_disease import _detect_media_type, _SUPPORTED_MEDIA_TYPES, _EXT_TO_MEDIA_TYPE
from app import _ALLOWED_IMAGE_TYPES


class TestDetectMediaType:
    def test_valid_content_type_jpeg(self):
        assert _detect_media_type("uploads/abc/img.jpg", "image/jpeg") == "image/jpeg"

    def test_valid_content_type_png(self):
        assert _detect_media_type("uploads/abc/img.png", "image/png") == "image/png"

    def test_valid_content_type_webp(self):
        assert _detect_media_type("uploads/abc/img.webp", "image/webp") == "image/webp"

    def test_valid_content_type_gif(self):
        assert _detect_media_type("uploads/abc/img.gif", "image/gif") == "image/gif"

    def test_empty_content_type_falls_back_to_extension_png(self):
        assert _detect_media_type("uploads/abc/img.png", "") == "image/png"

    def test_empty_content_type_falls_back_to_extension_webp(self):
        assert _detect_media_type("uploads/abc/img.webp", "") == "image/webp"

    def test_missing_extension_and_empty_content_type_returns_jpeg(self):
        assert _detect_media_type("uploads/abc/uuid-no-ext", "") == "image/jpeg"

    def test_unrecognised_content_type_uses_extension(self):
        assert _detect_media_type("uploads/abc/img.png", "application/octet-stream") == "image/png"

    def test_unrecognised_content_type_and_extension_returns_jpeg(self):
        assert _detect_media_type("uploads/abc/img.bmp", "image/bmp") == "image/jpeg"

    def test_jpg_and_jpeg_extensions_both_map_to_jpeg(self):
        assert _detect_media_type("img.jpg", "") == "image/jpeg"
        assert _detect_media_type("img.jpeg", "") == "image/jpeg"

    def test_extension_case_insensitive(self):
        assert _detect_media_type("uploads/abc/img.PNG", "") == "image/png"


class TestSupportedMediaTypesDerivedFromExtMap:
    def test_supported_types_matches_ext_map_values(self):
        assert _SUPPORTED_MEDIA_TYPES == set(_EXT_TO_MEDIA_TYPE.values())


class TestAllowedImageTypesConsistency:
    def test_allowed_image_types_keys_match_supported_media_types(self):
        """app.py and classify_disease.py must agree on the supported type set."""
        assert set(_ALLOWED_IMAGE_TYPES.keys()) == _SUPPORTED_MEDIA_TYPES

    def test_allowed_image_types_extensions_start_with_dot(self):
        for ext in _ALLOWED_IMAGE_TYPES.values():
            assert ext.startswith(".")

    def test_jpeg_maps_to_jpg_extension(self):
        assert _ALLOWED_IMAGE_TYPES["image/jpeg"] == ".jpg"

    def test_png_maps_to_png_extension(self):
        assert _ALLOWED_IMAGE_TYPES["image/png"] == ".png"

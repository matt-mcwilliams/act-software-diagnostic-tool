import pytest
from fastapi import HTTPException

from app.content import _read_export
from app.content_import import _validate_references


@pytest.mark.parametrize("subject", ["english", "math"])
def test_canonical_exports_have_importable_references(subject: str) -> None:
    data, source_sha256 = _read_export(subject)  # type: ignore[arg-type]

    _validate_references(data)

    assert len(source_sha256) == 64


def test_import_validation_rejects_unknown_skill() -> None:
    data, _ = _read_export("math")
    data["questions"][0]["skillIds"] = ["MATH-NOT-A-REAL-SKILL"]

    with pytest.raises(HTTPException) as error:
        _validate_references(data)

    assert error.value.status_code == 503

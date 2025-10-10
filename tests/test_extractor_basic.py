from app.extractor import _clean_dni, _normalize_result


def test_clean_dni():
    assert _clean_dni('12345678A') == '12345678A'
    assert _clean_dni('12.345.678-A') == '12345678A'
    assert _clean_dni(' 12345 678 A ') == '12345678A'


def test_normalize_result():
    assert _normalize_result('Apto') is True
    assert _normalize_result('No apto') is False
    assert _normalize_result('gai') is True
    assert _normalize_result('ez gai') is False
    assert _normalize_result('unknown') is None
from app.extractor import _clean_dni, _normalize_result


def test_clean_dni():
    assert _clean_dni('12345678A') == '12345678A'
    assert _clean_dni('12.345.678-A') == '12345678A'
    assert _clean_dni(' 12345 678 A ') == '12345678A'


def test_normalize_result():
    assert _normalize_result('Apto') is True
    assert _normalize_result('No apto') is False
    assert _normalize_result('gai') is True
    assert _normalize_result('ez gai') is False
    assert _normalize_result('unknown') is None

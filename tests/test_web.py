from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from carbon_preaudit.calc.inputs import parse_inputs
from carbon_preaudit.calc.run import calculate
from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues
from carbon_preaudit.preaudit.extractor import ExtractionError, Extractor, FakeExtractor
from carbon_preaudit.web.app import MAX_PDD_CHARS, MAX_UPLOAD_BYTES, app, get_extractor
from tests.helpers import CSV_HEADER, ONE_TREE_CSV, SQUARE_001, polygon_text

EXAMPLES = Path(__file__).parent.parent / "examples"
GEOJSON = (EXAMPLES / "project.geojson").read_text(encoding="utf-8")
CSV = (EXAMPLES / "plots.csv").read_text(encoding="utf-8")
PDD = (EXAMPLES / "pdd-section.md").read_text(encoding="utf-8")

AREA_QUOTE = "The project area covers 100.0 ha, delineated by the polygon provided in Annex A."
METHOD_QUOTE = (
    "The activity follows the methodology VM0047 (Afforestation, Reforestation and Revegetation)"
    " under the Verra VCS programme."
)
GROSS_QUOTE = "The gross removals of the project amount to 8,364 tCO2e over the crediting period."
BUFFER_QUOTE = (
    "A share of 20 % of the gross removals is withheld in the buffer pool to cover the risk"
    " of reversal."
)
# The quote spans a line break in the example text.
NET_QUOTE = (
    "After the buffer deduction, the net removals available for issuance amount to 6,691 tCO2e."
)


def _claimed(gross: float = 8364.0, gross_quote: str = GROSS_QUOTE) -> ClaimedValues:
    return ClaimedValues(
        project_area_ha=ClaimedValue[float](value=100.0, quote=AREA_QUOTE),
        tco2e_gross=ClaimedValue[float](value=gross, quote=gross_quote),
        tco2e_net=ClaimedValue[float](value=6691.0, quote=NET_QUOTE),
        buffer_pct=ClaimedValue[float](value=20.0, quote=BUFFER_QUOTE),
        methodology=ClaimedValue[str](value="VM0047", quote=METHOD_QUOTE),
    )


class _FailingExtractor:
    def extract(self, text: str) -> ClaimedValues:
        raise ExtractionError("Modell nicht erreichbar")


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def _use(extractor: Extractor) -> None:
    app.dependency_overrides[get_extractor] = lambda: extractor


def _form(**overrides: str) -> dict[str, str]:
    data = {"geojson_text": GEOJSON, "csv_text": CSV, "pdd_text": PDD, "buffer_pct": "20"}
    data.update(overrides)
    return data


def test_index_renders_form(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'hx-post="/check"' in response.text
    assert 'hx-encoding="multipart/form-data"' in response.text
    assert 'name="geojson_file"' in response.text
    assert 'name="buffer_pct" value="20.0"' in response.text
    assert "Beispiel laden" in response.text


def test_example_prefills_the_form(client: TestClient) -> None:
    response = client.get("/example")
    assert response.status_code == 200
    assert "The project area covers 100.0 ha" in response.text
    assert "P01,400,P01-T01" in response.text


def test_static_css_is_served(client: TestClient) -> None:
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_check_with_example_files_shows_tc_finding_and_marks(client: TestClient) -> None:
    # Gross claimed as tC: 8363.7 tCO2e * 12/44 = 2281.0 tC, written as 2,281.
    pdd = PDD.replace("8,364 tCO2e", "2,281 tCO2e")
    quote = GROSS_QUOTE.replace("8,364", "2,281")
    _use(FakeExtractor(_claimed(gross=2281.0, gross_quote=quote)))
    response = client.post(
        "/check",
        data={"pdd_text": pdd, "buffer_pct": "20"},
        files={
            "geojson_file": ("project.geojson", GEOJSON.encode(), "application/geo+json"),
            "csv_file": ("plots.csv", CSV.encode(), "text/csv"),
        },
    )
    assert response.status_code == 200
    html = response.text
    assert "badge-critical" in html
    assert "kritisch" in html
    assert "Vermutlich tC statt tCO₂e" in html
    assert '<mark class="hl hl-critical" title="Brutto-Menge (tCO₂e)">' + quote in html
    # Quote over a line break is marked as verified, the other fields are verified too.
    assert 'hl-ok" title="Netto-Menge (tCO₂e)">After the buffer\ndeduction' in html
    assert html.count("<mark") == 5
    assert "Keine Abweichungen gefunden" not in html
    # Key figures in German format, short hash with the full hash in the title.
    assert "100,02" in html
    assert "8.363,7" in html
    assert 'id="polygon-data"' in html
    run_hash = calculate(parse_inputs(GEOJSON, CSV, 20.0)).run_hash
    assert f'title="{run_hash}">{run_hash[:12]}<' in html


def test_check_without_findings(client: TestClient) -> None:
    _use(FakeExtractor(_claimed().model_copy(update={"extracted_by": "fake-model-1"})))
    response = client.post("/check", data=_form())
    assert response.status_code == 200
    assert "Keine Abweichungen gefunden" in response.text
    assert "badge-" not in response.text
    assert "hl-ok" in response.text
    assert "Extrahiert von: fake-model-1" in response.text


def test_check_escapes_pdd_text(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post("/check", data=_form(pdd_text="<script>alert(1)</script> text"))
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_broken_geojson_gives_422_with_message(client: TestClient) -> None:
    _use(FakeExtractor(_claimed()))
    response = client.post("/check", data=_form(geojson_text="{not json"))
    assert response.status_code == 422
    assert "Eingabe fehlerhaft" in response.text
    assert "Das GeoJSON ist ungültig." in response.text
    assert "Traceback" not in response.text


def test_missing_csv_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(_claimed()))
    response = client.post("/check", data=_form(csv_text=""))
    assert response.status_code == 422
    assert "CSV fehlt" in response.text


def test_error_from_the_calculation_gives_422(client: TestClient) -> None:
    # Valid for the parser, rejected by calculate(): the hole is larger than the outer ring.
    hole = [[-0.01, -0.01], [0.02, -0.01], [0.02, 0.02], [-0.01, 0.02], [-0.01, -0.01]]
    _use(FakeExtractor(ClaimedValues()))
    response = client.post(
        "/check", data=_form(geojson_text=polygon_text(SQUARE_001, hole), csv_text=ONE_TREE_CSV)
    )
    assert response.status_code == 422
    assert "Die Geometrie des Polygons ist ungültig." in response.text


def test_csv_without_required_column_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(_claimed()))
    response = client.post("/check", data=_form(csv_text=CSV_HEADER.replace("dbh_cm", "x") + "a\n"))
    assert response.status_code == 422
    assert "Eingabe fehlerhaft" in response.text


def test_invalid_buffer_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(_claimed()))
    for bad in ("abc", "150", "nan"):
        response = client.post("/check", data=_form(buffer_pct=bad))
        assert response.status_code == 422, bad


def test_buffer_with_decimal_comma_is_accepted(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post("/check", data=_form(buffer_pct="12,5"))
    assert response.status_code == 200
    assert "12,5 %" in response.text


def test_extraction_error_still_shows_key_figures(client: TestClient) -> None:
    _use(_FailingExtractor())
    response = client.post("/check", data=_form())
    assert response.status_code == 200
    assert "Extraktion fehlgeschlagen: Modell nicht erreichbar" in response.text
    assert "100,02" in response.text
    assert "Keine Abweichungen gefunden" not in response.text
    assert "Traceback" not in response.text


def test_missing_api_key_is_shown_as_extraction_notice(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Default dependency, no override: the key is missing, which must not become a 500.
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CARBON_PREAUDIT_PROVIDER", "gemini")
    response = client.post("/check", data=_form())
    assert response.status_code == 200
    assert "Extraktion fehlgeschlagen:" in response.text


def test_uploaded_file_wins_over_pasted_text(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post(
        "/check",
        data=_form(csv_text="garbage"),
        files={"csv_file": ("plots.csv", CSV.encode(), "text/csv")},
    )
    assert response.status_code == 200
    assert "100,02" in response.text


def test_non_utf8_file_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post(
        "/check",
        data=_form(),
        files={"csv_file": ("plots.csv", "Fläche".encode("latin-1"), "text/csv")},
    )
    assert response.status_code == 422
    assert "nicht UTF-8-kodiert" in response.text


def test_user_values_in_error_message_are_escaped(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post("/check", data=_form(buffer_pct="<script>1</script>"))
    assert response.status_code == 422
    assert "<script>1</script>" not in response.text
    assert "&lt;script&gt;1&lt;/script&gt;" in response.text


def test_oversized_file_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post(
        "/check",
        data=_form(),
        files={"csv_file": ("plots.csv", b"x" * (MAX_UPLOAD_BYTES + 1), "text/csv")},
    )
    assert response.status_code == 422
    assert "größer als" in response.text


def test_csv_field_above_csv_module_limit_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    header = CSV.splitlines()[0]
    oversized = f"{header}\nP1,400,{'x' * 140_000},20,15,0.6\n".encode()
    response = client.post(
        "/check",
        data=_form(),
        files={"csv_file": ("plots.csv", oversized, "text/csv")},
    )
    assert response.status_code == 422
    assert "CSV could not be read" in response.text


def test_file_at_the_limit_is_read(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    csv_bytes = CSV.encode()
    padded = csv_bytes + b"\n" * (MAX_UPLOAD_BYTES - len(csv_bytes))  # trailing blank lines
    response = client.post(
        "/check",
        data=_form(),
        files={"csv_file": ("plots.csv", padded, "text/csv")},
    )
    assert response.status_code == 200


def test_oversized_pasted_text_gives_422(client: TestClient) -> None:
    _use(FakeExtractor(ClaimedValues()))
    response = client.post("/check", data=_form(csv_text="x" * (MAX_UPLOAD_BYTES + 1)))
    assert response.status_code == 422
    assert "größer als" in response.text


def test_too_long_pdd_text_gives_422_before_extraction(client: TestClient) -> None:
    _use(_FailingExtractor())  # would show an extraction notice with 200 if it were reached
    response = client.post("/check", data=_form(pdd_text="a" * (MAX_PDD_CHARS + 1)))
    assert response.status_code == 422
    assert "PDD-Text" in response.text


def test_form_part_over_starlette_limit_gives_readable_422(client: TestClient) -> None:
    # Starlette rejects text parts over 1 MiB with HTTPException 400 before the endpoint runs.
    _use(FakeExtractor(ClaimedValues()))
    response = client.post("/check", data=_form(pdd_text="a" * (2 * 1024 * 1024)))
    assert response.status_code == 422
    assert "Eingabe zu groß" in response.text
    assert "text/html" in response.headers["content-type"]


def test_other_http_errors_keep_the_default_response(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_findings_list_shows_field_label(client: TestClient) -> None:
    _use(FakeExtractor(_claimed(gross=1.0, gross_quote=GROSS_QUOTE.replace("8,364", "1"))))
    response = client.post("/check", data=_form(pdd_text=PDD.replace("8,364", "1")))
    assert response.status_code == 200
    assert "tco2e_gross" not in response.text
    assert '<span class="finding-field">Brutto-Menge (tCO₂e)</span>' in response.text

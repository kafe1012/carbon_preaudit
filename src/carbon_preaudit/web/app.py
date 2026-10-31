"""FastAPI application: input form, check endpoint and result rendering."""

import math
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from carbon_preaudit.calc.inputs import (
    DuplicateTreeError,
    EmptyPlotsError,
    InconsistentPlotAreaError,
    InputError,
    InvalidGeoJSONError,
    InvalidGeometryError,
    InvalidValueError,
    MissingColumnError,
    OpenRingError,
    UnsupportedGeometryError,
    parse_inputs,
)
from carbon_preaudit.calc.params import DEFAULT_BUFFER_PCT
from carbon_preaudit.calc.run import calculate
from carbon_preaudit.domain.models import ClaimedValues
from carbon_preaudit.preaudit.compare import LABELS, compare, format_de
from carbon_preaudit.preaudit.extractor import ExtractionError, Extractor, make_extractor
from carbon_preaudit.web.highlight import build_marks, highlight

WEB_DIR = Path(__file__).parent
# examples/ lives at the repository root (and at /app/examples in the Docker image).
EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"
EXAMPLE_GEOJSON = "project.geojson"
EXAMPLE_CSV = "plots.csv"
EXAMPLE_PDD = "pdd-section.md"
HASH_DISPLAY_CHARS = 12
NO_VALUE = "\N{EN DASH}"
MAX_UPLOAD_BYTES = 1_000_000  # GeoJSON and CSV, file or pasted text
MAX_PDD_CHARS = 20_000

SEVERITY_LABELS = {
    "critical": "kritisch",
    "major": "wichtig",
    "info": "hinweis",
    "ok": "belegt",
}
DIAGNOSIS_LABELS = {
    "tc_instead_of_tco2e": "Vermutlich tC statt tCO₂e",
    "gross_net_swapped": "Brutto/netto verwechselt",
}
# calc/ reports in English; the page is German. The English text stays as technical detail.
INPUT_ERROR_MESSAGES: dict[type[InputError], str] = {
    InvalidGeoJSONError: "Das GeoJSON ist ungültig.",
    UnsupportedGeometryError: "Unterstützt wird nur ein einfaches GeoJSON-Polygon.",
    OpenRingError: "Ein Ring des Polygons ist nicht geschlossen.",
    InvalidGeometryError: "Die Geometrie des Polygons ist ungültig.",
    MissingColumnError: "In der CSV fehlen Pflichtspalten.",
    EmptyPlotsError: "Die CSV enthält keine Baumzeilen.",
    InvalidValueError: "Ein Wert in den Eingaben ist ungültig.",
    InconsistentPlotAreaError: "Ein Plot hat widersprüchliche Flächenangaben.",
    DuplicateTreeError: "Eine tree_id kommt in einem Plot doppelt vor.",
}

app = FastAPI(title="carbon-preaudit")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WEB_DIR / "templates")  # autoescape is on for .html


def _number(value: float | None, digits: int = 1) -> str:
    return NO_VALUE if value is None else format_de(value, digits)


def _percent(value: float | None) -> str:
    if value is None:
        return NO_VALUE
    return f"{'+' if value >= 0 else '-'}{format_de(abs(value) * 100, 1)} %"


templates.env.filters["de"] = _number  # pyright: ignore[reportUnknownMemberType]
templates.env.filters["de_pct"] = _percent  # pyright: ignore[reportUnknownMemberType]


class MissingInputError(InputError):
    """A required form field is empty."""


class HealthResponse(BaseModel):
    """Response body of the health endpoint."""

    status: str


class _LazyExtractor:
    """Builds the configured extractor on first use, so a missing key surfaces as ExtractionError
    inside the endpoint (shown as a notice) and not as a 500 while resolving the dependency."""

    def extract(self, text: str) -> ClaimedValues:
        return make_extractor().extract(text)


def get_extractor() -> Extractor:
    """Dependency: the configured extractor. Tests override it with a FakeExtractor."""
    return _LazyExtractor()


@app.get("/health")
def health() -> HealthResponse:
    """Report that the service is up."""
    return HealthResponse(status="ok")


def _index(request: Request, **form: str) -> HTMLResponse:
    values = {"geojson_text": "", "csv_text": "", "pdd_text": "", "buffer_pct": ""}
    values.update(form)
    if not values["buffer_pct"]:
        values["buffer_pct"] = str(DEFAULT_BUFFER_PCT)
    return templates.TemplateResponse(request, "index.html", {"form": values})


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """The input form."""
    return _index(request)


@app.get("/example", response_class=HTMLResponse)
def example(request: Request) -> HTMLResponse:
    """The input form prefilled with the files from examples/."""

    def read(name: str) -> str:
        return (EXAMPLES_DIR / name).read_text(encoding="utf-8")

    return _index(
        request,
        geojson_text=read(EXAMPLE_GEOJSON),
        csv_text=read(EXAMPLE_CSV),
        pdd_text=read(EXAMPLE_PDD),
    )


def _too_large(name: str) -> InputError:
    return InputError(f"{name}: Eingabe ist größer als {MAX_UPLOAD_BYTES // 1000} kB.")


def _text_input(upload: UploadFile | None, pasted: str, name: str) -> str:
    """Uploaded file wins over pasted text. Files are read up to the limit plus one byte."""
    if upload is not None and upload.filename:
        data = upload.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise _too_large(name)
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise InputError(f"{name}: Die Datei ist nicht UTF-8-kodiert.") from e
    if not pasted.strip():
        raise MissingInputError(f"{name} fehlt: Datei hochladen oder Text einfügen.")
    if len(pasted.encode("utf-8")) > MAX_UPLOAD_BYTES:
        raise _too_large(name)
    return pasted


def _buffer_pct(raw: str) -> float:
    raw = raw.strip().replace(",", ".")
    if not raw:
        return DEFAULT_BUFFER_PCT
    try:
        value = float(raw)
    except ValueError as e:
        raise InputError(f"Puffer: „{raw}“ ist keine Zahl.") from e
    if not math.isfinite(value):
        raise InputError("Puffer: Wert muss eine endliche Zahl sein.")
    return value


def _input_error_message(error: InputError) -> str:
    """German sentence for errors from calc/, with the English text as detail."""
    german = INPUT_ERROR_MESSAGES.get(type(error))
    return str(error) if german is None else f"{german} Details: {error}"


def _error(request: Request, message: str, status_code: int) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "_error.html", {"message": message}, status_code=status_code
    )


@app.exception_handler(StarletteHTTPException)
async def _form_too_large(request: Request, exc: StarletteHTTPException) -> Response:
    """Starlette answers an oversized form part with 400 and a JSON body; htmx would show nothing.

    Only that case (400 on /check) becomes a readable 422 fragment; everything else is default.
    """
    if exc.status_code == 400 and request.url.path == "/check":
        return _error(request, f"Eingabe zu groß oder fehlerhaft: {exc.detail}", 422)
    return await http_exception_handler(request, exc)


# A plain `def`: FastAPI runs it in the threadpool, so the blocking calculation and the LLM call
# (up to minutes with retries) do not stall the event loop. No await is needed in the body.
@app.post("/check", response_class=HTMLResponse)
def check(
    request: Request,
    extractor: Annotated[Extractor, Depends(get_extractor)],
    geojson_file: UploadFile | None = None,
    csv_file: UploadFile | None = None,
    geojson_text: Annotated[str, Form()] = "",
    csv_text: Annotated[str, Form()] = "",
    pdd_text: Annotated[str, Form()] = "",
    buffer_pct: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Calculate the run, extract the claims, compare, and render the result fragment.

    Status codes: invalid input is 422 (nothing can be shown). A failed extraction is 200
    with a notice: the calculation is valid and shown, only the comparison is missing.
    """
    try:
        geojson = _text_input(geojson_file, geojson_text, "GeoJSON")
        csv_content = _text_input(csv_file, csv_text, "CSV")
        if not pdd_text.strip():
            raise MissingInputError("PDD-Text fehlt.")
        if len(pdd_text) > MAX_PDD_CHARS:
            raise InputError(f"PDD-Text: länger als {MAX_PDD_CHARS} Zeichen.")
        inputs = parse_inputs(geojson, csv_content, _buffer_pct(buffer_pct))
        # calculate() raises InputErrors too: a hole not smaller than the outer ring, overflow.
        run = calculate(inputs)
    except InputError as e:
        return _error(request, _input_error_message(e), 422)
    context: dict[str, object] = {
        "run": run,
        "polygon": inputs.polygon.model_dump(mode="json"),
        "short_hash": run.run_hash[:HASH_DISPLAY_CHARS],
        "pdd_html": highlight(pdd_text, []),
        "findings": [],
        "extraction_error": None,
        "extracted_by": None,
        "severity_labels": SEVERITY_LABELS,
        "diagnosis_labels": DIAGNOSIS_LABELS,
        "field_labels": LABELS,
    }
    try:
        claimed = extractor.extract(pdd_text)
    except ExtractionError as e:
        context["extraction_error"] = str(e)
    else:
        findings = compare(claimed, run, pdd_text)
        context["pdd_html"] = highlight(pdd_text, build_marks(claimed, findings))
        context["findings"] = findings
        context["extracted_by"] = claimed.extracted_by
    return templates.TemplateResponse(request, "_result.html", context)

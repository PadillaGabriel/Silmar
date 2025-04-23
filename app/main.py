import json
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api_ml import get_order_details
from app.database import (
    init_db,
    add_order_if_not_exists,
    marcar_pedido_armado,
    marcar_pedido_despachado,
    get_all_pedidos          # <- Importamos la función de filtrado
)

app = FastAPI()

# --- Paths y persistencia de logísticas ---
BASE_DIR = Path(__file__).parent.resolve()
LOG_PATH = BASE_DIR / "logisticas.json"

def load_logistics() -> list[str]:
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text())
    return []

def save_logistics(lst: list[str]) -> None:
    LOG_PATH.write_text(json.dumps(lst, indent=2))

# --- Montar estáticos y plantillas ---
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# --- Página de inicio ---
@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return templates.TemplateResponse("inicio.html", {"request": request})


# --- Escanear Pedido ---
@app.get("/escanear", response_class=HTMLResponse)
def escanear_get(request: Request):
    return templates.TemplateResponse("escanear.html", {"request": request})

@app.post("/escanear", response_class=JSONResponse)
def escanear_post(order_id: str = Form(...)):
    detalle = get_order_details(order_id)
    if detalle.get("cliente") == "Error":
        return {"success": False}
    primero = detalle["items"][0]
    add_order_if_not_exists(order_id, {
        "cliente": detalle["cliente"],
        "titulo":  primero["titulo"],
        "cantidad": primero["cantidad"],
    })
    return {"success": True, "detalle": detalle}

@app.post("/armar", response_class=JSONResponse)
def armar_pedido(order_id: str = Form(...)):
    ok = marcar_pedido_armado(order_id)
    return {"success": ok}


# --- Despachar Pedido ---
@app.get("/despachar", response_class=HTMLResponse)
def despachar_get(request: Request):
    logisticas = load_logistics()
    return templates.TemplateResponse("despachar.html", {
        "request": request,
        "logisticas": logisticas
    })

@app.post("/despachar", response_class=JSONResponse)
def despachar_post(order_id: str = Form(...), logistica: str = Form(...)):
    ok = marcar_pedido_despachado(order_id, logistica)
    if ok:
        return {"success": True, "mensaje": "Pedido despachado correctamente"}
    return {"success": False, "error": "No se pudo despachar (¿está armado?)"}


# --- Historial de Pedidos ---
@app.get("/historial", response_class=HTMLResponse)
def historial(
    request: Request,
    order_id:  str | None = None,
    date_from: str | None = None,
    date_to:   str | None = None,
    logistica: str | None = None
):
    logisticas = load_logistics()
    pedidos    = get_all_pedidos(order_id, date_from, date_to, logistica)
    return templates.TemplateResponse("historial.html", {
        "request":    request,
        "logisticas": logisticas,
        "pedidos":    pedidos,
        "order_id":   order_id or "",
        "date_from":  date_from or "",
        "date_to":    date_to or "",
        "logistica":  logistica or ""
    })


# --- Configuración de Logísticas ---
@app.get("/configuracion", response_class=HTMLResponse)
def configuracion_get(request: Request):
    logisticas = load_logistics()
    return templates.TemplateResponse("configuracion.html", {
        "request": request,
        "logisticas": logisticas
    })

@app.post("/configuracion", response_class=HTMLResponse)
def configuracion_post(logistica: str = Form(...), request: Request = None):
    lst = load_logistics()
    if logistica and logistica not in lst:
        lst.append(logistica)
        save_logistics(lst)
    return templates.TemplateResponse("configuracion.html", {
        "request":    request,
        "logisticas": lst
    })


# --- Inicializar base de datos al arrancar la app ---
init_db()

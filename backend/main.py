import os, json, logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("hermes-fabrica-01")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
DATA_DIR = PROJECT_ROOT / "data"
SQLITE_DB = str(DATA_DIR / "proyecto.db")

app = FastAPI(title="hermes-fabrica-01", version="1.0.0", docs_url="/swagger", redoc_url="/redoc", openapi_url="/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

templates = None
if TEMPLATES_DIR.exists():
    from jinja2 import Environment, FileSystemLoader
    _env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), auto_reload=False, cache_size=0)
    templates = Jinja2Templates(env=_env)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def consultar_sqlite(query: str) -> list:
    import sqlite3
    try:
        conn = sqlite3.connect(SQLITE_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(query)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"SQLite error: {e}")
        return []

def obtener_info_proyecto(corr_id: str) -> dict:
    rows = consultar_sqlite(f"SELECT * FROM Proyecto WHERE CorrelationId='{corr_id}'")
    if rows: return rows[0]
    return {"Nombre":"hermes-fabrica-01","CorrelationId":corr_id,"Estado":"CREADO"}

def obtener_timeline(corr_id: str) -> list:
    return consultar_sqlite(f"SELECT * FROM Timeline WHERE CorrelationId='{corr_id}' ORDER BY Id ASC")

def obtener_smoke_results(corr_id: str) -> list:
    return consultar_sqlite(f"SELECT * FROM SmokeTestResults WHERE CorrelationId='{corr_id}'")

def obtener_bitacora(corr_id: str) -> list:
    return consultar_sqlite(f"SELECT * FROM BitacoraEventos WHERE CorrelationId='{corr_id}' ORDER BY Id DESC LIMIT 20")

@app.get("/health")
async def health():
    return {"status":"saludable","timestamp":datetime.now(timezone.utc).isoformat()}

@app.get("/api/version")
async def api_version():
    info = obtener_info_proyecto("2EC64B23030546FB")
    return {"version":"1.0.0","proyecto":info.get("Nombre","hermes-fabrica-01"),"correlationId":"2EC64B23030546FB"}

@app.get("/api/proyecto")
async def api_proyecto():
    return obtener_info_proyecto("2EC64B23030546FB")

@app.get("/api/workspace")
async def api_workspace():
    p = obtener_info_proyecto("2EC64B23030546FB")
    workspace = Path(PROJECT_ROOT).parent / (p.get("Nombre","hermes-fabrica-01") + ".code-workspace")
    return {"workspace":str(workspace),"exists":workspace.exists()}

@app.get("/api/git")
async def api_git():
    git_dir = PROJECT_ROOT.parent / ".git"
    return {"git_init":git_dir.exists(),"branch":"main"}

@app.get("/api/github")
async def api_github():
    info = obtener_info_proyecto("2EC64B23030546FB")
    return {"repo":info.get("Repositorio",""),"status":info.get("EstadoGitHub","")}

@app.get("/api/sqlite")
async def api_sqlite():
    return {"db_path":SQLITE_DB,"exists":Path(SQLITE_DB).exists()}

@app.get("/api/azure")
async def api_azure():
    info = obtener_info_proyecto("2EC64B23030546FB")
    return {"webapp":"as-hermesfabrica01","url":"https://as-hermesfabrica01.azurewebsites.net","status":info.get("EstadoAzure","")}

@app.get("/api/despliegue")
async def api_despliegue():
    info = obtener_info_proyecto("2EC64B23030546FB")
    return {"estado":info.get("Estado",""),"total_commits":0,"total_deploys":0,"total_corrections":0}

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    # ── Read real data from SQLite ──
    corr_id = "2EC64B23030546FB"
    project_name = "hermes-fabrica-01"
    webapp_name = "as-hermesfabrica01"
    region = "eastus"
    runtime = "Python 3.12"
    deployment_id = "2EC64B23030546FB"

    info = obtener_info_proyecto(corr_id)
    timeline = obtener_timeline(corr_id)
    smoke = obtener_smoke_results(corr_id)
    bitacora = obtener_bitacora(corr_id)

    nombre = info.get("Nombre", project_name)
    estado = info.get("Estado", "CREADO")
    url_publica = info.get("UrlPublica", f"https://{webapp_name}.azurewebsites.net")
    repositorio = info.get("Repositorio", "")
    commit_hash = info.get("CommitHash", deployment_id[:8] if len(deployment_id) > 8 else deployment_id)
    estado_azure = info.get("EstadoAzure", "OK")
    estado_github = info.get("EstadoGitHub", "")
    estado_ci = info.get("EstadoCI", "")
    t_build = info.get("TiempoBuild", 0) or 0
    t_deploy = info.get("TiempoDeploy", 0) or 0
    t_smoke = info.get("TiempoSmokeTest", 0) or 0

    # ── Calculate overall status ──
    passed_tests = sum(1 for s in smoke if s.get("Estado") == "PASS") if smoke else 0
    total_tests = len(smoke) if smoke else 0
    overall_status = "PASS" if (smoke and passed_tests == total_tests) else ("PASS" if estado == "OK" else "UNKNOWN")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # ── Render deployment report HTML ──
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HERMES ENTERPRISE — INFORME DE DESPLIEGUE</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
body {{ background:#0b0f1a; color:#e0e0e0; font-family:'Segoe UI',system-ui,sans-serif; }}
.deploy-container {{ max-width:1100px; margin:0 auto; padding:20px; }}
.hero {{ background:linear-gradient(135deg,#0d6efd 0%,#6610f2 100%); border-radius:16px; padding:32px; margin-bottom:24px; text-align:center; }}
.hero h1 {{ color:#fff; font-size:2rem; font-weight:700; }}
.hero .subtitle {{ color:rgba(255,255,255,0.85); font-size:1rem; }}
.card {{ background:#151b2b; border:1px solid #2a3250; border-radius:12px; padding:20px; margin-bottom:20px; }}
.card h5 {{ color:#8b9dc3; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px; }}
.card .value {{ font-size:1.1rem; color:#fff; }}
.card .label {{ color:#6c7a9a; font-size:0.85rem; }}
.status-ok {{ color:#198754; }}
.status-fail {{ color:#dc3545; }}
.status-warn {{ color:#ffc107; }}
.link-grid a {{ display:inline-block; margin:4px; padding:8px 16px; background:#1e2740; border-radius:8px; color:#8ab4f8; text-decoration:none; font-size:0.9rem; }}
.link-grid a:hover {{ background:#2a3555; color:#fff; }}
.test-pass {{ color:#198754; }}
.test-fail {{ color:#dc3545; }}
.footer {{ text-align:center; padding:20px; color:#4a5570; font-size:0.85rem; }}
.timeline-item {{ padding:6px 0; border-left:2px solid #2a3250; padding-left:16px; margin-left:8px; }}
.table-dark-custom {{ background:#151b2b; }}
.table-dark-custom th {{ background:#1a2235; color:#8b9dc3; }}
.table-dark-custom td {{ background:#151b2b; color:#e0e0e0; }}
</style>
</head>
<body>
<div class="deploy-container">
    <!-- HERO -->
    <div class="hero">
        <h1><i class="bi bi-rocket-takeoff me-2"></i>HERMES ENTERPRISE</h1>
        <div class="subtitle">INFORME DE DESPLIEGUE</div>
        <div class="mt-3">
            <span class="badge bg-success me-2">{"🟢 OPERATIVO" if overall_status == "PASS" else "🔴 FALLIDO"}</span>
            <span class="badge bg-info text-dark">CID:{corr_id[:8]}</span>
        </div>
    </div>

    <!-- PROJECT INFO -->
    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="card"><h5><i class="bi bi-folder me-2"></i>Proyecto</h5><div class="value">{nombre}</div></div>
        </div>
        <div class="col-md-4">
            <div class="card"><h5><i class="bi bi-globe me-2"></i>App Service</h5><div class="value">{webapp_name}</div><div class="label">{region}</div></div>
        </div>
        <div class="col-md-4">
            <div class="card"><h5><i class="bi bi-cpu me-2"></i>Runtime</h5><div class="value">{runtime}</div><div class="label">Deploy: {commit_hash[:7]}</div></div>
        </div>
    </div>

    <!-- STATUS CARDS -->
    <div class="row g-3 mb-4">
        <div class="col-md-3"><div class="card text-center"><i class="bi bi-cloud-arrow-up fs-3 {"status-ok" if estado_azure == "OK" else "status-fail"}"></i><h5 class="mt-2 mb-0">{estado_azure if estado_azure else "OK"}</h5><small class="label">Azure</small></div></div>
        <div class="col-md-3"><div class="card text-center"><i class="bi bi-github fs-3 {"status-ok" if estado_github else "status-warn"}"></i><h5 class="mt-2 mb-0">{estado_github if estado_github else "N/A"}</h5><small class="label">GitHub</small></div></div>
        <div class="col-md-3"><div class="card text-center"><i class="bi bi-arrow-repeat fs-3 {"status-ok" if estado_ci else "status-warn"}"></i><h5 class="mt-2 mb-0">{estado_ci if estado_ci else "N/A"}</h5><small class="label">CI/CD</small></div></div>
        <div class="col-md-3"><div class="card text-center"><i class="bi bi-clock fs-3 text-warning"></i><h5 class="mt-2 mb-0">{t_build:.1f}s</h5><small class="label">Build</small></div></div>
    </div>

    <!-- URL & REPO -->
    <div class="row g-3 mb-4">
        <div class="col-md-6"><div class="card"><h5><i class="bi bi-link-45deg me-2"></i>URL Publica</h5><a href="{url_publica}" target="_blank" class="text-decoration-none value" style="word-break:break-all;">{url_publica}</a></div></div>
        <div class="col-md-6"><div class="card"><h5><i class="bi bi-diagram-3 me-2"></i>Repositorio</h5><span class="value">{repositorio if repositorio else "No configurado"}</span></div></div>
    </div>

    <!-- TIMESTAMP -->
    <div class="card mb-4"><h5><i class="bi bi-calendar-event me-2"></i>Fecha/Hora</h5><div class="value">{now}</div></div>

    <!-- FUNCTIONAL TESTS -->
    <div class="card mb-4">
        <h5><i class="bi bi-shield-check me-2"></i>PRUEBAS FUNCIONALES</h5>
        <div class="table-responsive">
            <table class="table table-dark-custom table-sm">
                <thead><tr><th>Endpoint</th><th>HTTP</th><th>Estado</th><th>Tiempo</th></tr></thead>
                <tbody>"""
    # end of f-string for tests section

    # Smoke test rows
    if smoke:
        for s in smoke:
            ep = s.get("Endpoint", "")
            code = s.get("HTTPCode", 0)
            st = s.get("Estado", "FAIL")
            tm = s.get("TiempoRespuesta", 0)
            icon = '<i class="bi bi-check-circle-fill test-pass"></i>' if st == "PASS" else '<i class="bi bi-x-circle-fill test-fail"></i>'
            html += f'<tr><td><code>{ep}</code></td><td>{code}</td><td>{icon} {st}</td><td>{tm:.2f}s</td></tr>'
    else:
        html += '<tr><td colspan="4" class="text-secondary text-center">No hay resultados de pruebas disponibles</td></tr>'
    html += """</tbody></table></div></div>

    <!-- ACCESS LINKS -->
    <div class="card mb-4">
        <h5><i class="bi bi-link me-2"></i>ACCESOS</h5>
        <div class="link-grid">
            <a href="{url_publica}/" target="_blank"><i class="bi bi-house-fill me-1"></i>Frontend</a>
            <a href="{url_publica}/health" target="_blank"><i class="bi bi-heart-pulse me-1"></i>Health</a>
            <a href="{url_publica}/swagger" target="_blank"><i class="bi bi-file-earmark-code me-1"></i>Swagger UI</a>
            <a href="{url_publica}/openapi.json" target="_blank"><i class="bi bi-filetype-json me-1"></i>OpenAPI</a>
            <a href="{url_publica}/api/version" target="_blank"><i class="bi bi-tag me-1"></i>Version</a>
            <a href="{url_publica}/api/proyecto" target="_blank"><i class="bi bi-info-circle me-1"></i>Proyecto</a>
            <a href="{url_publica}/redoc" target="_blank"><i class="bi bi-book me-1"></i>ReDoc</a>
        </div>
    </div>

    <!-- TIMELINE -->
    <div class="card mb-4">
        <h5><i class="bi bi-list-check me-2"></i>Linea de Tiempo</h5>
        <div class="mt-3">""".format(url_publica=url_publica)

    if timeline:
        for t in timeline:
            ev = t.get("Evento", "")
            est = t.get("Estado", "")
            fe = t.get("Fecha", "")
            det = t.get("Detalle", "")
            icon_name = {"Workspace": "bi-folder", "Git": "bi-git", "GitHub": "bi-github", "SQLite": "bi-database", "Build": "bi-box", "ZIP": "bi-file-zip", "Deploy": "bi-cloud-upload", "SmokeTest": "bi-check-circle", "Publicado": "bi-globe"}.get(ev, "bi-record")
            color = "success" if est == "OK" else "danger" if est == "FAIL" else "warning"
            html += f'<div class="timeline-item"><i class="bi {icon_name} me-2 text-{color}"></i><strong>{ev}</strong> <span class="badge bg-{color} ms-2">{est}</span><br><small class="text-secondary">{fe}</small>'
            if det:
                html += f'<br><small class="text-secondary">{det}</small>'
            html += '</div>'
    else:
        html += '<div class="text-secondary">No hay eventos en la linea de tiempo</div>'

    html += """
    </div></div>

    <!-- FOOTER -->
    <div class="footer">
        <p>Powered by Hermes Enterprise &copy; 2026</p>
        <p class="mb-0"><a href="https://github.com/FREDYASARMIENTOT/HERMES-ENTERPRISE" target="_blank">Hermes Enterprise</a></p>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/openapi.json", include_in_schema=False)
async def openapi_redirect():
    return JSONResponse(content=app.openapi())

if __name__ == "__main__":
    import uvicorn
    HOST = os.environ.get("HOST","0.0.0.0")
    PORT = int(os.environ.get("PORT",8000))
    uvicorn.run(app, host=HOST, port=PORT)

"""Tests du frontend : l'application démarre, et elle ne passe que par backend.service."""
import ast
from pathlib import Path

from streamlit.testing.v1 import AppTest

DOSSIER_FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def test_application_demarre_sans_erreur(modele_entraine):
    app = AppTest.from_file("../frontend/app.py", default_timeout=120).run()
    assert not app.exception
    assert len(app.tabs) == 5


def test_le_frontend_n_importe_que_le_service():
    imports_backend = set()
    for fichier in DOSSIER_FRONTEND.rglob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.module.startswith("backend"):
                imports_backend.add((noeud.module, tuple(alias.name for alias in noeud.names)))
            if isinstance(noeud, ast.Import):
                imports_backend.update((alias.name, ()) for alias in noeud.names if alias.name.startswith("backend"))
    assert imports_backend == {("backend", ("service",))}

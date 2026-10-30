"""Données partagées par les tests : la base est reconstruite une seule fois, dans un dossier
temporaire, à partir de l'archive brute. Les tests ne touchent jamais data/olist.db.
"""
import pytest

from backend.data import charger_archive_dans_sqlite, lire_table_analyse


@pytest.fixture(scope="session")
def base_test(tmp_path_factory):
    base = tmp_path_factory.mktemp("donnees") / "olist_test.db"
    nb_lignes = charger_archive_dans_sqlite(base=base)
    return base, nb_lignes


@pytest.fixture(scope="session")
def table_analyse(base_test):
    base, _ = base_test
    return lire_table_analyse(base=base)

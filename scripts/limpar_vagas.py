"""Remove duplicatas e publicações claramente antigas do banco local.

Uso:
    python scripts/limpar_vagas.py --dry-run
    python scripts/limpar_vagas.py

O banco guarda histórico para deduplicação. Por isso a limpeza mantém uma
linha por ``chave_secundaria`` e escolhe como representante a linha com
feedback/situação preenchidos; em empate, mantém a coleta mais recente.
"""

from __future__ import annotations

import argparse
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "jobs.db"


def _normalizar(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(char for char in texto if not unicodedata.combining(char)).lower()


def _tem_publicacao_antiga(publicado_em: str | None) -> bool:
    texto = _normalizar(publicado_em)
    return "mes" in texto or "ano" in texto or "month" in texto or "year" in texto


def _prioridade(linha: sqlite3.Row) -> tuple[int, int, int, str, str]:
    """Prioriza dados manuais e, depois, a coleta mais recente."""
    feedback_preenchido = int(linha["feedback"] not in (None, ""))
    situacao_preenchida = int(linha["situacao"] not in (None, "", "nova"))
    digest_pendente = int(linha["digest_pendente"] == 1)
    return (
        feedback_preenchido,
        situacao_preenchida,
        digest_pendente,
        linha["encontrada_em"] or "",
        linha["id"],
    )


def _ids_para_remover(conn: sqlite3.Connection) -> tuple[set[str], int, int]:
    conn.row_factory = sqlite3.Row
    linhas = conn.execute(
        """
        SELECT id, chave_secundaria, feedback, situacao, digest_pendente,
               encontrada_em, publicado_em
        FROM vagas_vistas
        """
    ).fetchall()

    por_chave: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for linha in linhas:
        chave = (linha["chave_secundaria"] or "").strip()
        if chave:
            por_chave[chave].append(linha)

    duplicatas: set[str] = set()
    for grupo in por_chave.values():
        if len(grupo) > 1:
            representante = max(grupo, key=_prioridade)
            duplicatas.update(linha["id"] for linha in grupo if linha["id"] != representante["id"])

    antigas = {
        linha["id"]
        for linha in linhas
        if _tem_publicacao_antiga(linha["publicado_em"])
    }
    ids = duplicatas | antigas
    return ids, len(duplicatas), len(antigas - duplicatas)


def limpar_vagas(db_path: Path = DB_PATH, dry_run: bool = False) -> tuple[int, int, int, int]:
    conn = sqlite3.connect(db_path)
    try:
        ids, duplicatas, antigas = _ids_para_remover(conn)
        antes = conn.execute("SELECT COUNT(*) FROM vagas_vistas").fetchone()[0]

        if not dry_run:
            with conn:
                conn.executemany(
                    "DELETE FROM vagas_vistas WHERE id = ?",
                    ((id_,) for id_ in ids),
                )
            integridade = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integridade != "ok":
                raise RuntimeError(f"integrity_check falhou: {integridade}")

        depois = antes - len(ids)
        return antes, depois, duplicatas, antigas
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    antes, depois, duplicatas, antigas = limpar_vagas(args.db, args.dry_run)
    acao = "seriam removidos" if args.dry_run else "removidos"
    print(f"Registros antes: {antes}")
    print(f"Duplicatas {acao}: {duplicatas}")
    print(f"Publicações antigas {acao}: {antigas}")
    print(f"Registros depois: {depois}")


if __name__ == "__main__":
    main()

"""Teste manual de scraping/filtro SEM efeito colateral.

Roda um scraper específico (ou todos os do perfil) com os termos que
quiser, imprime as vagas BRUTAS que a fonte devolveu e aplica o filtro do
perfil pra mostrar o funil completo: bruta -> filtrada, com motivo de
aprovação/reprovação em cada vaga. Não toca em jobs.db, não notifica no
Telegram, não marca nada como visto.

Útil pra:
- investigar uma fonte num termo específico sem gastar ciclo de produção
- testar termo de busca novo antes de adicionar no config.py
- ver POR QUE uma vaga passou ou foi barrada (cargo, escopo, cidade) sem
  ter que ler o código do filtro
"""
import argparse
import sys

from logger import get_logger
from perfis import PERFIS
from utils.filtro import filtrar_vagas

logger = get_logger()


def _cabeçalho_vaga(v):
    return (
        f"[{v.site}] {v.titulo} | {v.empresa} | {v.local} | modalidade="
        f"{v.modalidade or 'não informada'} | publicado={v.publicado_em or 'não informado'}"
    )


def _diagnostico(v, regras):
    """Motivo legível de aprovação ou de reprovação. Reaproveita a avaliação
    interna (_avaliar) pra detalhar o porquê sem duplicar a lógica — o mesmo
    objeto que combina_com()/pontuar_relevancia() usam."""
    av = v._avaliar(regras)

    if av.aprovada:
        motivo = v.motivo_aprovacao(regras)
        if av.bate_remoto:
            mercado = ", ".join(sorted(av.escopos)) if av.escopos else "sem mercado declarado"
            return f"APROVADA ({v.relevancia}/10) - {motivo} - escopo: {mercado}"
        return f"APROVADA ({v.relevancia}/10) - {motivo}"

    razoes = []
    bate_cargo = av.bate_forte or av.bate_ambiguo or av.bate_ferramenta
    if not bate_cargo:
        razoes.append("cargo não bate (nem forte, nem ambíguo+qualificador, nem ferramenta+cargo)")
    if av.bate_remoto:
        mercado = ", ".join(sorted(av.escopos)) if av.escopos else "sem mercado declarado"
        escopo_rejeitado = v.escopo_rejeitado_por_mercado(regras)
        if escopo_rejeitado:
            razoes.append(f"escopo rejeitado por mercado: {', '.join(sorted(escopo_rejeitado))}")
        elif not av.idioma_bateu_titulo and regras.idiomas_exigidos is not None:
            razoes.append("remoto sem mercado e sem idioma exigido no título")
    else:
        razoes.append(
            f"modalidade {v.modalidade or 'não informada'} não é remota "
            "(ou o perfil só aceita remoto)"
        )
    return "REPROVADA - " + " | ".join(razoes)


def _rodar_scraper(scraper, regras):
    print("\n" + "=" * 70)
    print(f"FONTE: {scraper.__class__.__name__} | termos: {', '.join(scraper.termos_busca)}")
    print("=" * 70)

    try:
        vagas = scraper.buscar_vagas()
    except Exception as e:
        print(f"\nERRO na fonte {scraper.__class__.__name__}: {e}")
        logger.exception(f"Erro no scraper {scraper.__class__.__name__}")
        return

    print(f"\n{len(vagas)} vaga(s) bruta(s)\n")

    aprovadas, descartes_escopo = filtrar_vagas(vagas, regras)
    ids_aprovados = {id(v) for v in aprovadas}

    for i, v in enumerate(vagas, 1):
        print(f"{i:>3}. {_cabeçalho_vaga(v)}")
        print(f"     -> {_diagnostico(v, regras)}")

    print(f"\nFunil: {len(vagas)} brutas -> {len(aprovadas)} filtradas")

    if descartes_escopo:
        detalhe = "; ".join(f"{escopo} ({n})" for escopo, n in descartes_escopo.most_common())
        print(f"Descarte por escopo: {detalhe}")

    if aprovadas:
        print("\nAprovadas (ranqueadas por relevância):")
        for i, v in enumerate(sorted(aprovadas, key=lambda x: -x.relevancia), 1):
            print(f"{i:>3}. {_cabeçalho_vaga(v)}")
    return vagas


def main():
    parser = argparse.ArgumentParser(
        description="Teste manual de scraping/filtro (sem DB e sem Telegram)"
    )
    parser.add_argument(
        "--perfil",
        required=True,
        choices=sorted(PERFIS.keys()),
        help="Perfil cujas regras de filtro e fontes usar ('brasil' ou 'internacional').",
    )
    parser.add_argument(
        "--fonte",
        help="Nome da classe do scraper (ex: CathoScraper). Padrão: TODAS as fontes do perfil.",
    )
    parser.add_argument(
        "--termos",
        nargs="+",
        help="Termos de busca (substitui os do perfil). Ex: 'analista de dados' 'power bi'.",
    )
    args = parser.parse_args()

    perfil = PERFIS[args.perfil]

    termos = args.termos or perfil.termos_busca
    print(f"\nPERFIL: {perfil.nome}")
    print(f"Termos: {', '.join(termos)}")

    definicoes = perfil.definicao_scrapers
    if args.fonte:
        definicoes = [d for d in definicoes if d.classe.__name__ == args.fonte]
        if not definicoes:
            nomes = ", ".join(sorted(d.classe.__name__ for d in perfil.definicao_scrapers))
            print(f"\nFonte '{args.fonte}' não existe neste perfil. Disponíveis: {nomes}")
            sys.exit(1)

    ouro = None
    for definicao in definicoes:
        scraper = definicao.classe(termos_busca=termos, **definicao.kwargs_extras)
        ouro = _rodar_scraper(scraper, perfil.regras)

    if ouro is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
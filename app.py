import csv
import json
import sys
from pathlib import Path


CAMPOS = [
    'no_entidade', 'co_entidade', 'no_uf', 'sg_uf', 'co_uf',
    'no_municipio', 'co_municipio', 'no_mesorregiao', 'co_mesorregiao',
    'no_microrregiao', 'co_microrregiao', 'nu_ano_censo', 'no_regiao',
    'co_regiao', 'qt_mat_bas', 'qt_mat_inf', 'qt_mat_fund', 'qt_mat_med',
    'qt_mat_prof', 'qt_mat_eja', 'qt_mat_esp',
]

CAMPOS_ESCOLA = [
    'no_entidade', 'co_entidade', 'no_uf', 'sg_uf', 'co_uf',
    'no_municipio', 'co_municipio', 'nu_ano_censo', 'no_regiao', 'co_regiao',
]

CAMPOS_MATRICULA = [
    'co_entidade', 'qt_mat_bas', 'qt_mat_inf', 'qt_mat_fund',
    'qt_mat_med', 'qt_mat_prof', 'qt_mat_eja', 'qt_mat_esp',
]

CAMPOS_NUMERICOS = [
    'co_entidade', 'co_uf', 'co_municipio', 'co_mesorregiao',
    'co_microrregiao', 'nu_ano_censo', 'co_regiao', 'qt_mat_bas',
    'qt_mat_inf', 'qt_mat_fund', 'qt_mat_med', 'qt_mat_prof',
    'qt_mat_eja', 'qt_mat_esp',
]


def ler_csv(caminho_csv, campos, codificacao):
    registros = {}

    with open(caminho_csv, 'r', encoding=codificacao, newline='') as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=';')
        if not leitor.fieldnames:
            raise ValueError(f'CSV vazio ou sem cabeçalho: {caminho_csv}')

        leitor.fieldnames = [nome.strip().lower() for nome in leitor.fieldnames]
        obrigatorios = campos + ['sg_uf', 'nu_ano_censo', 'co_uf']
        ausentes = [campo for campo in obrigatorios if campo not in leitor.fieldnames]
        if ausentes:
            raise ValueError('Colunas ausentes em ' + str(caminho_csv) + ': ' + ', '.join(ausentes))

        for numero_linha, linha in enumerate(leitor, start=2):
            uf = (linha['sg_uf'] or '').strip().upper()
            ano = (linha['nu_ano_censo'] or '').strip()
            if uf != 'PB' or ano != '2025':
                continue

            if (linha['co_uf'] or '').strip() != '25':
                raise ValueError(f'Linha {numero_linha}: o código de UF de PB deve ser 25.')

            registro = {}
            for campo in campos:
                valor = (linha[campo] or '').strip()
                if valor == '':
                    registro[campo] = None
                elif campo in CAMPOS_NUMERICOS:
                    try:
                        registro[campo] = int(valor)
                    except ValueError:
                        raise ValueError(
                            f'Linha {numero_linha}: {campo} não é um inteiro: {valor!r}'
                        ) from None
                    if registro[campo] < 0:
                        raise ValueError(f'Linha {numero_linha}: {campo} é negativo.')
                else:
                    registro[campo] = valor

            codigo = registro['co_entidade']
            if codigo is None:
                raise ValueError(f'Linha {numero_linha}: código de instituição vazio.')
            if codigo in registros:
                raise ValueError(f'Código de instituição repetido: {codigo}')
            registros[codigo] = registro

    if not registros:
        raise ValueError(f'Não há registros PB/2025 em {caminho_csv}.')
    return registros


def ler_tabela(caminho_csv, campos):
    try:
        return ler_csv(caminho_csv, campos, 'utf-8-sig')
    except UnicodeDecodeError:
        return ler_csv(caminho_csv, campos, 'latin-1')


def extrair_dados(caminho_escolas, caminho_matriculas, caminho_json):
    escolas = ler_tabela(caminho_escolas, CAMPOS_ESCOLA)
    matriculas = ler_tabela(caminho_matriculas, CAMPOS_MATRICULA)

    for codigo in matriculas:
        if codigo not in escolas:
            raise ValueError(f'Instituição {codigo} está em matrículas, mas não em escolas.')

    instituicoes = []
    for codigo, escola in escolas.items():
        # Preserva as 21 propriedades e sua ordem. Ausência de dado vira null.
        instituicao = {campo: None for campo in CAMPOS}
        for campo in CAMPOS_ESCOLA:
            instituicao[campo] = escola[campo]

        if codigo in matriculas:
            for campo in CAMPOS_MATRICULA:
                instituicao[campo] = matriculas[codigo][campo]
        instituicoes.append(instituicao)

    caminho_json = Path(caminho_json)
    caminho_json.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_json, 'w', encoding='utf-8') as arquivo:
        json.dump(instituicoes, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
        arquivo.write('\n')

    print(f'{len(instituicoes)} instituições da Paraíba exportadas.')
    print(f'{len(matriculas)} instituições com registro na tabela de matrículas.')
    print('Os quatro campos de mesorregião/microrregião ficam null: ausentes na edição 2025.')
    print(f'JSON: {caminho_json.resolve()}')
    return instituicoes


if __name__ == '__main__':
    pasta_projeto = Path(__file__).resolve().parent
    escolas_padrao = pasta_projeto / 'dados' / 'Tabela_Escola_2025_V2.csv'
    matriculas_padrao = pasta_projeto / 'dados' / 'Tabela_Matricula_2025_V2.csv'
    saida_padrao = pasta_projeto.parent / 'src' / 'datasets' / 'instituicoes_pb_2025.json'

    if len(sys.argv) not in (1, 3, 4):
        print('Uso: python app.py [caminho_csv_escolas caminho_csv_matriculas] [caminho_json]')
        sys.exit(1)

    escolas = Path(sys.argv[1]) if len(sys.argv) >= 3 else escolas_padrao
    matriculas = Path(sys.argv[2]) if len(sys.argv) >= 3 else matriculas_padrao
    saida = Path(sys.argv[3]) if len(sys.argv) == 4 else saida_padrao
    try:
        extrair_dados(escolas, matriculas, saida)
    except (OSError, ValueError, csv.Error) as erro:
        print(f'Não foi possível extrair os dados: {erro}', file=sys.stderr)
        sys.exit(1)

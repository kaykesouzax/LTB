from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import io
import re
import os

app = Flask(__name__)
CORS(app)

VENDEDORES = {
    "29070003": {"nome": "ALEXSANDRO ALVES DE SOUZA",           "pdv": "LABREA"},
    "29070004": {"nome": "ANDREI ALVES DE SOUZA",               "pdv": "HUMAITA"},
    "29070005": {"nome": "ANGELA ALMEIDA DA SILVA",             "pdv": "CANUTAMA"},
    "29070006": {"nome": "ANTONIO MARCIO BATISTA DOS S.",       "pdv": "LABREA"},
    "29070008": {"nome": "DIEGO PEREIRA GOMES",                 "pdv": "HUMAITA"},
    "29070009": {"nome": "EDSON RUAN LEAL NOGUEIRA",            "pdv": "HUMAITA"},
    "29070012": {"nome": "LUAN HENRIQUE ROCHA DIAS",            "pdv": "APUI"},
    "29070014": {"nome": "RAIMISON DE FRANCA RODRIGUES",        "pdv": "HUMAITA"},
    "29070016": {"nome": "THALYS CASTRO DA SILVA",              "pdv": "LABREA"},
    "29070018": {"nome": "JOSE EWERTON BARROS CAVALCANTE",      "pdv": "LABREA"},
    "29070020": {"nome": "MARIA HELENA GOMES PIMENTA",          "pdv": "HUMAITA"},
    "29070022": {"nome": "SERGIO MOREIRA DA COSTA JUNIOR",      "pdv": "HUMAITA"},
    "29070034": {"nome": "CARLOS BARBOSA DE SOUZA",             "pdv": "BOCA DO ACRE"},
    "29070039": {"nome": "ANTONIO HENRIQUE DA COSTA DOS SANTOS","pdv": "BOCA DO ACRE"},
    "29070049": {"nome": "ADRIANO JOTAERRY VIEIRA NUNES",       "pdv": "HUMAITA"},
    "29070052": {"nome": "WENDEL SILVA DE OLIVEIRA",            "pdv": "BOCA DO ACRE"},
    "29070076": {"nome": "DOUGLAS MACIEL DIAS",                 "pdv": "LABREA"},
    "29070077": {"nome": "BRUNA CARLA BEZERRA SOUZA",           "pdv": "BOCA DO ACRE"},
    "29070080": {"nome": "KAWANE ANDRADE KISTNER",              "pdv": "KM 180"},
    "29070082": {"nome": "RODRIGO DOS SANTOS QUEMEL",           "pdv": "TAPAUA"},
    "29070087": {"nome": "GUILHERME DO NASCIMENTO MELO",        "pdv": "CANUTAMA"},
    "29070089": {"nome": "JONAS BARROS COELHO",                 "pdv": "PAUINI"},
    "29070090": {"nome": "OMAR VALE NASCIMENTO",                "pdv": "PAUINI"},
    "29070094": {"nome": "TAYANE MAIA E SILVA",                 "pdv": "LABREA"},
    "29070101": {"nome": "ARTEMISA BELEM DE SOUZA",             "pdv": "LABREA"},
    "29070109": {"nome": "JOSE WILLIAN DA SILVA PINTO",         "pdv": "HUMAITA"},
    "29070110": {"nome": "SHIRLANE SANTANA DE MELO",            "pdv": "APUI"},
    "29070114": {"nome": "ROSIELE DA SILVA TORRES",             "pdv": "HUMAITA"},
    "29070115": {"nome": "ROSA CARVALHO NUNES",                 "pdv": "HUMAITA"},
    "29070116": {"nome": "ANTONIA AGUIDA NASCIMENTO DA S.",     "pdv": "LABREA"},
    "29070118": {"nome": "JANDERSON GUSTAVO CARNEIRO",          "pdv": "LABREA"},
    "29070119": {"nome": "RUBENITO GOMES ONOFRE JUNIOR",        "pdv": "BOCA DO ACRE"},
}

FRETES = {
    "LABREA":       {"valor": "650,00", "extenso": "SEISCENTOS E CINQUENTA"},
    "CANUTAMA":     {"valor": "550,00", "extenso": "QUINHENTOS E CINQUENTA"},
    "TAPAUA":       {"valor": "550,00", "extenso": "QUINHENTOS E CINQUENTA"},
    "HUMAITA":      {"valor": "850,00", "extenso": "OITOCENTOS E CINQUENTA"},
    "KM 180":       {"valor": "850,00", "extenso": "OITOCENTOS E CINQUENTA"},
    "APUI":         {"valor": "850,00", "extenso": "OITOCENTOS E CINQUENTA"},
    "BOCA DO ACRE": {"valor": "850,00", "extenso": "OITOCENTOS E CINQUENTA"},
    "PAUINI":       {"valor": "850,00", "extenso": "OITOCENTOS E CINQUENTA"},
}

def nome_curto(nome_completo):
    partes = nome_completo.strip().split()
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1]}"

def parse_client_data(raw: str, nproposta_manual="", nrecibo_manual="", matricula="") -> dict:
    # Parser formato ANTIGO (label:\n valor) - NÃO MEXER
    def get_old(label):
        pattern = rf"^{re.escape(label)}:\s*\n([^\n]+)"
        match = re.search(pattern, raw, re.IGNORECASE | re.MULTILINE)
        if match:
            val = match.group(1).strip()
            if val.endswith(':') or not val:
                return ""
            return val
        return ""
    
    # Parser formato NOVO (inline + estruturas mistas)
    def get_new(label):
        pattern = rf"{re.escape(label)}:\s*([^\n]+)"
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'\s+(Nome Social|Ocupação|Pessoa|Tipo Documento|Orgão Expeditor|Data Emissão|Gênero|Estado Civil|Emancipado|Alfabetizado|Telefone Recado|Telefone Residencial|Telefone Celular|E-mail|Nacionalidade|UF de Nascimento|Número|Complemento|Bairro|Cidade|UF|Categoria|Prazo Original Grupo|Tipo de Cota|Dia Vencimento|Data de Venda|Plano|Valor do Crédito|Modelo):.*', '', val, flags=re.IGNORECASE).strip()
            if val and not val.endswith(':') and val != '-':
                return val
        return ""
    
    def get(label):
        val = get_new(label)
        if val:
            return val
        return get_old(label)

    nome = get("Nome")
    ddn = get("Data Nascimento") or get("Data de Nascimento")
    nac = get("Nacionalidade")
    
    # Estado Civil - novo formato: "Estado Civil: \n Emancipado: \n SOLTEIRO(A)"
    estado_civil_match = re.search(r'Estado\s+Civil:.*?\n(?:Emancipado:)?\s*\n([A-Z]+(?:\([A-Z]\))?)', raw, re.I | re.DOTALL)
    estado_civil = estado_civil_match.group(1).strip().upper() if estado_civil_match else get("Estado Civil").upper()
    
    # Profissão/Ocupação - novo formato vem antes de "Pessoa:"
    profissao_match = re.search(r'Ocupação:\s*(?:Pessoa:)?\s*\n([A-Z]+)', raw, re.I)
    profissao = profissao_match.group(1).strip() if profissao_match else (get("Ocupação") or get("Profissão"))
    
    cpf = get("CPF")
    
    rg_match = re.search(r'Número\s+Documento:.*?\n(?:REGISTRO\s+GERAL|RG)?\s*\n?([0-9]+)', raw, re.I | re.DOTALL)
    rg = rg_match.group(1).strip() if rg_match else (get("Número do Documento") or get("RG"))
    
    # Órgão Emissor e Data Emissão - novo formato: "Orgão Expeditor:\n Data Emissão:\n SSP AM\n 13/02/2023"
    orgao_match = re.search(r'Orgão\s+Expeditor:.*?\n(?:Data\s+Emissão:)?\s*\n([^\n]+)\n([0-9]{2}/[0-9]{2}/[0-9]{4})', raw, re.I | re.DOTALL)
    if orgao_match:
        orgao_emissor = orgao_match.group(1).strip()
        data_emissao_raw = orgao_match.group(2).strip()
    else:
        orgao_emissor = get("Orgão Expeditor") or get("Órgão Emissor") or ""
        data_emissao_raw = get("Data Emissão") or ""
    de_parts = re.split(r'[/\-]', data_emissao_raw)
    dia_emissao = de_parts[0].zfill(2) if len(de_parts) > 0 and de_parts[0] else ""
    mes_emissao = de_parts[1].zfill(2) if len(de_parts) > 1 and de_parts[1] else ""
    ano_emissao = de_parts[2] if len(de_parts) > 2 else ""
    
    phone1 = get("Telefone Celular") or get("Telefone 1")
    phone2 = get("Telefone Residencial") or get("Telefone 2")
    email = get("E-mail") or get("Email")
    
    # ─── ENDEREÇO - NOVO FORMATO ─────────────────────────────────────────────
    # Endereço e CEP: pula "CEP:\n" se presente e pega a rua na linha seguinte
    end_cep_match = re.search(r'Endereço:\s*\n(?:CEP:\s*\n)?([^\n]+)\n([0-9][0-9\.\-]+)', raw, re.I)
    endereco_novo = end_cep_match.group(1).strip() if end_cep_match else ""
    cep_novo      = end_cep_match.group(2).strip() if end_cep_match else ""

    # Número: logo após "Número:\n" - se numérico é o número, senão é complemento
    num_raw_m = re.search(r'Número:\s*\n([^\n]+)', raw, re.I)
    num_raw   = num_raw_m.group(1).strip() if num_raw_m else ""
    if num_raw and re.match(r'^[0-9]+$', num_raw):
        numero_raw_ok    = num_raw
        complemento_novo = ""
    else:
        numero_raw_ok    = ""
        complemento_novo = num_raw if num_raw and ":" not in num_raw else ""  # "AME" sim, "Complemento: Bairro:" não

    # Bairro inline: "Complemento: Bairro:\n VALOR" — só se a linha seguinte não for outra label
    if re.search(r'Complemento:\s*Bairro:\s*\nCidade:', raw, re.I):
        bairro_cb = ""  # bairro vem do bloco Cidade/UF
    else:
        bairro_cb_m = re.search(r'Complemento:\s*Bairro:\s*\n([^\n]+)', raw, re.I)
        bairro_cb   = bairro_cb_m.group(1).strip() if bairro_cb_m else ""

    # Padrão unificado: cidade na 1ª linha após "Cidade: UF:", depois lixo (qualquer linha não-numérica),
    # número, bairro, UF — robusto a espaços no início das linhas
    end_bloco = re.search(
        r'Cidade:\s*UF:\s*\n\s*([^\n]+)\n(?:\s*[^\n]*\n)*?\s*(\d+)\n\s*([^\n]+)\n\s*([A-Z]{2})(?=\s*\n|\s*$)',
        raw, re.I
    )

    if end_bloco:
        cidade_novo = end_bloco.group(1).strip()
        numero_novo = end_bloco.group(2).strip()
        bairro_novo = end_bloco.group(3).strip()
        uf_novo     = end_bloco.group(4).strip()
    else:
        cidade_novo = numero_novo = bairro_novo = uf_novo = ""

    endereco    = endereco_novo    or get("Endereço")
    numero      = numero_raw_ok    or numero_novo or get("Número")
    complemento = complemento_novo or get("Complemento")
    bairro      = bairro_novo      or get("Bairro")
    cidade      = cidade_novo      or get("Cidade")
    uf          = uf_novo          or get("UF")
    cep         = cep_novo         or get("CEP")
    
    modelo = get("Modelo")
    
    valor_match = re.search(r'Valor\s+do\s+Crédito\*?:.*?\n?(R\$\s*[0-9\.,]+)', raw, re.I | re.DOTALL)
    valor_bem = valor_match.group(1).strip() if valor_match else (get("Valor do Bem Base*") or get("Valor do Bem Base"))
    
    parc_match = re.search(r'Valor\s+Total\s+da\s+Parcela\s+R\$\s*\n?([0-9\.,]+)', raw, re.I | re.DOTALL)
    valor_parc = parc_match.group(1).strip() if parc_match else get("Valor da Parcela")
    
    prazo_match = re.search(r'Prazo\s+Original\s+Grupo:.*?([0-9]+)', raw, re.I | re.DOTALL)
    prazo = prazo_match.group(1).strip() if prazo_match else get("Prazo")
    
    vencimento = get("Dia Vencimento")
    
    # Tipo de Cota - novo formato: "Tipo de Cota: 25 \n Cota Reposição"
    tipo_cota_match = re.search(r'Tipo\s+de\s+Cota:.*?\n(Cota\s+(?:Nova|Reposição|Reposicao))', raw, re.I | re.DOTALL)
    tipo_cota = tipo_cota_match.group(1).strip().upper() if tipo_cota_match else get("Tipo de Cota").upper()
    
    plano = get("Plano").upper()
    data_venda = get("Data de Venda")

    nrecibo = nrecibo_manual or ""
    nproposta = nproposta_manual or ""

    vendedor = VENDEDORES.get(matricula.strip(), {})
    nome_vendedor = vendedor.get("nome", "")
    pdv = vendedor.get("pdv", "")
    frete = FRETES.get(pdv.upper(), {})
    frete_valor = frete.get("valor", "")
    frete_extenso = frete.get("extenso", "")

    vendedor_codigo = f"{nome_curto(nome_vendedor)} - {matricula}" if nome_vendedor and matricula else ""

    c = re.sub(r'\D', '', cpf)
    cpf_fmt = f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else cpf

    def fmt_ddd(p):
        d = re.sub(r'\D', '', p)
        return d[:2] if len(d) >= 2 else ""
    def fmt_tel(p):
        d = re.sub(r'\D', '', p)
        if len(d) == 11: return f"{d[2:7]}-{d[7:]}"
        if len(d) == 10: return f"{d[2:6]}-{d[6:]}"
        return p

    ddn_parts = re.split(r'[/\-]', ddn)
    dia_nasc = ddn_parts[0].zfill(2) if len(ddn_parts) > 0 and ddn_parts[0] else ""
    mes_nasc = ddn_parts[1].zfill(2) if len(ddn_parts) > 1 and ddn_parts[1] else ""
    ano_nasc = ddn_parts[2] if len(ddn_parts) > 2 else ""

    endereco_completo = endereco
    if numero:
        endereco_completo = f"{endereco}, {numero}"

    data_parts = re.split(r'[/\-]', data_venda)
    dia_venda = data_parts[0].zfill(2) if len(data_parts) > 0 and data_parts[0] else ""
    mes_venda_num = data_parts[1].zfill(2) if len(data_parts) > 1 else ""
    ano_venda = data_parts[2] if len(data_parts) > 2 else ""
    meses = {"01":"JANEIRO","02":"FEVEREIRO","03":"MARÇO","04":"ABRIL","05":"MAIO","06":"JUNHO",
             "07":"JULHO","08":"AGOSTO","09":"SETEMBRO","10":"OUTUBRO","11":"NOVEMBRO","12":"DEZEMBRO"}
    mes_venda = meses.get(mes_venda_num, mes_venda_num.upper())

    local_assinatura = f"{cidade}-{uf}" if cidade and uf else cidade or ""

    ec_solteiro = "X" if "SOLTEIRO" in estado_civil else ""
    ec_casado = "X" if "CASADO" in estado_civil and "DIVORCIADO" not in estado_civil else ""
    ec_div = "X" if "DIVORCIADO" in estado_civil else ""
    ec_outros = "X" if estado_civil and not any(x in estado_civil for x in ["SOLTEIRO","CASADO","DIVORCIADO"]) else ""

    cota_nova = "X" if "NOVA" in tipo_cota else ""
    cota_repos = "X" if "REPOSI" in tipo_cota else ""

    plano_map = {
        "SUPER LEGAL":"Texto6","MULTICHANCES":"Texto7",
        "VOU DE HONDA +":"Texto8","MINHA SCOOTER HONDA+":"Texto9",
        "#VOU DE HONDA+":"Texto10","NORMAL":"Texto11",
        "MEGA FÁCIL":"Texto12","CONQUISTA":"Texto13",
        "VOU DE HONDA":"Texto14","MINHA SCOOTER HONDA":"Texto15",
        "#VOU DE HONDA":"Texto16","TRX/CRF":"Texto17",
        "ESPECIAL":"Texto18","MASTER":"Texto19","ADVANCE":"Texto20",
    }
    plano_field = None
    for key, field in plano_map.items():
        if key in plano:
            plano_field = field
            break

    fields = {
        "NOME": nome, "DIA": dia_nasc, "MÊS": mes_nasc, "ANO": ano_nasc,
        "NACIONALIDADE": nac, "1": ec_solteiro, "2": ec_casado, "3": ec_div, "4": ec_outros,
        "PROFISSÃO": profissao, "NÚMERO DO CPF": cpf_fmt, "NÚMERO DE IDENTIDADERG": rg,
        "ORGÃO EMISSOR": orgao_emissor, "DIA 2": dia_emissao, "MÊS 2": mes_emissao, "ANO 2": ano_emissao,
        "ENDEREÇO": endereco_completo, "BAIRRO": bairro, "CIDADE": cidade, "ESTADO": uf, "CEP": cep,
        "DDD 1": fmt_ddd(phone1), "TELEFONE 1": fmt_tel(phone1), "TELEFONE 2": phone2, "EMAIL": email,
        "NRECI": nrecibo, "NPROP": nproposta, "MODELO": modelo,
        "VALOR BASE DO BEM": valor_bem, "VALOR DA PARCELA": valor_parc,
        "QTD DE PARC": prazo, "VENC DE PARCELA": vencimento,
        "Texto2": cota_nova, "Texto3": cota_repos, "Texto4": "X", "Texto5": "",
        "CIDADE_WKMH": local_assinatura, "DIA_0HVI": dia_venda, "MES": mes_venda, "ANO_GXGT": ano_venda,
        "Assinatura Cliente": "", "IDVE": vendedor_codigo, "PDV": pdv, "MAT": matricula,
        "autoriza a REVEMAR COMÉRCIO DE MOTOS LTDA CONCESSIONÁRIA a": "",
        "undefined": "", "ANOM": "",
        "CIENTE DO PAGAMENTO DO FRETE NO VALOR DE R": frete_valor, "undefined_2": frete_extenso,
        "ESCREVER DE PRÓPRIO PUNHO FICO CIENTE DO VALOR DO FRETE": "",
        "Assinatura do responsável Legal ou Assinatura a Rogo quando": "",
        "Assinatura do responsável Legal ou Assinatura a Rogo": "",
    }

    if plano_field:
        fields[plano_field] = "X"

    return fields

@app.route("/preencher", methods=["POST"])
def preencher():
    if "pdf" not in request.files:
        return jsonify({"erro": "PDF não enviado"}), 400
    if "dados" not in request.form:
        return jsonify({"erro": "Dados do cliente não enviados"}), 400

    pdf_file = request.files["pdf"]
    dados_raw = request.form["dados"]
    nproposta_manual = request.form.get("nproposta", "")
    nrecibo_manual = request.form.get("nrecibo", "")
    matricula = request.form.get("matricula", "")

    try:
        fields = parse_client_data(dados_raw, nproposta_manual, nrecibo_manual, matricula)
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        writer.append(reader)

        for page in writer.pages:
            writer.update_page_form_field_values(page, fields, auto_regenerate=False)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        nome_arquivo = re.sub(r'[^a-zA-Z0-9_]', '_', fields.get("NOME", "documento"))
        return send_file(output, mimetype="application/pdf", as_attachment=True,
                        download_name=f"REVEMAR_{nome_arquivo}.pdf")

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/vendedor/<matricula>", methods=["GET"])
def get_vendedor(matricula):
    vendedor = VENDEDORES.get(matricula.strip())
    if vendedor:
        pdv = vendedor["pdv"]
        frete = FRETES.get(pdv.upper(), {})
        return jsonify({
            "matricula": matricula, "nome": vendedor["nome"],
            "nome_curto": nome_curto(vendedor["nome"]),
            "pdv": pdv, "frete": frete.get("valor", ""),
        })
    return jsonify({"erro": "Matrícula não encontrada"}), 404

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

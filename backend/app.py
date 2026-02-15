from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import io
import re
import os

app = Flask(__name__)
CORS(app)

# ─── Tabela de vendedores ──────────────────────────────────────────────────
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

def nome_curto(nome_completo):
    """Retorna PRIMEIRO + ÚLTIMO nome"""
    partes = nome_completo.strip().split()
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1]}"

def parse_client_data(raw: str, nproposta_manual="", nrecibo_manual="", matricula="") -> dict:
    def get(label):
        pattern = rf"^{re.escape(label)}:\s*\n([^\n]+)"
        match = re.search(pattern, raw, re.IGNORECASE | re.MULTILINE)
        if match:
            val = match.group(1).strip()
            if val.endswith(':') or not val:
                return ""
            return val
        return ""

    nome          = get("Nome")
    ddn           = get("Data de Nascimento")
    nac           = get("Nacionalidade")
    estado_civil  = get("Estado Civil").upper()
    profissao     = get("Ocupação") or get("Profissão")
    cpf           = get("CPF")
    rg            = get("Número do Documento") or get("RG")
    phone1        = get("Telefone Celular") or get("Telefone 1")
    phone2        = get("Telefone Residencial") or get("Telefone 2")
    email         = get("E-mail") or get("Email")
    endereco      = get("Endereço")
    numero        = get("Número")
    complemento   = get("Complemento")
    bairro        = get("Bairro")
    cidade        = get("Cidade")
    uf            = get("UF")
    cep           = get("CEP")
    modelo        = get("Modelo")
    valor_bem     = get("Valor do Bem Base*") or get("Valor do Bem Base")
    valor_parc    = get("Valor da Parcela")
    prazo         = get("Prazo")
    vencimento    = get("Dia Vencimento")
    tipo_cota     = get("Tipo de Cota").upper()
    plano         = get("Plano").upper()
    data_venda    = get("Data de Venda")

    nrecibo   = nrecibo_manual or ""
    nproposta = nproposta_manual or ""

    # Lookup vendedor pela matrícula
    vendedor = VENDEDORES.get(matricula.strip(), {})
    nome_vendedor = vendedor.get("nome", "")
    pdv           = vendedor.get("pdv", "")

    # Formato vendedor/código: PRIMEIRO ÚLTIMO - MATRÍCULA
    if nome_vendedor and matricula:
        vendedor_codigo = f"{nome_curto(nome_vendedor)} - {matricula}"
    else:
        vendedor_codigo = ""

    # CPF formatado
    c = re.sub(r'\D', '', cpf)
    cpf_fmt = f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else cpf

    # Telefones
    def fmt_ddd(p):
        d = re.sub(r'\D', '', p)
        return d[:2] if len(d) >= 2 else ""
    def fmt_tel(p):
        d = re.sub(r'\D', '', p)
        if len(d) == 11: return f"{d[2:7]}-{d[7:]}"
        if len(d) == 10: return f"{d[2:6]}-{d[6:]}"
        return p

    # Data nascimento
    ddn_parts = re.split(r'[/\-]', ddn)
    dia_nasc = ddn_parts[0].zfill(2) if len(ddn_parts) > 0 and ddn_parts[0] else ""
    mes_nasc = ddn_parts[1].zfill(2) if len(ddn_parts) > 1 and ddn_parts[1] else ""
    ano_nasc = ddn_parts[2] if len(ddn_parts) > 2 else ""

    # Endereço completo
    endereco_completo = endereco
    if numero:
        endereco_completo = f"{endereco}, {numero}"
    if complemento:
        endereco_completo += f" {complemento}"

    # Data de venda
    data_parts = re.split(r'[/\-]', data_venda)
    dia_venda     = data_parts[0].zfill(2) if len(data_parts) > 0 and data_parts[0] else ""
    mes_venda_num = data_parts[1].zfill(2) if len(data_parts) > 1 else ""
    ano_venda     = data_parts[2] if len(data_parts) > 2 else ""
    meses = {
        "01":"JANEIRO","02":"FEVEREIRO","03":"MARÇO","04":"ABRIL",
        "05":"MAIO","06":"JUNHO","07":"JULHO","08":"AGOSTO",
        "09":"SETEMBRO","10":"OUTUBRO","11":"NOVEMBRO","12":"DEZEMBRO"
    }
    mes_venda = meses.get(mes_venda_num, mes_venda_num.upper())

    local_assinatura = f"{cidade}-{uf}" if cidade and uf else cidade or ""

    # Estado civil
    ec_solteiro = "X" if "SOLTEIRO" in estado_civil else ""
    ec_casado   = "X" if "CASADO" in estado_civil and "DIVORCIADO" not in estado_civil else ""
    ec_div      = "X" if "DIVORCIADO" in estado_civil else ""
    ec_outros   = "X" if estado_civil and not any(x in estado_civil for x in ["SOLTEIRO","CASADO","DIVORCIADO"]) else ""

    # Cota
    cota_nova  = "X" if "NOVA" in tipo_cota else ""
    cota_repos = "X" if "REPOSI" in tipo_cota else ""

    # Plano
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
        "NOME":                   nome,
        "DIA":                    dia_nasc,
        "MÊS":                    mes_nasc,
        "ANO":                    ano_nasc,
        "NACIONALIDADE":          nac,
        "1":                      ec_solteiro,
        "2":                      ec_casado,
        "3":                      ec_div,
        "4":                      ec_outros,
        "PROFISSÃO":              profissao,
        "NÚMERO DO CPF":          cpf_fmt,
        "NÚMERO DE IDENTIDADERG": rg,
        "ORGÃO EMISSOR":          "",
        "DIA 2":                  "",
        "MÊS 2":                  "",
        "ANO 2":                  "",
        "ENDEREÇO":               endereco_completo,
        "BAIRRO":                 bairro,
        "CIDADE":                 cidade,
        "ESTADO":                 uf,
        "CEP":                    cep,
        "DDD 1":                  fmt_ddd(phone1),
        "TELEFONE 1":             fmt_tel(phone1),
        "TELEFONE 2":             phone2,
        "EMAIL":                  email,
        "NRECI":                  nrecibo,
        "NPROP":                  nproposta,
        "MODELO":                 modelo,
        "VALOR BASE DO BEM":      valor_bem,
        "VALOR DA PARCELA":       valor_parc,
        "QTD DE PARC":            prazo,
        "VENC DE PARCELA":        vencimento,
        "Texto2":                 cota_nova,
        "Texto3":                 cota_repos,
        "Texto4":                 "",
        "Texto5":                 "X",
        "CIDADE_WKMH":            local_assinatura,
        "DIA_0HVI":               dia_venda,
        "MES":                    mes_venda,
        "ANO_GXGT":               ano_venda,
        # Pág 2 e 6
        "Assinatura Cliente":     "",           # em branco
        "IDVE":                   vendedor_codigo,  # PRIMEIRO ÚLTIMO - MATRÍCULA
        "PDV":                    pdv,              # da lista
        "MAT":                    "",
        # Pág 3
        "autoriza a REVEMAR COMÉRCIO DE MOTOS LTDA CONCESSIONÁRIA a": "",
        "undefined":              "",
        "ANOM":                   "",
        # Pág 4
        "CIENTE DO PAGAMENTO DO FRETE NO VALOR DE R": "",
        "undefined_2":            "",
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

    pdf_file         = request.files["pdf"]
    dados_raw        = request.form["dados"]
    nproposta_manual = request.form.get("nproposta", "")
    nrecibo_manual   = request.form.get("nrecibo", "")
    matricula        = request.form.get("matricula", "")

    try:
        fields = parse_client_data(dados_raw, nproposta_manual, nrecibo_manual, matricula)
        reader = PdfReader(pdf_file)
        writer = PdfWriter()
        writer.append(reader)

        for page in writer.pages:
            writer.update_page_form_field_values(
                page, fields, auto_regenerate=False
            )

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        nome_arquivo = re.sub(r'[^a-zA-Z0-9_]', '_', fields.get("NOME", "documento"))
        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"REVEMAR_{nome_arquivo}.pdf"
        )

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/vendedor/<matricula>", methods=["GET"])
def get_vendedor(matricula):
    """Endpoint para o frontend consultar nome e PDV pela matrícula"""
    vendedor = VENDEDORES.get(matricula.strip())
    if vendedor:
        return jsonify({
            "matricula": matricula,
            "nome": vendedor["nome"],
            "nome_curto": nome_curto(vendedor["nome"]),
            "pdv": vendedor["pdv"]
        })
    return jsonify({"erro": "Matrícula não encontrada"}), 404

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

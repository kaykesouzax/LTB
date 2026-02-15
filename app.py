from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import io
import re
import os

app = Flask(__name__)
CORS(app)

# ─── Parser dos dados do cliente ──────────────────────────────────────────
def parse_client_data(raw: str) -> dict:
    def get(label):
        pattern = rf"{re.escape(label)}[:\s]*\n?([^\n]+)"
        match = re.search(pattern, raw, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    nome        = get("Nome")
    ddn         = get("Data de Nascimento")
    nac         = get("Nacionalidade")
    estado_civil = get("Estado Civil").upper()
    profissao   = get("Ocupação") or get("Profissão")
    cpf         = get("CPF")
    rg          = get("Número do Documento") or get("RG")
    phone1      = get("Telefone Celular") or get("Telefone 1")
    phone2      = get("Telefone Residencial") or get("Telefone 2")
    email       = get("E-mail") or get("Email")
    endereco    = get("Endereço")
    numero      = get("Número")
    bairro      = get("Bairro")
    cidade      = get("Cidade")
    uf          = get("UF")
    cep         = get("CEP")
    modelo      = get("Modelo")
    valor_bem   = get(r"Valor do Bem Base\*") or get("Valor do Bem Base")
    valor_parc  = get("Valor da Parcela")
    prazo       = get("Prazo")
    vencimento  = get("Dia Vencimento")
    tipo_cota   = get("Tipo de Cota").upper()
    plano       = get("Plano").upper()
    data_venda  = get("Data de Venda")

    # Formatar CPF
    c = re.sub(r'\D', '', cpf)
    if len(c) == 11:
        cpf_fmt = f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
    else:
        cpf_fmt = cpf

    # Formatar telefones
    def fmt_phone(p):
        digits = re.sub(r'\D', '', p)
        if len(digits) == 11:
            return digits[:2], f"{digits[2:7]}-{digits[7:]}"
        if len(digits) == 10:
            return digits[:2], f"{digits[2:6]}-{digits[6:]}"
        return "", p

    ddd1, tel1 = fmt_phone(phone1)
    _, tel2_full = fmt_phone(phone2)

    # Dia/mês/ano nascimento
    ddn_parts = re.split(r'[/\-]', ddn)
    dia_nasc = ddn_parts[0] if len(ddn_parts) > 0 else ""
    mes_nasc = ddn_parts[1] if len(ddn_parts) > 1 else ""
    ano_nasc = ddn_parts[2] if len(ddn_parts) > 2 else ""

    # Endereço + número
    endereco_completo = f"{endereco}, {numero}" if numero else endereco

    # Data de venda para local/data
    data_parts = re.split(r'[/\-]', data_venda)
    dia_venda = data_parts[0] if len(data_parts) > 0 else "14"
    mes_venda_num = data_parts[1] if len(data_parts) > 1 else "02"
    ano_venda = data_parts[2] if len(data_parts) > 2 else "2026"
    meses = {"01":"janeiro","02":"fevereiro","03":"março","04":"abril","05":"maio",
             "06":"junho","07":"julho","08":"agosto","09":"setembro",
             "10":"outubro","11":"novembro","12":"dezembro"}
    mes_venda = meses.get(mes_venda_num, mes_venda_num)

    # Estado civil checkbox
    ec_solteiro = "X" if "SOLTEIRO" in estado_civil else ""
    ec_casado   = "X" if "CASADO" in estado_civil and "DIVORCIADO" not in estado_civil else ""
    ec_div      = "X" if "DIVORCIADO" in estado_civil else ""
    ec_outros   = "X" if estado_civil and not any(x in estado_civil for x in ["SOLTEIRO","CASADO","DIVORCIADO"]) else ""

    # Tipo de cota checkbox
    cota_nova   = "X" if "NOVA" in tipo_cota else ""
    cota_repos  = "X" if "REPOSI" in tipo_cota else ""

    # Plano — mapeamento para campo Texto
    plano_map = {
        "SUPER LEGAL": "Texto6", "MULTICHANCES": "Texto7",
        "VOU DE HONDA +": "Texto8", "MINHA SCOOTER HONDA+": "Texto9",
        "#VOU DE HONDA+": "Texto10", "NORMAL": "Texto11",
        "MEGA FÁCIL": "Texto12", "CONQUISTA": "Texto13",
        "VOU DE HONDA": "Texto14", "MINHA SCOOTER HONDA": "Texto15",
        "#VOU DE HONDA": "Texto16", "TRX/CRF": "Texto17",
        "ESPECIAL": "Texto18", "MASTER": "Texto19", "ADVANCE": "Texto20",
    }
    plano_field = plano_map.get(plano, "Texto18")

    return {
        "NOME": nome,
        "DIA": dia_nasc,
        "MÊS": mes_nasc,
        "ANO": ano_nasc,
        "NACIONALIDADE": nac,
        "1": ec_solteiro,
        "2": ec_casado,
        "3": ec_div,
        "4": ec_outros,
        "PROFISSÃO": profissao,
        "NÚMERO DO CPF": cpf_fmt,
        "NÚMERO DE IDENTIDADERG": rg,
        "ORGÃO EMISSOR": "SSP",
        "ENDEREÇO": endereco_completo,
        "BAIRRO": bairro,
        "CIDADE": cidade,
        "ESTADO": uf,
        "CEP": cep,
        "DDD 1": ddd1,
        "TELEFONE 1": tel1,
        "TELEFONE 2": phone2,
        "EMAIL": email,
        "MODELO": modelo,
        "VALOR BASE DO BEM": valor_bem,
        "VALOR DA PARCELA": valor_parc,
        "QTD DE PARC": prazo,
        "VENC DE PARCELA": vencimento,
        "Texto2": cota_nova,
        "Texto3": cota_repos,
        "Texto4": "",   # COM SEGURO
        "Texto5": "X",  # SEM SEGURO (padrão)
        plano_field: "X",
        "CIDADE_WKMH": cidade,
        "DIA_0HVI": dia_venda,
        "MES": mes_venda,
        "ANO_GXGT": ano_venda,
        "autoriza a REVEMAR COMÉRCIO DE MOTOS LTDA CONCESSIONÁRIA a": "",
        "undefined": modelo,
    }

# ─── Rota principal ────────────────────────────────────────────────────────
@app.route("/preencher", methods=["POST"])
def preencher():
    if "pdf" not in request.files:
        return jsonify({"erro": "PDF não enviado"}), 400
    if "dados" not in request.form:
        return jsonify({"erro": "Dados do cliente não enviados"}), 400

    pdf_file = request.files["pdf"]
    dados_raw = request.form["dados"]

    try:
        fields = parse_client_data(dados_raw)

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

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

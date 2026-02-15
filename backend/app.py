from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import io
import re
import os

app = Flask(__name__)
CORS(app)

def parse_client_data(raw: str, nproposta_manual="", nrecibo_manual="") -> dict:
    def get(label):
        # Busca label com : e valor na PRÓXIMA linha (para evitar pegar texto do label seguinte)
        pattern = rf"^{re.escape(label)}:\s*\n([^\n]+)"
        match = re.search(pattern, raw, re.IGNORECASE | re.MULTILINE)
        if match:
            val = match.group(1).strip()
            # Rejeitar se o valor parece ser um label (termina com : ou é linha em branco)
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
    nome_vendedor = get("Nome do vendedor") or get("Vendedor")
    codigo_vend   = get("Código") or get("Codigo")
    concessionaria = get("Concessionária") or get("Concessionaria")

    nrecibo   = nrecibo_manual or get("Número Recibo") or ""
    nproposta = nproposta_manual or get("Número Proposta") or ""

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

    # Local = Cidade-UF
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

    # Pág 2 e 6: linha acima = CODIGO- NOME, linha abaixo = só código
    vendedor_linha1 = f"{codigo_vend}- {nome_vendedor}" if codigo_vend and nome_vendedor else codigo_vend or nome_vendedor or ""

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
        # Pág 2/6 - vendedor
        "Assinatura Cliente":     vendedor_linha1,
        "IDVE":                   codigo_vend,
        "PDV":                    cidade,
        "MAT":                    "",
        # Pág 3 - grupo/cota/rd em branco
        "autoriza a REVEMAR COMÉRCIO DE MOTOS LTDA CONCESSIONÁRIA a": "",
        "undefined":              "",
        "ANOM":                   "",
        # Pág 4 - não preencher
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

    try:
        fields = parse_client_data(dados_raw, nproposta_manual, nrecibo_manual)
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

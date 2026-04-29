import re


def mask_cpf(cpf: str) -> str:
    """
    Mascara um CPF para exibição segura ao cliente.

    Exemplos:
        "12345678901"    -> "123.***.***-01"
        "123.456.789-01" -> "123.***.***-01"
        ""               -> ""   (retorna vazio sem erro)
    """
    if not cpf:
        return cpf

    digits = re.sub(r"\D", "", cpf)

    if len(digits) != 11:
        # Se não tem 11 dígitos, não é um CPF reconhecível — retorna sem expor
        return "***.***.***-**"

    return f"{digits[:3]}.***.***-{digits[9:]}"


def mask_cpf_in_text(text: str) -> str:
    """
    Substitui qualquer padrão de CPF encontrado em um texto por versão mascarada.
    Útil como salvaguarda antes de enviar qualquer mensagem ao cliente.

    Formatos reconhecidos:
        123.456.789-01  (com pontuação)
        12345678901     (somente dígitos, 11 seguidos)
    """
    # Formato com pontuação: 000.000.000-00
    text = re.sub(
        r"\b(\d{3})\.\d{3}\.\d{3}-(\d{2})\b",
        r"\1.***.***-\2",
        text,
    )
    # Formato somente dígitos: 00000000000 (11 dígitos consecutivos)
    # Exige que não seja precedido/seguido por outro dígito (evita mascarar telefones)
    text = re.sub(
        r"(?<!\d)(\d{3})\d{5}(\d{3})(?!\d)",
        r"\1*****\2",
        text,
    )
    return text

import re

from django.core.exceptions import ValidationError


def validar_telefono_chileno(valor):
    if not valor:
        return
    if not isinstance(valor, str):
        raise ValidationError(
            "Ingresa un teléfono chileno válido.",
            code="invalid_phone",
        )
    telefono = valor.strip()
    if not re.fullmatch(
        r"(?:\+?56|0056)?[ .-]?(?:[2-9]|\([2-9]\))(?:[ .-]?\d){8}",
        telefono,
    ):
        raise ValidationError(
            "Ingresa un teléfono chileno válido.",
            code="invalid_phone",
        )


def normalizar_telefono_chileno(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise ValidationError(
            "Ingresa un teléfono chileno válido.",
            code="invalid_phone",
        )

    telefono = valor.strip()
    validar_telefono_chileno(telefono)
    digitos = re.sub(r"\D", "", telefono)
    if digitos.startswith("0056"):
        digitos = digitos[4:]
    elif digitos.startswith("56") and len(digitos) == 11:
        digitos = digitos[2:]

    if len(digitos) != 9:
        raise ValidationError(
            "Ingresa un teléfono chileno válido.",
            code="invalid_phone",
        )

    return f"+56{digitos}"

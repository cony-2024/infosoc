import re

from django.core.exceptions import ValidationError


def normalizar_rut(valor):
    if not isinstance(valor, str):
        raise ValidationError("Ingresa un RUT válido.")

    match = re.fullmatch(
        r"((?:\d{1,2}(?:\.\d{3}){0,2})|\d{1,8})-?([\dK])",
        valor.strip().upper(),
    )
    if not match:
        raise ValidationError("Ingresa un RUT válido.")

    cuerpo, digito_ingresado = match.groups()
    cuerpo = cuerpo.replace(".", "")
    suma = sum(
        int(digito) * (indice % 6 + 2)
        for indice, digito in enumerate(reversed(cuerpo))
    )
    resultado = 11 - suma % 11
    digito_esperado = "0" if resultado == 11 else "K" if resultado == 10 else str(resultado)
    if digito_ingresado != digito_esperado:
        raise ValidationError("El dígito verificador del RUT no es válido.")

    return f"{cuerpo}-{digito_esperado}"


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

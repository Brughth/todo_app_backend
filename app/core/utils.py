import pycountry
import phonenumbers
from pydantic import ValidationError


def validate_phone_fields(
    code: str | None,
    numeric: str | None,
    phone: str | None,
) -> None:
    """
    Validates that the phone fields are either all provided together or all empty.
    If provided, it checks that the country code is valid, the numeric code matches the country code, and that the full phone number is valid for the given country.
    Compatible with both Pydantic's ValidationError and ValueError for flexibility in different contexts.
    """
    fields = [code, numeric, phone]

    # Tous vides = ok (téléphone optionnel)
    if not any(fields):
        return

    # Partiellement rempli = erreur
    if not all(fields):
        raise ValueError(
            "'phone_number', 'phone_country_code' and 'phone_country_number' "
            "must be provided together"
        )

    # Vérifier le code pays
    country = pycountry.countries.get(alpha_2=code.upper())
    if not country:
        raise ValueError(f"Invalid country code: {code}")

    # Vérifier l'indicatif
    expected_numeric = phonenumbers.country_code_for_region(code.upper())
    expected_str = f'+{expected_numeric}'
    if numeric != expected_str:
        raise ValueError(
            f"Invalid phone country number: {numeric} "
            f"for country code: {code} (expected: {expected_str})"
        )

    # Vérifier le numéro complet
    full_number = f'{numeric}{phone}'
    try:
        parsed = phonenumbers.parse(full_number, code.upper())
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number: {phone} for country: {code}")
    except phonenumbers.NumberParseException:
        raise ValueError(
            f"Invalid phone number {numeric}{phone} for country {country.name}"
        )
"""Rules for passwords selected during enrollment or a future password change."""

from app.modules.p1_gestion_identidad_seguridad.exceptions import WeakPasswordError

PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128

# Compact MVP blocklist: high-frequency, patterned, and Socratia-specific values that still meet
# the minimum length. It is deliberately checked as a whole value rather than as substrings.
COMMON_PASSWORDS = frozenset(
    {
        "111111111111111",
        "123456789012345",
        "123456789123456",
        "abcdefghijklmnop",
        "adminadminadmin",
        "contraseñacontraseña",
        "contrasena123456",
        "iloveyouiloveyou",
        "letmeinletmeinletmein",
        "miclavesegura123",
        "password123456",
        "password123456789",
        "passwordpassword",
        "passwordpassword1",
        "qwertyqwertyqwerty",
        "qwertyuiopasdfgh",
        "socratia12345678",
        "socratiapassword",
        "welcome123456789",
    }
)

SEQUENCES = (
    "0123456789",
    "1234567890",
    "abcdefghijklmnopqrstuvwxyz",
    "qwertyuiopasdfghjklzxcvbnm",
)

CONTEXT_SUFFIXES = ("1", "123", "1234", "12345", "123456", "2026", "!", "1!")


def validate_new_password(password: str, *, email: str, full_name: str) -> str:
    """Validate without trimming or otherwise rewriting the submitted secret."""

    if len(password) < PASSWORD_MIN_LENGTH:
        raise WeakPasswordError(
            f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise WeakPasswordError(
            f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres."
        )

    comparable = password.casefold()
    if (
        comparable in COMMON_PASSWORDS
        or _is_repeated_pattern(comparable)
        or _is_repeated_sequence(comparable)
        or comparable in _context_blocklist(email, full_name)
    ):
        raise WeakPasswordError(
            "Esta contraseña es demasiado común o predecible. "
            "Elige una frase más difícil de adivinar."
        )
    return password


def _is_repeated_pattern(value: str) -> bool:
    for pattern_length in range(1, min(8, len(value) // 2 + 1)):
        if len(value) % pattern_length == 0:
            pattern = value[:pattern_length]
            if pattern * (len(value) // pattern_length) == value:
                return True
    return False


def _is_repeated_sequence(value: str) -> bool:
    for sequence in SEQUENCES:
        repetitions = len(value) // len(sequence) + 2
        repeated = sequence * repetitions
        if value in repeated or value in repeated[::-1]:
            return True
    return False


def _context_blocklist(email: str, full_name: str) -> set[str]:
    local_part = email.partition("@")[0]
    context_values = {
        "socratia",
        email.casefold(),
        local_part.casefold(),
        full_name.casefold(),
        "".join(character for character in full_name.casefold() if character.isalnum()),
    }
    blocked: set[str] = set()
    for value in context_values:
        if len(value) < 3:
            continue
        blocked.add(value)
        for suffix in CONTEXT_SUFFIXES:
            blocked.add(f"{value}{suffix}")
            blocked.add(f"{value}-{suffix}")
    return blocked

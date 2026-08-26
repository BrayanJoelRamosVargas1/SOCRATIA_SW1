export const PASSWORD_MIN_LENGTH = 15;
export const PASSWORD_MAX_LENGTH = 128;

const COMMON_PASSWORDS = new Set([
  "111111111111111",
  "123456789012345",
  "abcdefghijklmnop",
  "adminadminadmin",
  "contrasena123456",
  "password123456",
  "password123456789",
  "passwordpassword",
  "passwordpassword1",
  "qwertyqwertyqwerty",
  "qwertyuiopasdfgh",
  "socratia12345678",
  "socratiapassword",
]);

const LABELS = ["Sin evaluar", "Débil", "Aceptable", "Buena", "Fuerte"] as const;

export type PasswordStrength = {
  score: number;
  label: (typeof LABELS)[number];
  acceptable: boolean;
  predictable: boolean;
};

export function countPasswordCharacters(password: string): number {
  return Array.from(password).length;
}

export function analyzePassword(password: string): PasswordStrength {
  if (!password) {
    return { score: 0, label: LABELS[0], acceptable: false, predictable: false };
  }

  const comparable = password.toLocaleLowerCase();
  const predictable = COMMON_PASSWORDS.has(comparable) || isRepeatedPattern(comparable);
  const characterCount = countPasswordCharacters(password);
  const acceptable = characterCount >= PASSWORD_MIN_LENGTH && !predictable;
  if (!acceptable) {
    return { score: 1, label: LABELS[1], acceptable, predictable };
  }

  const characterGroups = [/[a-záéíóúñ]/u, /[A-ZÁÉÍÓÚÑ]/u, /\d/u, /[^\p{L}\p{N}]/u].filter(
    (pattern) => pattern.test(password),
  ).length;
  const wordCount = password.split(/\s+/u).filter(Boolean).length;
  let score = characterCount >= 28 ? 4 : characterCount >= 20 ? 3 : 2;
  if (score < 4 && (wordCount >= 4 || characterGroups >= 3)) {
    score += 1;
  }
  return { score, label: LABELS[score], acceptable, predictable };
}

export function hasBoundarySpace(password: string): boolean {
  return password.startsWith(" ") || password.endsWith(" ");
}

function isRepeatedPattern(value: string): boolean {
  for (let patternLength = 1; patternLength <= Math.min(7, value.length / 2); patternLength += 1) {
    if (value.length % patternLength === 0) {
      const pattern = value.slice(0, patternLength);
      if (pattern.repeat(value.length / patternLength) === value) {
        return true;
      }
    }
  }
  return false;
}

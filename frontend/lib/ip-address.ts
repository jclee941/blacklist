export function formatIPv4Input(value: string): string {
  const sanitized = value.replace(/[^\d.]/g, '');
  if (sanitized.includes('.')) {
    return sanitized
      .split('.')
      .slice(0, 4)
      .map((part) => part.slice(0, 3))
      .join('.');
  }

  const digits = sanitized.slice(0, 12);
  return digits.match(/.{1,3}/g)?.join('.') ?? '';
}

export function isValidIPv4(value: string): boolean {
  const parts = value.split('.');
  return (
    parts.length === 4 &&
    parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) >= 0 && Number(part) <= 255)
  );
}

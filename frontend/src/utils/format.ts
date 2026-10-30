import { Candidate } from '../types';

const pad = (n: number): string => String(n).padStart(2, '0');
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "+919876543210" -> "+91 9876543210" (matches the Figma table) */
export function formatPhone(e164: string = ''): string {
  if (e164.startsWith('+91') && e164.length === 13) return `+91 ${e164.slice(3)}`;
  return e164;
}

/** ISO -> "12-10-2026" */
export function formatDate(iso?: string | null): string {
  if (!iso) return 'NA';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return 'NA';
  return `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()}`;
}

/** ISO -> "08 Oct 2026, 10:30 AM" */
export function formatDateTime(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const h = d.getHours();
  return `${pad(d.getDate())} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${pad(h % 12 || 12)}:${pad(d.getMinutes())} ${h < 12 ? 'AM' : 'PM'}`;
}

/** Date -> value for <input type="datetime-local"> in local time */
export function toLocalInputValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export const plural = (n: number, one: string, many: string = `${one}s`): string =>
  `${n} ${n === 1 ? one : many}`;

export const firstName = (name: string = ''): string =>
  name.trim().split(/\s+/)[0] || '';

/** Strips non-digits from phone number and creates a WhatsApp direct link */
export function getWhatsAppShareUrl(phone: string = '', text: string = ''): string {
  const digits = phone.replace(/[^0-9]/g, '');
  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
}

/** Generates a standard mailto: URL */
export function getMailtoShareUrl(email: string = '', subject: string = '', body: string = ''): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

/** Mirrors the backend renderer so the UI can preview personalised text. */
export function renderPreview(body: string, candidate: Partial<Candidate> & { name: string }): string {
  const values: Record<string, string> = {
    name: candidate.name,
    first_name: firstName(candidate.name),
    phone: candidate.phone || '',
    email: candidate.email || '',
    candidate_id: candidate.code || '',
  };
  return body.replace(/\{\{\s*([A-Za-z_]+)\s*\}\}/g, (m, k) => (k in values ? values[k] : m));
}


import { describe, expect, it } from 'vitest';
import {
  formatDate,
  formatDateTime,
  formatPhone,
  getMailtoShareUrl,
  getWhatsAppShareUrl,
  plural,
  renderPreview,
} from '../utils/format';
import { isActive, STATUS } from '../utils/status';
import { countVisible } from '../components/RecipientChips';

describe('format', () => {
  it('formats Indian numbers like the design', () => {
    expect(formatPhone('+919876543210')).toBe('+91 9876543210');
  });
  it('leaves other numbers alone', () => {
    expect(formatPhone('+442071838750')).toBe('+442071838750');
  });
  it('shows NA for a missing date', () => {
    expect(formatDate(null)).toBe('NA');
  });
  it('formats DD-MM-YYYY', () => {
    expect(formatDate(new Date(2026, 9, 8, 10, 30).toISOString())).toBe('08-10-2026');
  });
  it('formats history timestamps', () => {
    expect(formatDateTime(new Date(2026, 9, 8, 10, 30).toISOString())).toBe('08 Oct 2026, 10:30 AM');
  });
  it('pluralises', () => {
    expect(plural(1, 'Recipient')).toBe('1 Recipient');
    expect(plural(5, 'Recipient')).toBe('5 Recipients');
  });
  it('previews placeholders and keeps unknown ones', () => {
    const c = { name: 'Rahul Sharma', phone: '+91', email: '', code: 'A1B2C3' };
    expect(renderPreview('Hi {{first_name}} ({{candidate_id}}) {{nope}}', c)).toBe(
      'Hi Rahul (A1B2C3) {{nope}}'
    );
  });
  it('generates real WhatsApp direct sharing URL', () => {
    expect(getWhatsAppShareUrl('+91 98765 43210', 'Hi Rahul!')).toBe(
      'https://wa.me/919876543210?text=Hi%20Rahul!'
    );
  });
  it('generates real mailto direct sharing URL', () => {
    expect(getMailtoShareUrl('rahul@example.com', 'Job Offer', 'Hi Rahul')).toBe(
      'mailto:rahul@example.com?subject=Job%20Offer&body=Hi%20Rahul'
    );
  });
});

describe('status', () => {
  it('knows every status the API can send', () => {
    (['scheduled', 'queued', 'sending', 'sent', 'delivered', 'read', 'failed', 'cancelled'] as const).forEach(
      (s) => expect(STATUS[s]).toBeTruthy()
    );
  });
  it('only polls while a status can still change', () => {
    expect(isActive('sent')).toBe(true);
    expect(isActive('read')).toBe(false);
    expect(isActive('failed')).toBe(false);
  });
});

describe('countVisible (two-line recipient chips)', () => {
  it('shows everything when it fits', () => {
    expect(countVisible([100, 100, 100], 400, 50)).toBe(3);
  });
  it('collapses to fit two lines plus the +n chip', () => {
    const widths = Array(20).fill(100);
    const n = countVisible(widths, 320, 50);
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThan(20);
    expect(n).toBeLessThanOrEqual(5);
  });
  it('handles no recipients', () => {
    expect(countVisible([], 300, 50)).toBe(0);
  });
});


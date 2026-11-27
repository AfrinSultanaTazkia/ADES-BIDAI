/**
 * ADES BIDAI — Bangla-First Utility Functions
 * Supports 100% offline numerical and terminology conversion for government health dashboard.
 */

const BN_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];

/**
 * Converts English numbers or strings with digits to Bengali numerals.
 * Handles comma formatting, decimals, and null/undefined values.
 */
export function toBangla(value, decimals = null) {
  if (value === null || value === undefined || value === '') return '০';

  let num = Number(value);
  if (isNaN(num)) {
    // If it's a string with digits, replace each digit
    return String(value).replace(/[0-9]/g, (d) => BN_DIGITS[d]);
  }

  let formatted;
  if (decimals !== null && typeof decimals === 'number') {
    formatted = num.toFixed(decimals);
  } else {
    // Format with commas for thousands
    if (Number.isInteger(num)) {
      formatted = num.toLocaleString('en-US');
    } else {
      formatted = String(num);
    }
  }

  return formatted.replace(/[0-9]/g, (d) => BN_DIGITS[d]);
}

/**
 * Translates risk tier strings to standardized official Bangla labels.
 */
export function translateRisk(risk) {
  if (!risk) return 'অনির্ধারিত';
  const r = String(risk).trim().toLowerCase();
  if (r.includes('high') || r.includes('চরম') || r.includes('উচ্চ')) {
    return 'চরম ঝুঁকিপূর্ণ';
  }
  if (r.includes('medium') || r.includes('মাঝারি')) {
    return 'মাঝারি ঝুঁকিপূর্ণ';
  }
  if (r.includes('low') || r.includes('কম')) {
    return 'কম ঝুঁকিপূর্ণ';
  }
  if (r.includes('critical') || r.includes('সংকট')) {
    return 'সংকটজনক ঝুঁকি';
  }
  return risk;
}

/**
 * Translates City Corporation names to standardized official Bangla labels.
 */
export function translateCity(city) {
  if (!city) return 'সব সিটি কর্পোরেশন';
  const c = String(city).trim().toLowerCase();
  if (c.includes('north') || c.includes('dncc')) return 'ঢাকা উত্তর সিটি কর্পোরেশন';
  if (c.includes('south') || c.includes('dscc')) return 'ঢাকা দক্ষিণ সিটি কর্পোরেশন';
  if (c.includes('chattogram') || c.includes('ctg') || c.includes('ccc')) return 'চট্টগ্রাম সিটি কর্পোরেশন';
  if (c.includes('gazipur') || c.includes('gcc')) return 'গাজীপুর সিটি কর্পোরেশন';
  if (c.includes('narayanganj') || c.includes('ncc')) return 'নারায়ণগঞ্জ সিটি কর্পোরেশন';
  return city;
}

/**
 * Translates resource types to official Bangla labels.
 */
export function translateResource(resource) {
  if (!resource) return '';
  const res = String(resource).trim().toLowerCase();
  if (res.includes('saline')) return 'আইভি স্যালাইন ব্যাগ';
  if (res.includes('kit') || res.includes('diagnostic')) return 'ডেঙ্গু টেস্ট কিট';
  if (res.includes('bed')) return 'হাসপাতাল শয্যা';
  if (res.includes('crew') || res.includes('spray')) return 'মশক নিধন দল';
  return resource;
}

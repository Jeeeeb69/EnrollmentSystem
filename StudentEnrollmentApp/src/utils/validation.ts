const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const nameRegex = /^[A-Za-z][A-Za-z .'-]*$/;
const studentNumberRegex = /^[A-Za-z0-9-]{4,50}$/;
const phoneRegex = /^\+?[0-9][0-9 -]{6,18}$/;
const subjectCodeRegex = /^[A-Za-z0-9-]{2,20}$/;
const sectionRegex = /^[A-Za-z0-9-]{1,50}$/;

export const courses = [
  "Information Technology",
  "Computer Science",
  "Technology Communication Management",
] as const;

export const yearLevels = [
  "1st Year",
  "2nd Year",
  "3rd Year",
  "4th Year",
] as const;

export const semesters = ["1st Sem", "2nd Sem"] as const;

export function cleanText(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

export function validateEmail(email: string) {
  const cleanEmail = email.trim().toLowerCase();

  if (!cleanEmail) {
    return "Email is required.";
  }

  if (!emailRegex.test(cleanEmail)) {
    return "Enter a valid email address.";
  }

  return "";
}

export function validatePassword(password: string) {
  if (!password) {
    return "Password is required.";
  }

  if (password.length < 8) {
    return "Password must be at least 8 characters.";
  }

  if (/^\d+$/.test(password)) {
    return "Password cannot be entirely numeric.";
  }

  if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    return "Password must include letters and numbers.";
  }

  const lowerPassword = password.toLowerCase();
  const commonPasswords = [
    "password",
    "password123",
    "password1234",
    "qwerty123",
    "admin123",
    "welcome123",
    "letmein123",
    "rhean123",
  ];

  if (
    commonPasswords.includes(lowerPassword) ||
    lowerPassword.includes("password")
  ) {
    return "Password is too common. Use a more unique password.";
  }

  return "";
}

export function validateName(value: string, label: string, required = true) {
  const cleanValue = cleanText(value);

  if (!cleanValue) {
    return required ? `${label} is required.` : "";
  }

  if (!nameRegex.test(cleanValue)) {
    return `${label} may only contain letters, spaces, apostrophes, periods, and hyphens.`;
  }

  return "";
}

export function validateStudentNumber(value: string) {
  const cleanValue = cleanText(value).toUpperCase();

  if (!cleanValue) {
    return "Student number is required.";
  }

  if (!studentNumberRegex.test(cleanValue)) {
    return "Student number must be 4-50 characters and use only letters, numbers, and hyphens.";
  }

  return "";
}

export function validatePhone(value: string) {
  const cleanValue = cleanText(value);

  if (cleanValue && !phoneRegex.test(cleanValue)) {
    return "Contact number must be 7-19 digits and may include spaces, hyphens, or a leading plus.";
  }

  return "";
}

export function validateBirthday(value: string) {
  if (!value) {
    return "";
  }

  const birthday = new Date(`${value}T00:00:00`);
  const today = new Date();
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());

  if (Number.isNaN(birthday.getTime())) {
    return "Enter a valid birthday.";
  }

  if (birthday > todayOnly) {
    return "Birthday cannot be in the future.";
  }

  let age = todayOnly.getFullYear() - birthday.getFullYear();
  const hadBirthdayThisYear =
    todayOnly.getMonth() > birthday.getMonth() ||
    (todayOnly.getMonth() === birthday.getMonth() &&
      todayOnly.getDate() >= birthday.getDate());

  if (!hadBirthdayThisYear) {
    age -= 1;
  }

  if (age < 15) {
    return "Student must be at least 15 years old.";
  }

  if (age > 100) {
    return "Birthday is outside the allowed range.";
  }

  return "";
}

export function validateSubjectCode(value: string) {
  const cleanValue = cleanText(value).toUpperCase();

  if (!cleanValue) {
    return "Subject code is required.";
  }

  if (!subjectCodeRegex.test(cleanValue)) {
    return "Subject code must be 2-20 characters and use only letters, numbers, and hyphens.";
  }

  return "";
}

export function validateUnits(value: string) {
  const numberValue = Number(value);

  if (!value.trim()) {
    return "Units are required.";
  }

  if (!Number.isInteger(numberValue) || numberValue < 1 || numberValue > 6) {
    return "Units must be a whole number between 1 and 6.";
  }

  return "";
}

export function validateSectionName(value: string) {
  const cleanValue = cleanText(value).toUpperCase();

  if (!cleanValue) {
    return "Section name is required.";
  }

  if (!sectionRegex.test(cleanValue)) {
    return "Section name must use only letters, numbers, and hyphens.";
  }

  return "";
}

export function validateCapacity(value: string) {
  const numberValue = Number(value);

  if (!value.trim()) {
    return "Max capacity is required.";
  }

  if (!Number.isInteger(numberValue) || numberValue < 1 || numberValue > 100) {
    return "Max capacity must be a whole number between 1 and 100.";
  }

  return "";
}

export function firstValidationError(errors: string[]) {
  return errors.find(Boolean) || "";
}

export function getApiErrorMessage(data: any, fallback: string) {
  if (!data) {
    return fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  if (data.error || data.detail) {
    return data.error || data.detail;
  }

  const firstValue = Object.values(data)[0];

  if (Array.isArray(firstValue)) {
    return String(firstValue[0]);
  }

  if (typeof firstValue === "string") {
    return firstValue;
  }

  return fallback;
}

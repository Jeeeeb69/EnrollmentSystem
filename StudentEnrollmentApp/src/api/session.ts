import { api } from "./api";

export interface CurrentUser {
  id: number;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  email_verified: boolean;
}

export async function getCurrentUser() {
  const response = await api.get<CurrentUser>("auth/me/");

  return response.data;
}

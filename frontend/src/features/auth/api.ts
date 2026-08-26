import { apiRequest } from "@/lib/api";
import type { User } from "@/types/user";

type AuthResponse = { user: User };

export type RegisterInput = {
  full_name: string;
  email: string;
  password: string;
};

export type LoginInput = {
  email: string;
  password: string;
};

export async function register(input: RegisterInput): Promise<User> {
  const response = await apiRequest<AuthResponse>(
    "/auth/register",
    { method: "POST", body: JSON.stringify(input) },
    false,
  );
  return response.user;
}

export async function login(input: LoginInput): Promise<User> {
  const response = await apiRequest<AuthResponse>(
    "/auth/login",
    { method: "POST", body: JSON.stringify(input) },
    false,
  );
  return response.user;
}

export async function logout(): Promise<void> {
  await apiRequest("/auth/logout", { method: "POST" }, false);
}

export function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/users/me");
}


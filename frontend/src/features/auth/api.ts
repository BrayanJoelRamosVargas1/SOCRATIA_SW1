import { apiRequest } from "@/lib/api";
import type { User } from "@/types/user";

type AuthResponse = { user: User };
type MessageResponse = { message: string };

export type RegisterInput = {
  full_name: string;
  email: string;
  password: string;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type ResetPasswordInput = {
  token: string;
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

export async function forgotPassword(email: string): Promise<string> {
  const response = await apiRequest<MessageResponse>(
    "/auth/forgot-password",
    { method: "POST", body: JSON.stringify({ email }) },
    false,
  );
  return response.message;
}

export async function resetPassword(input: ResetPasswordInput): Promise<string> {
  const response = await apiRequest<MessageResponse>(
    "/auth/reset-password",
    { method: "POST", body: JSON.stringify(input) },
    false,
  );
  return response.message;
}

export async function logout(): Promise<void> {
  await apiRequest("/auth/logout", { method: "POST" }, false);
}

export function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/users/me");
}

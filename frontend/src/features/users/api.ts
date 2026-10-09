import { apiRequest } from "@/lib/api";
import type { User } from "@/types/user";

export async function updateProfile(data: { full_name?: string; bio?: string }): Promise<User> {
  return apiRequest<User>("/profile", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

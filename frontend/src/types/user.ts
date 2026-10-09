export type User = {
  id: string;
  email: string;
  full_name: string;
  bio?: string | null;
  is_active: boolean;
  roles: string[];
  created_at: string;
};


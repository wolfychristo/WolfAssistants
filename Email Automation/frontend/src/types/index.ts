export interface TrialInfo {
  is_active: boolean;
  days_remaining: number;
  has_expired: boolean;
  start_date: string | null;
  end_date: string | null;
}

export interface User {
  id: number;
  email: string;
  name?: string;
  full_name?: string | null;
  profile_image_url?: string | null;
  businessName?: string;
  company_name?: string | null;
  createdAt?: string;
  updatedAt?: string;
  created_at?: string;
  updated_at?: string | null;
  is_admin?: boolean;
  pricing_tier?: string;
  payment_status?: string;
  is_active?: boolean;
  deleted_at?: string | null;
  deletion_reason?: string | null;
  trial?: TrialInfo;
}

export interface Todo {
  id: number;
  title: string;
  description?: string | null;
  completed: boolean;
  due_date?: string | null;
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  updated_at?: string | null;
  owner_email: string;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  deleted_users: number;
  new_signups_today: number;
  new_signups_this_week: number;
  new_signups_this_month: number;
  deletion_reasons: Record<string, number>;
  tier_distribution: Record<string, number>;
  recent_signups: Array<{
    id: number;
    email: string;
    full_name: string | null;
    company_name: string | null;
    pricing_tier: string;
    created_at: string;
    is_active: boolean;
  }>;
  recent_deletions: Array<{
    id: number;
    email: string;
    full_name: string | null;
    company_name: string | null;
    deletion_reason: string | null;
    deleted_at: string | null;
    feedback_category?: string | null;
    feedback_custom_category?: string | null;
    feedback_rating?: number | null;
    feedback_details?: string | null;
  }>;
  feedback_categories: Record<string, number>;
  average_feedback_rating: number;
  feedback_insights: {
    total_feedback_responses: number;
    most_common_category: string | null;
    lowest_rated_category: string | null;
    contact_consent_rate: number;
  };
  admin_users: number;
}

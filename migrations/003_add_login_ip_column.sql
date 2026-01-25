-- Database Migration Script for Login IP Tracking
-- Run this in your Supabase SQL Editor

-- Add column to track user's last login IP address
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(45);

-- Add column to track last login timestamp (optional but useful)
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;

-- Create index for IP-based lookups (useful for security audits)
CREATE INDEX IF NOT EXISTS idx_users_last_login_ip ON users(last_login_ip);

-- ===========================================
-- IATRS - Intelligent Applicant Tracking System
-- Complete Database Schema
-- ===========================================

CREATE DATABASE IF NOT EXISTS iatrs;
USE iatrs;

-- Recruiters Table
CREATE TABLE IF NOT EXISTS recruiters (
    recruiter_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    company VARCHAR(150) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_recruiters_email (email),
    INDEX idx_recruiters_company (company)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Jobs Table (Enhanced)
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    requirements TEXT,
    department VARCHAR(100) NOT NULL,
    location VARCHAR(120) NOT NULL,
    work_mode ENUM('Remote', 'Hybrid', 'Onsite') DEFAULT 'Hybrid',
    
    -- Salary
    min_salary INT,
    max_salary INT,
    salary_currency VARCHAR(10) DEFAULT 'USD',
    salary_period VARCHAR(20) DEFAULT 'YEAR',
    
    -- Skills
    required_skills TEXT,
    preferred_skills TEXT,
    
    -- Experience
    min_experience_years INT,
    max_experience_years INT,
    
    -- Education
    education_level VARCHAR(50),
    
    -- Status & Metadata
    status ENUM('Open', 'Closed', 'Paused') DEFAULT 'Open',
    is_featured BOOLEAN DEFAULT FALSE,
    is_remote_friendly BOOLEAN DEFAULT FALSE,
    views_count INT DEFAULT 0,
    applications_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at DATETIME,
    
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    INDEX idx_jobs_title (title),
    INDEX idx_jobs_department (department),
    INDEX idx_jobs_location (location),
    INDEX idx_jobs_status (status),
    INDEX idx_jobs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Candidates Table (Enhanced)
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    resume_url VARCHAR(300),
    
    -- Professional Info
    current_title VARCHAR(150),
    current_company VARCHAR(150),
    total_experience_years FLOAT,
    expected_salary INT,
    notice_period_days INT,
    preferred_locations TEXT,
    preferred_work_mode ENUM('Remote', 'Hybrid', 'Onsite'),
    
    -- Scoring
    profile_score INT DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_candidates_email (email),
    INDEX idx_candidates_current_title (current_title),
    INDEX idx_candidates_current_company (current_company)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Applications Table (Enhanced)
CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    candidate_id INT NOT NULL,
    
    -- Status & Scoring
    status ENUM('Applied', 'Screening', 'Interviewing', 'Rejected', 'Hired') DEFAULT 'Applied',
    match_score FLOAT,
    screening_score FLOAT,
    resume_score INT,
    
    -- Application Details
    cover_letter TEXT,
    applied_via VARCHAR(50) DEFAULT 'website',
    referral_code VARCHAR(50),
    
    -- Recruiter Notes
    recruiter_notes TEXT,
    rejection_reason VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    UNIQUE KEY unique_job_candidate (job_id, candidate_id),
    INDEX idx_applications_status (status),
    INDEX idx_applications_job_id (job_id),
    INDEX idx_applications_candidate_id (candidate_id),
    INDEX idx_applications_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Interviews Table (Enhanced)
CREATE TABLE IF NOT EXISTS interviews (
    interview_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    
    -- Scheduling
    scheduled_at DATETIME NOT NULL,
    end_time DATETIME,
    
    -- Type & Status
    interview_type ENUM('Phone', 'Video', 'Onsite') NOT NULL,
    status ENUM('Scheduled', 'Completed', 'Cancelled', 'No-Show') DEFAULT 'Scheduled',
    
    -- Details
    interview_link VARCHAR(500),
    location_address VARCHAR(500),
    interview_notes TEXT,
    
    -- Interviewer
    interviewer_name VARCHAR(150),
    interviewer_email VARCHAR(150),
    
    -- Feedback & Scoring
    feedback TEXT,
    interview_score INT,
    recommendation VARCHAR(50),
    technical_score INT,
    communication_score INT,
    cultural_fit_score INT,
    problem_solving_score INT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE,
    INDEX idx_interviews_scheduled_at (scheduled_at),
    INDEX idx_interviews_status (status),
    INDEX idx_interviews_application_id (application_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- User Credentials Table (Enhanced)
CREATE TABLE IF NOT EXISTS user_credentials (
    credential_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('candidate', 'recruiter', 'admin') NOT NULL,
    candidate_id INT,
    recruiter_id INT,
    
    -- Security
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(100),
    
    -- Password Management
    last_password_change DATETIME,
    failed_login_attempts INT DEFAULT 0,
    locked_until DATETIME,
    
    -- Session
    last_login_at DATETIME,
    last_login_ip VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    INDEX idx_credentials_email (email),
    INDEX idx_credentials_role (role),
    INDEX idx_credentials_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- User Profiles Table (Enhanced)
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id INT AUTO_INCREMENT PRIMARY KEY,
    credential_id INT NOT NULL UNIQUE,
    
    -- Basic Info
    full_name VARCHAR(120),
    phone_number VARCHAR(20),
    profile_image VARCHAR(300),
    
    -- Candidate Fields
    skills TEXT,
    education TEXT,
    experience TEXT,
    resume_path VARCHAR(300),
    bio TEXT,
    
    -- Recruiter Fields
    company_name VARCHAR(150),
    company_website VARCHAR(255),
    designation VARCHAR(120),
    
    -- Additional Fields
    location VARCHAR(150),
    timezone VARCHAR(50) DEFAULT 'UTC',
    social_links TEXT,
    preferences TEXT,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    
    -- Analytics
    profile_views INT DEFAULT 0,
    profile_completeness INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (credential_id) REFERENCES user_credentials(credential_id) ON DELETE CASCADE,
    INDEX idx_profiles_credential_id (credential_id),
    INDEX idx_profiles_full_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    
    -- Content
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    
    -- Related Entity
    related_type VARCHAR(50),
    related_id INT,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_sent BOOLEAN DEFAULT FALSE,
    
    -- Delivery
    send_email BOOLEAN DEFAULT TRUE,
    send_push BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME,
    
    INDEX idx_notifications_user (user_id, user_type),
    INDEX idx_notifications_is_read (is_read),
    INDEX idx_notifications_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    user_type VARCHAR(20),
    
    -- Action
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    
    -- Details
    old_values TEXT,
    new_values TEXT,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_audit_logs_user_id (user_id),
    INDEX idx_audit_logs_entity (entity_type, entity_id),
    INDEX idx_audit_logs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Job Templates Table
CREATE TABLE IF NOT EXISTS job_templates (
    template_id INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_id INT NOT NULL,
    
    -- Template Content
    title VARCHAR(150) NOT NULL,
    description TEXT,
    requirements TEXT,
    department VARCHAR(100) NOT NULL,
    required_skills TEXT,
    preferred_skills TEXT,
    min_experience_years INT,
    education_level VARCHAR(50),
    
    -- Metadata
    is_public BOOLEAN DEFAULT FALSE,
    usage_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    INDEX idx_templates_recruiter (recruiter_id),
    INDEX idx_templates_public (is_public)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Email Verification Tokens Table
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    user_type VARCHAR(20) NOT NULL,
    user_id INT,
    
    is_used BOOLEAN DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_email_tokens_token (token),
    INDEX idx_email_tokens_email (email),
    INDEX idx_email_tokens_is_used (is_used)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Password Reset Tokens Table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    
    is_used BOOLEAN DEFAULT FALSE,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_reset_tokens_token (token),
    INDEX idx_reset_tokens_email (email),
    INDEX idx_reset_tokens_is_used (is_used)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===========================================
-- Initial Data
-- ===========================================

-- Insert default admin user (password: admin123)
INSERT INTO user_credentials (email, password_hash, role, is_verified, is_active)
VALUES (
    'admin@iatrs.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJu',
    'admin',
    TRUE,
    TRUE
);

INSERT INTO user_profiles (credential_id, full_name, designation)
VALUES (
    (SELECT credential_id FROM user_credentials WHERE email = 'admin@iatrs.com'),
    'System Administrator',
    'Admin'
);

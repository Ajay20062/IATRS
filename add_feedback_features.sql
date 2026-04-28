-- =============================================
-- Smart ATS - Feedback & Rating System Tables
-- =============================================

USE ats_db;

-- 1. Interview Feedback Table
CREATE TABLE IF NOT EXISTS InterviewFeedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    recruiter_id INT NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    technical_rating INT CHECK (technical_rating >= 1 AND technical_rating <= 5),
    communication_rating INT CHECK (communication_rating >= 1 AND communication_rating <= 5),
    culture_fit_rating INT CHECK (culture_fit_rating >= 1 AND culture_fit_rating <= 5),
    strengths TEXT,
    concerns TEXT,
    recommendation ENUM('Strong Hire', 'Hire', 'No Hire', 'Strong No Hire') NOT NULL,
    additional_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES Interviews(interview_id) ON DELETE CASCADE,
    FOREIGN KEY (recruiter_id) REFERENCES Recruiters(recruiter_id) ON DELETE CASCADE
);

-- 2. Application Ratings (overall candidate rating by HR)
CREATE TABLE IF NOT EXISTS ApplicationRatings (
    rating_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    recruiter_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_notes TEXT,
    rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES Applications(application_id) ON DELETE CASCADE,
    FOREIGN KEY (recruiter_id) REFERENCES Recruiters(recruiter_id) ON DELETE CASCADE,
    UNIQUE KEY unique_app_rating (application_id, recruiter_id)
);

-- 3. Status History (audit trail)
CREATE TABLE IF NOT EXISTS StatusHistory (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by INT NOT NULL,
    change_reason TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES Applications(application_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- 4. Insert initial status as 'Applied' for existing applications
INSERT IGNORE INTO StatusHistory (application_id, old_status, new_status, changed_by, change_reason)
SELECT application_id, NULL, 'Applied',
       (SELECT COALESCE(u.user_id, 1) FROM Users u
        JOIN Candidates c ON c.email = u.email
        WHERE c.candidate_id = Applications.candidate_id LIMIT 1),
       'Application submitted'
FROM Applications;

-- 5. Trigger to auto-log status changes on Applications table
DROP TRIGGER IF EXISTS after_application_status_update;

DELIMITER //

CREATE TRIGGER after_application_status_update
AFTER UPDATE ON Applications
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO StatusHistory (application_id, old_status, new_status, changed_by, change_reason)
        VALUES (
            NEW.application_id,
            OLD.status,
            NEW.status,
            (SELECT recruiter_id FROM Jobs WHERE job_id = NEW.job_id LIMIT 1),
            CONCAT('Status changed from ', OLD.status, ' to ', NEW.status)
        );
    END IF;
END//

DELIMITER ;

-- 6. Update Applications view to include ratings
DROP VIEW IF EXISTS ApplicationDetails;
CREATE VIEW ApplicationDetails AS
SELECT
    a.application_id,
    a.job_id,
    a.candidate_id,
    a.status,
    a.created_at,
    j.title AS job_title,
    j.department,
    j.location,
    j.recruiter_id,
    c.full_name AS candidate_name,
    c.email AS candidate_email,
    c.phone AS candidate_phone,
    AVG(ar.rating) AS avg_rating,
    COUNT(DISTINCT ar.rating_id) AS rating_count,
    (SELECT new_status FROM StatusHistory sh WHERE sh.application_id = a.application_id ORDER BY changed_at DESC LIMIT 1) AS last_status
FROM Applications a
JOIN Jobs j ON a.job_id = j.job_id
JOIN Candidates c ON a.candidate_id = c.candidate_id
LEFT JOIN ApplicationRatings ar ON a.application_id = ar.application_id
GROUP BY a.application_id;

-- 7. Interview with feedback view
DROP VIEW IF EXISTS InterviewWithFeedback;
CREATE VIEW InterviewWithFeedback AS
SELECT
    i.interview_id,
    i.application_id,
    i.scheduled_at,
    i.interview_type,
    i.status AS interview_status,
    i.created_at,
    a.candidate_id,
    c.full_name AS candidate_name,
    j.title AS job_title,
    j.recruiter_id,
    f.feedback_id,
    f.rating,
    f.recommendation
FROM Interviews i
JOIN Applications a ON i.application_id = a.application_id
JOIN Candidates c ON a.candidate_id = c.candidate_id
JOIN Jobs j ON a.job_id = j.job_id
LEFT JOIN InterviewFeedback f ON i.interview_id = f.interview_id;

SELECT 'Feedback system tables created successfully!' AS result;

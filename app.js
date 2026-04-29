const express = require('express');
const cors = require('cors');
const bcrypt = require('bcrypt');
const mysql = require('mysql2/promise');
const winston = require('winston');
const path = require('path');
require('dotenv').config();

const { getDbConnection } = require('./db_connect');

// Initialize Express app
const app = express();

// Express configuration
app.set('trust proxy', 1);
app.use(express.json({ limit: '16mb' }));
app.use(express.urlencoded({ extended: true, limit: '16mb' }));

// Enable CORS for all routes
app.use(cors());

// Configure static file serving
app.use('/static', express.static(path.join(__dirname, 'frontend')));

// Configure logging
const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    defaultMeta: { service: 'iatrs-backend' },
    transports: [
        new winston.transports.File({ filename: 'app.log' }),
        new winston.transports.Console({
            format: winston.format.combine(
                winston.format.colorize(),
                winston.format.simple()
            )
        })
    ]
});

const ALLOWED_ROLES = new Set(['candidate', 'recruiter']);
const ALLOWED_APPLICATION_STATUSES = new Set(['Applied', 'Screening', 'Interviewing', 'Rejected', 'Hired']);
const ALLOWED_INTERVIEW_TYPES = new Set(['Phone', 'Video', 'Onsite']);
const ALLOWED_INTERVIEW_STATUSES = new Set(['Scheduled', 'Completed', 'No-Show', 'Cancelled']);
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email) {
    return EMAIL_REGEX.test(email || '');
}

function serializeUser(user) {
    return {
        user_id: user.user_id,
        full_name: user.full_name,
        email: user.email,
        role: user.role,
        candidate_id: user.candidate_id,
        recruiter_id: user.recruiter_id
    };
}

async function safeCheckPassword(passwordHash, password) {
    try {
        return await bcrypt.compare(password, passwordHash);
    } catch (error) {
        logger.error('Password check error:', error);
        return false;
    }
}

function formatIntegrityError(error) {
    const message = error.message.toLowerCase();

    if ((message.includes('duplicate entry') || message.includes('unique')) &&
        (message.includes('applications') || (message.includes('job_id') && message.includes('candidate_id')))) {
        return 'You have already applied for this job';
    }

    if (message.includes('duplicate entry') && message.includes('email')) {
        return 'Email already exists';
    }

    if (message.includes('foreign key')) {
        return 'Referenced record was not found. Please refresh and try again';
    }

    return 'Database integrity constraint failed';
}

async function initializeAuthTable() {
    let connection = null;
    let transaction = null;

    try {
        connection = await getDbConnection();
        if (!connection) return false;

        await connection.execute(`
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT PRIMARY KEY AUTO_INCREMENT,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('candidate', 'recruiter') NOT NULL,
                candidate_id INT UNIQUE,
                recruiter_id INT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_users_candidate
                    FOREIGN KEY (candidate_id)
                    REFERENCES Candidates(candidate_id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_users_recruiter
                    FOREIGN KEY (recruiter_id)
                    REFERENCES Recruiters(recruiter_id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
        `);

        return true;
    } catch (error) {
        logger.error('Error initializing auth table:', error);
        return false;
    } finally {
        if (connection) {
            await connection.end();
        }
    }
}

async function initializeInterviewArtifacts() {
    let connection = null;

    try {
        connection = await getDbConnection();
        if (!connection) return false;

        // Create view
        await connection.execute(`
            CREATE OR REPLACE VIEW Scheduled_Interviews AS
            SELECT interview_id, application_id, scheduled_at, interview_type, status
            FROM Interviews
            WHERE status = 'Scheduled'
        `);

        // Check if trigger exists
        const [rows] = await connection.execute(`
            SELECT COUNT(*) AS count
            FROM information_schema.triggers
            WHERE trigger_schema = DATABASE()
              AND trigger_name = 'trg_update_application_status'
        `);

        if (rows[0].count === 0) {
            await connection.execute(`
                CREATE TRIGGER trg_update_application_status
                AFTER UPDATE ON Interviews
                FOR EACH ROW
                BEGIN
                    IF NEW.status = 'Completed' THEN
                        UPDATE Applications
                        SET status = 'Interviewing'
                        WHERE application_id = NEW.application_id;
                    END IF;
                END
            `);
        }

        return true;
    } catch (error) {
        logger.error('Error initializing interview artifacts:', error);
        return false;
    } finally {
        if (connection) {
            await connection.end();
        }
    }
}

// Initialize database artifacts
(async () => {
    await initializeAuthTable();
    await initializeInterviewArtifacts();
})();

// Health check endpoint
app.get('/health', async (req, res) => {
    try {
        const connection = await getDbConnection();
        if (connection) {
            await connection.end();
            logger.info('Health check passed - database connected');
            return res.json({
                status: 'healthy',
                database: 'connected',
                timestamp: new Date().toISOString()
            });
        } else {
            return res.status(503).json({
                status: 'unhealthy',
                database: 'disconnected',
                timestamp: new Date().toISOString()
            });
        }
    } catch (error) {
        logger.error('Health check failed:', error);
        return res.status(503).json({
            status: 'unhealthy',
            database: 'error',
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

// Authentication Routes

// Unified register endpoint
app.post('/auth/register', async (req, res) => {
    const { full_name, email, password, role } = req.body;

    // Validation
    if (!full_name || !email || !password || !role) {
        return res.status(400).json({ error: 'All fields are required' });
    }

    if (!isValidEmail(email)) {
        return res.status(400).json({ error: 'Invalid email format' });
    }

    if (password.length < 6) {
        return res.status(400).json({ error: 'Password must be at least 6 characters long' });
    }

    if (!ALLOWED_ROLES.has(role)) {
        return res.status(400).json({ error: 'Invalid role. Must be candidate or recruiter' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        // Start transaction
        await connection.beginTransaction();

        // Hash password
        const passwordHash = await bcrypt.hash(password, 12);

        // Insert into role-specific table first
        let roleId;
        if (role === 'candidate') {
            const [result] = await connection.execute(
                'INSERT INTO Candidates (full_name, email) VALUES (?, ?)',
                [full_name, email]
            );
            roleId = result.insertId;
        } else { // recruiter
            const [result] = await connection.execute(
                'INSERT INTO Recruiters (full_name, email) VALUES (?, ?)',
                [full_name, email]
            );
            roleId = result.insertId;
        }

        // Insert into Users table
        const [userResult] = await connection.execute(
            'INSERT INTO Users (full_name, email, password_hash, role, candidate_id, recruiter_id) VALUES (?, ?, ?, ?, ?, ?)',
            [full_name, email, passwordHash, role, role === 'candidate' ? roleId : null, role === 'recruiter' ? roleId : null]
        );

        await connection.commit();

        const user = {
            user_id: userResult.insertId,
            full_name,
            email,
            role,
            candidate_id: role === 'candidate' ? roleId : null,
            recruiter_id: role === 'recruiter' ? roleId : null
        };

        logger.info(`User registered: ${email} as ${role}`);
        res.status(201).json({
            message: 'User registered successfully',
            user: serializeUser(user)
        });

    } catch (error) {
        if (connection) {
            await connection.rollback();
        }
        logger.error('Registration error:', error);
        const friendlyMessage = formatIntegrityError(error);
        res.status(400).json({ error: friendlyMessage });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Legacy register endpoints
app.post('/register/candidate', async (req, res) => {
    req.body.role = 'candidate';
    // Forward to unified register
    return app._router.handle(req, res, () => {});
});

app.post('/register/recruiter', async (req, res) => {
    req.body.role = 'recruiter';
    // Forward to unified register
    return app._router.handle(req, res, () => {});
});

// Login endpoint
app.post('/auth/login', async (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({ error: 'Email and password are required' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            'SELECT * FROM Users WHERE email = ?',
            [email]
        );

        if (rows.length === 0) {
            return res.status(401).json({ error: 'Invalid email or password' });
        }

        const user = rows[0];
        const isValidPassword = await safeCheckPassword(user.password_hash, password);

        if (!isValidPassword) {
            return res.status(401).json({ error: 'Invalid email or password' });
        }

        logger.info(`User logged in: ${email}`);
        res.json({
            message: 'Login successful',
            user: serializeUser(user)
        });

    } catch (error) {
        logger.error('Login error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Legacy login endpoint
app.post('/login', async (req, res) => {
    // Forward to unified login
    return app._router.handle(req, res, () => {});
});

// Job Management Routes

// Get all jobs with pagination
app.get('/jobs', async (req, res) => {
    const page = parseInt(req.query.page) || 1;
    const perPage = parseInt(req.query.per_page) || 10;
    const offset = (page - 1) * perPage;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            `SELECT j.*, r.full_name as recruiter_name, r.email as recruiter_email
             FROM Jobs j
             JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
             ORDER BY j.created_at DESC
             LIMIT ? OFFSET ?`,
            [perPage, offset]
        );

        const [countRows] = await connection.execute('SELECT COUNT(*) as total FROM Jobs');
        const total = countRows[0].total;
        const totalPages = Math.ceil(total / perPage);

        res.json({
            jobs: rows,
            pagination: {
                page,
                per_page: perPage,
                total,
                total_pages: totalPages,
                has_next: page < totalPages,
                has_prev: page > 1
            }
        });

    } catch (error) {
        logger.error('Get jobs error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get single job
app.get('/jobs/:id', async (req, res) => {
    const jobId = req.params.id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            `SELECT j.*, r.full_name as recruiter_name, r.email as recruiter_email
             FROM Jobs j
             JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
             WHERE j.job_id = ?`,
            [jobId]
        );

        if (rows.length === 0) {
            return res.status(404).json({ error: 'Job not found' });
        }

        res.json({ job: rows[0] });

    } catch (error) {
        logger.error('Get job error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Create job
app.post('/jobs', async (req, res) => {
    const { title, description, requirements, location, department, salary_min, salary_max, recruiter_id } = req.body;

    if (!title || !description || !recruiter_id) {
        return res.status(400).json({ error: 'Title, description, and recruiter_id are required' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [result] = await connection.execute(
            `INSERT INTO Jobs (title, description, requirements, location, department, salary_min, salary_max, recruiter_id)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
            [title, description, requirements || null, location || null, department || null, salary_min || null, salary_max || null, recruiter_id]
        );

        logger.info(`Job created: ${title} by recruiter ${recruiter_id}`);
        res.status(201).json({
            message: 'Job created successfully',
            job_id: result.insertId
        });

    } catch (error) {
        logger.error('Create job error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get jobs by recruiter
app.get('/jobs/recruiter/:recruiter_id', async (req, res) => {
    const recruiterId = req.params.recruiter_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            'SELECT * FROM Jobs WHERE recruiter_id = ? ORDER BY created_at DESC',
            [recruiterId]
        );

        res.json({ jobs: rows });

    } catch (error) {
        logger.error('Get recruiter jobs error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Search jobs
app.get('/jobs/search', async (req, res) => {
    const { q, location, department, status, page = 1, per_page = 10 } = req.query;
    const offset = (page - 1) * per_page;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        let query = `
            SELECT j.*, r.full_name as recruiter_name
            FROM Jobs j
            JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE 1=1
        `;
        const params = [];

        if (q) {
            query += ' AND (j.title LIKE ? OR j.description LIKE ? OR j.requirements LIKE ?)';
            params.push(`%${q}%`, `%${q}%`, `%${q}%`);
        }

        if (location) {
            query += ' AND j.location LIKE ?';
            params.push(`%${location}%`);
        }

        if (department) {
            query += ' AND j.department LIKE ?';
            params.push(`%${department}%`);
        }

        if (status) {
            query += ' AND j.status = ?';
            params.push(status);
        }

        query += ' ORDER BY j.created_at DESC LIMIT ? OFFSET ?';
        params.push(parseInt(per_page), offset);

        const [rows] = await connection.execute(query, params);

        // Get total count for pagination
        let countQuery = 'SELECT COUNT(*) as total FROM Jobs j WHERE 1=1';
        const countParams = [];

        if (q) {
            countQuery += ' AND (j.title LIKE ? OR j.description LIKE ? OR j.requirements LIKE ?)';
            countParams.push(`%${q}%`, `%${q}%`, `%${q}%`);
        }

        if (location) {
            countQuery += ' AND j.location LIKE ?';
            countParams.push(`%${location}%`);
        }

        if (department) {
            countQuery += ' AND j.department LIKE ?';
            countParams.push(`%${department}%`);
        }

        if (status) {
            countQuery += ' AND j.status = ?';
            countParams.push(status);
        }

        const [countRows] = await connection.execute(countQuery, countParams);
        const total = countRows[0].total;
        const totalPages = Math.ceil(total / per_page);

        res.json({
            jobs: rows,
            pagination: {
                page: parseInt(page),
                per_page: parseInt(per_page),
                total,
                total_pages: totalPages,
                has_next: page < totalPages,
                has_prev: page > 1
            }
        });

    } catch (error) {
        logger.error('Search jobs error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get job recommendations for candidate
app.get('/jobs/recommend/:candidate_id', async (req, res) => {
    const candidateId = req.params.candidate_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        // Simple recommendation based on candidate's past applications
        // In a real system, this would use ML algorithms
        const [appliedJobs] = await connection.execute(
            `SELECT DISTINCT j.department, j.location
             FROM Applications a
             JOIN Jobs j ON a.job_id = j.job_id
             WHERE a.candidate_id = ?`,
            [candidateId]
        );

        let query = `
            SELECT j.*, r.full_name as recruiter_name
            FROM Jobs j
            JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
            WHERE j.status = 'Open'
        `;
        const params = [];

        if (appliedJobs.length > 0) {
            const departments = appliedJobs.map(job => job.department).filter(Boolean);
            const locations = appliedJobs.map(job => job.location).filter(Boolean);

            if (departments.length > 0) {
                query += ' AND j.department IN (?)';
                params.push(departments);
            }

            if (locations.length > 0) {
                query += ' AND j.location IN (?)';
                params.push(locations);
            }
        }

        query += ' ORDER BY j.created_at DESC LIMIT 10';

        const [rows] = await connection.execute(query, params);

        res.json({ recommendations: rows });

    } catch (error) {
        logger.error('Get recommendations error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Application Management Routes

// Apply for job
app.post('/apply', async (req, res) => {
    const { job_id, candidate_id } = req.body;

    if (!job_id || !candidate_id) {
        return res.status(400).json({ error: 'job_id and candidate_id are required' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        // Check if job exists and is open
        const [jobRows] = await connection.execute(
            'SELECT * FROM Jobs WHERE job_id = ? AND status = "Open"',
            [job_id]
        );

        if (jobRows.length === 0) {
            return res.status(400).json({ error: 'Job not found or not open for applications' });
        }

        // Check if candidate has already applied
        const [existingApp] = await connection.execute(
            'SELECT * FROM Applications WHERE job_id = ? AND candidate_id = ?',
            [job_id, candidate_id]
        );

        if (existingApp.length > 0) {
            return res.status(400).json({ error: 'You have already applied for this job' });
        }

        // Create application
        const [result] = await connection.execute(
            'INSERT INTO Applications (job_id, candidate_id, status) VALUES (?, ?, "Applied")',
            [job_id, candidate_id]
        );

        logger.info(`Application created: job ${job_id} by candidate ${candidate_id}`);
        res.status(201).json({
            message: 'Application submitted successfully',
            application_id: result.insertId
        });

    } catch (error) {
        logger.error('Apply for job error:', error);
        const friendlyMessage = formatIntegrityError(error);
        res.status(400).json({ error: friendlyMessage });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get applications by candidate
app.get('/applications/candidate/:candidate_id', async (req, res) => {
    const candidateId = req.params.candidate_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            `SELECT a.*, j.title, j.location, j.department, r.full_name as recruiter_name
             FROM Applications a
             JOIN Jobs j ON a.job_id = j.job_id
             JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
             WHERE a.candidate_id = ?
             ORDER BY a.applied_at DESC`,
            [candidateId]
        );

        res.json({ applications: rows });

    } catch (error) {
        logger.error('Get candidate applications error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get applications by recruiter
app.get('/applications/recruiter/:recruiter_id', async (req, res) => {
    const recruiterId = req.params.recruiter_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            `SELECT a.*, j.title, j.location, j.department, c.full_name as candidate_name, c.email as candidate_email
             FROM Applications a
             JOIN Jobs j ON a.job_id = j.job_id
             JOIN Candidates c ON a.candidate_id = c.candidate_id
             WHERE j.recruiter_id = ?
             ORDER BY a.applied_at DESC`,
            [recruiterId]
        );

        res.json({ applications: rows });

    } catch (error) {
        logger.error('Get recruiter applications error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Update application status
app.put('/applications/:application_id/status', async (req, res) => {
    const applicationId = req.params.application_id;
    const { status } = req.body;

    if (!status || !ALLOWED_APPLICATION_STATUSES.has(status)) {
        return res.status(400).json({ error: 'Valid status is required' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [result] = await connection.execute(
            'UPDATE Applications SET status = ? WHERE application_id = ?',
            [status, applicationId]
        );

        if (result.affectedRows === 0) {
            return res.status(404).json({ error: 'Application not found' });
        }

        // Log status change
        await connection.execute(
            'INSERT INTO StatusHistory (application_id, old_status, new_status, changed_by) VALUES (?, (SELECT status FROM Applications WHERE application_id = ?), ?, ?)',
            [applicationId, applicationId, status, req.body.changed_by || null]
        );

        logger.info(`Application ${applicationId} status updated to ${status}`);
        res.json({ message: 'Application status updated successfully' });

    } catch (error) {
        logger.error('Update application status error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Interview Management Routes

// Schedule interview
app.post('/interviews', async (req, res) => {
    const { application_id, scheduled_at, interview_type, notes } = req.body;

    if (!application_id || !scheduled_at || !interview_type) {
        return res.status(400).json({ error: 'application_id, scheduled_at, and interview_type are required' });
    }

    if (!ALLOWED_INTERVIEW_TYPES.has(interview_type)) {
        return res.status(400).json({ error: 'Invalid interview type' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [result] = await connection.execute(
            'INSERT INTO Interviews (application_id, scheduled_at, interview_type, status, notes) VALUES (?, ?, ?, "Scheduled", ?)',
            [application_id, scheduled_at, interview_type, notes || null]
        );

        logger.info(`Interview scheduled: ${result.insertId} for application ${application_id}`);
        res.status(201).json({
            message: 'Interview scheduled successfully',
            interview_id: result.insertId
        });

    } catch (error) {
        logger.error('Schedule interview error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Update interview status
app.put('/interviews/:interview_id/status', async (req, res) => {
    const interviewId = req.params.interview_id;
    const { status } = req.body;

    if (!status || !ALLOWED_INTERVIEW_STATUSES.has(status)) {
        return res.status(400).json({ error: 'Valid status is required' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [result] = await connection.execute(
            'UPDATE Interviews SET status = ? WHERE interview_id = ?',
            [status, interviewId]
        );

        if (result.affectedRows === 0) {
            return res.status(404).json({ error: 'Interview not found' });
        }

        logger.info(`Interview ${interviewId} status updated to ${status}`);
        res.json({ message: 'Interview status updated successfully' });

    } catch (error) {
        logger.error('Update interview status error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get scheduled interviews by recruiter
app.get('/interviews/scheduled/recruiter/:recruiter_id', async (req, res) => {
    const recruiterId = req.params.recruiter_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            `SELECT i.*, a.application_id, j.title as job_title, c.full_name as candidate_name
             FROM Scheduled_Interviews i
             JOIN Applications a ON i.application_id = a.application_id
             JOIN Jobs j ON a.job_id = j.job_id
             JOIN Candidates c ON a.candidate_id = c.candidate_id
             WHERE j.recruiter_id = ?
             ORDER BY i.scheduled_at ASC`,
            [recruiterId]
        );

        res.json({ interviews: rows });

    } catch (error) {
        logger.error('Get scheduled interviews error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Submit interview feedback
app.post('/interviews/:interview_id/feedback', async (req, res) => {
    const interviewId = req.params.interview_id;
    const { feedback_text, rating, interviewer_id } = req.body;

    if (!feedback_text || rating === undefined) {
        return res.status(400).json({ error: 'feedback_text and rating are required' });
    }

    if (rating < 1 || rating > 5) {
        return res.status(400).json({ error: 'Rating must be between 1 and 5' });
    }

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [result] = await connection.execute(
            'INSERT INTO InterviewFeedback (interview_id, feedback_text, rating, interviewer_id) VALUES (?, ?, ?, ?)',
            [interviewId, feedback_text, rating, interviewer_id || null]
        );

        logger.info(`Feedback submitted for interview ${interviewId}`);
        res.status(201).json({
            message: 'Feedback submitted successfully',
            feedback_id: result.insertId
        });

    } catch (error) {
        logger.error('Submit feedback error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get interview feedback
app.get('/interviews/:interview_id/feedback', async (req, res) => {
    const interviewId = req.params.interview_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [rows] = await connection.execute(
            `SELECT f.*, u.full_name as interviewer_name
             FROM InterviewFeedback f
             LEFT JOIN Users u ON f.interviewer_id = u.user_id
             WHERE f.interview_id = ?
             ORDER BY f.created_at DESC`,
            [interviewId]
        );

        res.json({ feedback: rows });

    } catch (error) {
        logger.error('Get feedback error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Analytics and Dashboard Routes

// Get recruiter analytics
app.get('/analytics/recruiter/:recruiter_id', async (req, res) => {
    const recruiterId = req.params.recruiter_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        // Get job statistics
        const [jobStats] = await connection.execute(
            `SELECT 
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_jobs,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_jobs
             FROM Jobs WHERE recruiter_id = ?`,
            [recruiterId]
        );

        // Get application statistics
        const [appStats] = await connection.execute(
            `SELECT 
                COUNT(*) as total_applications,
                SUM(CASE WHEN status = 'Applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'Screening' THEN 1 ELSE 0 END) as screening,
                SUM(CASE WHEN status = 'Interviewing' THEN 1 ELSE 0 END) as interviewing,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'Hired' THEN 1 ELSE 0 END) as hired
             FROM Applications a
             JOIN Jobs j ON a.job_id = j.job_id
             WHERE j.recruiter_id = ?`,
            [recruiterId]
        );

        // Get interview statistics
        const [interviewStats] = await connection.execute(
            `SELECT 
                COUNT(*) as total_interviews,
                SUM(CASE WHEN status = 'Scheduled' THEN 1 ELSE 0 END) as scheduled,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) as no_show,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled
             FROM Interviews i
             JOIN Applications a ON i.application_id = a.application_id
             JOIN Jobs j ON a.job_id = j.job_id
             WHERE j.recruiter_id = ?`,
            [recruiterId]
        );

        res.json({
            job_stats: jobStats[0],
            application_stats: appStats[0],
            interview_stats: interviewStats[0]
        });

    } catch (error) {
        logger.error('Get analytics error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get recruiter dashboard data
app.get('/dashboard/recruiter/:recruiter_id', async (req, res) => {
    const recruiterId = req.params.recruiter_id;

    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        // Recent applications
        const [recentApps] = await connection.execute(
            `SELECT a.*, j.title, c.full_name as candidate_name
             FROM Applications a
             JOIN Jobs j ON a.job_id = j.job_id
             JOIN Candidates c ON a.candidate_id = c.candidate_id
             WHERE j.recruiter_id = ?
             ORDER BY a.applied_at DESC
             LIMIT 10`,
            [recruiterId]
        );

        // Upcoming interviews
        const [upcomingInterviews] = await connection.execute(
            `SELECT i.*, a.application_id, j.title, c.full_name as candidate_name
             FROM Interviews i
             JOIN Applications a ON i.application_id = a.application_id
             JOIN Jobs j ON a.job_id = j.job_id
             JOIN Candidates c ON a.candidate_id = c.candidate_id
             WHERE j.recruiter_id = ? AND i.status = 'Scheduled' AND i.scheduled_at > NOW()
             ORDER BY i.scheduled_at ASC
             LIMIT 5`,
            [recruiterId]
        );

        res.json({
            recent_applications: recentApps,
            upcoming_interviews: upcomingInterviews
        });

    } catch (error) {
        logger.error('Get dashboard error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Get system statistics
app.get('/system/stats', async (req, res) => {
    let connection = null;
    try {
        connection = await getDbConnection();
        if (!connection) {
            return res.status(500).json({ error: 'Database connection failed' });
        }

        const [stats] = await connection.execute(`
            SELECT 
                (SELECT COUNT(*) FROM Users) as total_users,
                (SELECT COUNT(*) FROM Candidates) as total_candidates,
                (SELECT COUNT(*) FROM Recruiters) as total_recruiters,
                (SELECT COUNT(*) FROM Jobs) as total_jobs,
                (SELECT COUNT(*) FROM Applications) as total_applications,
                (SELECT COUNT(*) FROM Interviews) as total_interviews
        `);

        res.json({ stats: stats[0] });

    } catch (error) {
        logger.error('Get system stats error:', error);
        res.status(500).json({ error: 'Internal server error' });
    } finally {
        if (connection) {
            await connection.end();
        }
    }
});

// Frontend Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'index.html'));
});

app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'login.html'));
});

app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'register.html'));
});

app.get('/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'dashboard.html'));
});

app.get('/recruiter/jobs', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'recruiter_jobs.html'));
});

app.get('/recruiter/candidates', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'recruiter_candidates.html'));
});

app.get('/recruiter/analytics', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'recruiter_analytics.html'));
});

app.get('/my-applications', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'my_applications.html'));
});

app.get('/api-status', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'api-status.html'));
});

app.get('/database-schema', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'database-schema.html'));
});

// Error handling middleware
app.use((error, req, res, next) => {
    logger.error('Unhandled error:', error);
    res.status(500).json({
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
    });
});

// Start server
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    logger.info(`Server running on port ${PORT}`);
});

module.exports = app;
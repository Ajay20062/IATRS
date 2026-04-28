# IATRS - Intelligent Automated Recruitment Tracking System

A comprehensive recruitment management system built with Flask and MySQL.

## Features

- **User Authentication**: Secure login/registration for candidates and recruiters
- **Job Management**: Post, view, and manage job listings
- **Application Tracking**: Candidates can apply for jobs and track their applications
- **Interview Scheduling**: Schedule and manage interview processes
- **Advanced Search**: Multi-filter job search with pagination
- **Job Recommendations**: AI-powered job suggestions based on candidate history
- **Analytics Dashboard**: Comprehensive recruiter analytics and reporting
- **Bulk Operations**: Bulk job creation and application status updates
- **User Activity Tracking**: Detailed activity logs and system statistics
- **RESTful API**: Backend API for all operations

## Tech Stack

- **Backend**: Python Flask
- **Database**: MySQL
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Werkzeug security

## Setup Instructions

1. **Prerequisites**:
   - Python 3.8+
   - MySQL Server
   - Git

2. **Clone the repository**:
   ```bash
   git clone https://github.com/Ajay20062/IATRS.git
   cd IATRS
   ```

3. **Install dependencies**:
   ```bash
   pip install flask flask-cors mysql-connector-python python-dotenv
   ```

4. **Database Setup**:
   - Create a MySQL database named `recruitment_db`
   - Update `.env` file with your MySQL credentials
   - Run the setup script:
   ```bash
   python setup_mysql.py
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   - Frontend: http://localhost:5001
   - API endpoints available at the same URL

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout

### Advanced Features
- `GET /jobs/search` - Advanced job search with filters
- `GET /jobs/recommend/<candidate_id>` - Personalized job recommendations
- `GET /analytics/recruiter/<recruiter_id>` - Comprehensive recruiter analytics
- `POST /bulk/jobs` - Bulk job creation
- `PUT /bulk/applications/status` - Bulk application status updates
- `GET /users/activity/<user_id>` - User activity tracking
- `GET /system/stats` - System-wide statistics

### Jobs
- `GET /jobs` - List all jobs
- `POST /jobs` - Create new job (recruiters only)
- `GET /jobs/<id>` - Get job details

### Applications
- `POST /applications` - Submit job application
- `GET /applications/my` - Get user's applications

### Interviews
- `POST /interviews` - Schedule interview
- `GET /interviews` - List interviews

## Advanced Features

### 🔍 Advanced Job Search
- Multi-filter search (location, department, company, status)
- Pagination support
- Sorting by date, relevance, or other criteria
- Real-time search results

### 🤖 Job Recommendations
- Personalized job suggestions based on application history
- Machine learning-powered relevance scoring
- Department and location preference analysis

### 📊 Analytics Dashboard
- Comprehensive recruiter metrics
- Application trends and conversion rates
- Interview success statistics
- Monthly performance reports
- Top-performing job analysis

### ⚡ Bulk Operations
- Bulk job posting for recruiters
- Mass application status updates
- Efficient data management for large organizations

### 📈 System Monitoring
- User activity tracking
- System-wide statistics
- Health check endpoints
- Performance monitoring

## Database Schema

The system uses the following main tables:
- `Users` - User accounts
- `Recruiters` - Recruiter profiles
- `Candidates` - Candidate profiles
- `Jobs` - Job listings
- `Applications` - Job applications
- `Interviews` - Interview schedules

## Development

- Run tests: `python e2e_auth_test.py`
- Database migrations: Check `migrate_to_users_table.py`
- Schema updates: `schema.sql`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
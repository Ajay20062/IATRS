# Smart ATS Recruitment System

A comprehensive Applicant Tracking System (ATS) built with Flask, MySQL, and modern web technologies.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MySQL Server
- Modern web browser

### Setup Instructions

1. **Clone/Download the project**
   ```bash
   git clone https://github.com/Ajay20062/DBMS-IATRS/
   cd DBMS-IATRS
   ```

2. **Set up Python environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure Database**
   - Create MySQL database named `iats_db`
   - Update `.env` file with your database credentials:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=iats_db
   ```

4. **Initialize Database**
   ```bash
   python seed_data.py
   ```

5. **Start the Application**
   ```bash
   # Windows
   start.bat
   
   # Mac/Linux
   ./start.sh
   
   # Or manually:
   python app.py
   ```

6. **Access the Application**
   - Backend API root: http://127.0.0.1:5000
   - Candidate Portal: http://127.0.0.1:5000/ui
   - Recruiter Dashboard: http://127.0.0.1:5000/ui/dashboard.html
   - Database Schema: http://127.0.0.1:5000/ui/database-schema.html
   - API Status: http://127.0.0.1:5000/ui/api-status.html

## 📁 Project Structure

```
DBMS-IATRS/
├── app.py                 # Main Flask application
├── db_connect.py          # Database connection module
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── schema.sql            # Database schema
├── seed_data.py          # Sample data seeder
├── setup_mysql.py        # Database setup script
├── start.bat             # Windows startup script
├── start.sh              # Mac/Linux startup script
├── venv/                 # Python virtual environment
├── frontend/             # Frontend HTML files
│   ├── index.html        # Candidate portal
│   ├── dashboard.html    # Recruiter dashboard
│   ├── database-schema.html  # Database viewer
│   └── api-status.html   # API monitoring
└── README.md             # This file
```

## 🛠️ Technology Stack

### Backend
- **Flask** - Web framework
- **Flask-CORS** - Cross-origin resource sharing
- **MySQL** - Database
- **python-dotenv** - Environment variable management

### Frontend
- **HTML5** - Markup
- **Tailwind CSS** - Styling
- **JavaScript (ES6+)** - Interactivity
- **Fetch API** - HTTP requests

### Database
- **MySQL** - Relational database
- **SQL** - Query language

## 📊 Database Schema

The system uses 5 main tables:
- **Recruiters** - Hiring managers and recruiters
- **Jobs** - Job postings and positions
- **Candidates** - Job applicants
- **Applications** - Job applications linking candidates to jobs
- **Interviews** - Interview schedules and details

## 🔧 API Endpoints

### Jobs
- `GET /jobs` - Get all jobs
- `GET /jobs/<id>` - Get specific job
- `POST /jobs` - Create new job

### Applications
- `GET /applications` - Get all applications with candidate/job details
- `POST /apply` - Submit job application

### System
- `GET /` - Health check endpoint

## 🎯 Features

### Candidate Portal
- **Job Search**: Real-time search and filtering
- **Advanced Filters**: Filter by department, location, status
- **View Modes**: Grid and list views
- **Statistics**: Job counts and metrics
- **Applications**: One-click job applications

### Recruiter Dashboard
- **Application Management**: View and manage all applications
- **Job Creation**: Create new job postings
- **Statistics**: Application metrics and analytics
- **Modern UI**: Professional interface with charts

### System Features
- **Real-time Updates**: Live data synchronization
- **Error Handling**: Comprehensive error management
- **Responsive Design**: Works on all devices
- **Professional UI**: Modern, clean interface

## 🔒 Environment Variables

Create a `.env` file in the project root:

```env
# MySQL Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=iats_db
```

## 🧪 Testing

### Test Database Connection
```bash
python test_db.py
```

### Test API Endpoints
```bash
python test_apply_api.py
```

### Seed Sample Data
```bash
python seed_data.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure MySQL server is running
   - Check `.env` file credentials
   - Verify database name exists

2. **Module Import Errors**
   - Activate virtual environment
   - Install requirements: `pip install -r requirements.txt`

3. **Port Already in Use**
   - Change port in `app.py` (line 256)
   - Kill existing Python processes

4. **CORS Issues**
   - Ensure Flask-CORS is installed
   - Check frontend API URL configuration

### Debug Mode

The application runs in debug mode by default. For production:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## 📝 Development Notes

### Adding New Features
1. Update database schema in `schema.sql`
2. Add API endpoints in `app.py`
3. Update frontend HTML/JavaScript
4. Test with `test_db.py`

### Database Changes
- Use `setup_mysql.py` for schema changes
- Backup data before schema updates
- Test with sample data first

## 📞 Support

For issues and questions:
1. Check troubleshooting section
2. Review error logs in console
3. Verify database connection
4. Test API endpoints individually

## 📜 License

This project is for educational and demonstration purposes.

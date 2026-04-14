erDiagram
    USERS ||--o| CANDIDATES : maps_to
    USERS ||--o| RECRUITERS : maps_to
    RECRUITERS ||--o{ JOBS : posts
    JOBS ||--o{ APPLICATIONS : receives
    CANDIDATES ||--o{ APPLICATIONS : submits
    APPLICATIONS ||--o{ INTERVIEWS : has

    USERS {
        int user_id PK
        string full_name
        string email
        string password_hash
        string role
        int candidate_id FK
        int recruiter_id FK
        timestamp created_at
    }

    RECRUITERS {
        int recruiter_id PK
        string full_name
        string email
        string company
        timestamp created_at
    }

    JOBS {
        int job_id PK
        int recruiter_id FK
        string title
        string department
        string location
        string status
        timestamp created_at
    }

    CANDIDATES {
        int candidate_id PK
        string full_name
        string email
        string phone
        string resume_url
        timestamp created_at
    }

    APPLICATIONS {
        int application_id PK
        int job_id FK
        int candidate_id FK
        string status
        timestamp created_at
    }

    INTERVIEWS {
        int interview_id PK
        int application_id FK
        datetime scheduled_at
        string interview_type
        string status
        timestamp created_at
    }

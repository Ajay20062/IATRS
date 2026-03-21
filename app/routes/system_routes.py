from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from app import models
from app.utils.dependencies import get_db

router = APIRouter(prefix="/stats", tags=["System"])


@router.get("/schema")
def schema_stats(db: Session = Depends(get_db)):
    recruiters = db.query(func.count(models.Recruiter.recruiter_id)).scalar() or 0
    jobs = db.query(func.count(models.Job.job_id)).scalar() or 0
    candidates = db.query(func.count(models.Candidate.candidate_id)).scalar() or 0
    applications = db.query(func.count(models.Application.application_id)).scalar() or 0
    interviews = db.query(func.count(models.Interview.interview_id)).scalar() or 0
    
    # Calculate total records including other tables if needed, or just these core ones
    total = recruiters + jobs + candidates + applications + interviews

    return {
        "recruiters": recruiters,
        "jobs": jobs,
        "candidates": candidates,
        "applications": applications,
        "interviews": interviews,
        "total_records": total,
    }


@router.get("/table/{table_name}")
def get_table_data(table_name: str, db: Session = Depends(get_db)):
    table_map = {
        "recruiters": models.Recruiter,
        "jobs": models.Job,
        "candidates": models.Candidate,
        "applications": models.Application,
        "interviews": models.Interview,
        "user_credentials": models.UserCredential,
        "user_profiles": models.UserProfile
    }

    if table_name not in table_map:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    model = table_map[table_name]
    
    # Introspect columns
    mapper = inspect(model)
    columns = []
    for column in mapper.columns:
        col_info = {
            "name": column.name,
            "type": str(column.type),
            "primary_key": column.primary_key,
            "nullable": column.nullable,
            "foreign_keys": [fk.target_fullname for fk in column.foreign_keys]
        }
        columns.append(col_info)

    # Fetch data (limit 50)
    rows = db.query(model).limit(50).all()
    
    data = []
    for row in rows:
        row_dict = {}
        for col in columns:
            val = getattr(row, col["name"])
            # Simple serialization for Date/Time objects
            if val is not None and ("Date" in col["type"] or "Time" in col["type"]):
                row_dict[col["name"]] = str(val)
            else:
                row_dict[col["name"]] = val
        data.append(row_dict)

    return {"columns": columns, "rows": data}


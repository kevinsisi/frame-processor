from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import PhotoOut, ProjectCreate, ProjectDetail, ProjectOut
from models.photo import Photo
from models.project import Project
from services import storage

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    project = Project(name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut(id=project.id, name=project.name, created_at=project.created_at, photo_count=0)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectOut]:
    rows = db.execute(
        select(Project, func.count(Photo.id))
        .join(Photo, Photo.project_id == Project.id, isouter=True)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    ).all()
    return [
        ProjectOut(id=p.id, name=p.name, created_at=p.created_at, photo_count=count)
        for p, count in rows
    ]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: UUID, db: Session = Depends(get_db)) -> ProjectDetail:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    photos = db.execute(
        select(Photo).where(Photo.project_id == project_id).order_by(Photo.uploaded_at)
    ).scalars().all()
    return ProjectDetail(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        photo_count=len(photos),
        photos=[PhotoOut.model_validate(p) for p in photos],
    )


@router.post("/{project_id}/photos", response_model=list[PhotoOut], status_code=status.HTTP_201_CREATED)
def upload_photos(
    project_id: UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> list[PhotoOut]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    saved: list[Photo] = []
    for upload in files:
        try:
            stored = storage.save_original(project_id=project_id, upload=upload)
        except storage.UnsupportedFormatError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        photo = Photo(
            project_id=project_id,
            original_filename=stored.original_filename,
            stored_path=str(stored.relative_path),
            size_bytes=stored.size_bytes,
            width=stored.width,
            height=stored.height,
            mime_type=stored.mime_type,
        )
        db.add(photo)
        saved.append(photo)

    db.commit()
    for photo in saved:
        db.refresh(photo)
    return [PhotoOut.model_validate(p) for p in saved]

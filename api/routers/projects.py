from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import (
    AdjustmentVersionOut,
    PhotoOut,
    ProcessingVersionOut,
    ProcessingVersionPhotoOut,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
)
from models.photo import Photo
from models.photo_processing_version import PhotoProcessingVersion
from models.processing_job import ProcessingJob
from models.project import Project
from services import storage

router = APIRouter(prefix="/projects", tags=["projects"])


def _processing_version_out(job: ProcessingJob) -> ProcessingVersionOut:
    return ProcessingVersionOut(
        id=job.id,
        project_id=job.project_id,
        version_number=job.version_number,
        status=job.status,
        preset=job.preset,
        denoise_strength=job.denoise_strength,
        lens_distort_correct=job.lens_distort_correct,
        level_correct=job.level_correct,
        auto_crop_aspect=job.auto_crop_aspect,
        cpl_strength=job.cpl_strength,
        chroma_clean_strength=job.chroma_clean_strength,
        photo_ids=list(job.photo_ids or []),
        progress=job.progress,
        total=job.total,
        error=job.error,
        retry_scope=job.retry_scope,
        retry_of_job_id=job.retry_of_job_id,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def _photo_out(photo: Photo, versions: dict[UUID, list[ProcessingVersionPhotoOut]]) -> PhotoOut:
    return PhotoOut(
        id=photo.id,
        project_id=photo.project_id,
        original_filename=photo.original_filename,
        size_bytes=photo.size_bytes,
        width=photo.width,
        height=photo.height,
        mime_type=photo.mime_type,
        uploaded_at=photo.uploaded_at,
        processed_paths=dict(photo.processed_paths or {}),
        adjustment_params=photo.adjustment_params,
        adjustment_versions=[
            AdjustmentVersionOut.model_validate(version)
            for version in (photo.adjustment_versions or [])
        ],
        processing_versions=versions.get(photo.id, []),
    )


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
    jobs = (
        db.execute(
            select(ProcessingJob)
            .where(ProcessingJob.project_id == project_id, ProcessingJob.archived_at.is_(None))
            .order_by(ProcessingJob.version_number.desc())
        )
        .scalars()
        .all()
    )
    photo_version_rows = (
        db.execute(
            select(PhotoProcessingVersion, ProcessingJob.version_number)
            .join(ProcessingJob, ProcessingJob.id == PhotoProcessingVersion.processing_job_id)
            .where(ProcessingJob.project_id == project_id, ProcessingJob.archived_at.is_(None))
            .order_by(ProcessingJob.version_number.desc(), PhotoProcessingVersion.created_at.desc())
        )
        .all()
    )
    versions_by_photo: dict[UUID, list[ProcessingVersionPhotoOut]] = {}
    for version, version_number in photo_version_rows:
        versions_by_photo.setdefault(version.photo_id, []).append(
            ProcessingVersionPhotoOut(
                processing_job_id=version.processing_job_id,
                version_number=version_number,
                status=version.status,
                path=version.path,
                error=version.error,
                created_at=version.created_at,
            )
        )
    return ProjectDetail(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        photo_count=len(photos),
        photos=[_photo_out(p, versions_by_photo) for p in photos],
        processing_versions=[_processing_version_out(job) for job in jobs],
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

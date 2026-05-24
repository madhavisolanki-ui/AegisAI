from typing import Any, List, Optional
from uuid import UUID
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem
from app.models.audit_log import AISystemAuditLog
from app.schemas.ai_system import (
    AISystemCreate,
    AISystemResponse,
    AISystemUpdate,
    BulkImportResponse,
    ComplianceStatusUpdateSchema,
)
from app.schemas.audit_log import AISystemAuditLogResponse
from app.schemas.pagination import PaginatedResponse
from app.modules.grc import ai_system_service

router = APIRouter()

@router.post("/", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def register_ai_system(
    payload: AISystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Register a new AI system in the GRC platform.

    Args:
        payload (AISystemCreate): The schema containing details of the AI system to register.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        AISystemResponse: The created AI system database record.
    """
    return ai_system_service.create_system(db=db, system_in=payload, owner_id=current_user.id)


_SORTABLE_FIELDS = {
    "name": AISystem.name,
    "risk_level": AISystem.risk_level,
    "compliance_score": AISystem.compliance_score,
    "created_at": AISystem.created_at,
}


@router.get("/", response_model=PaginatedResponse[AISystemResponse])
def list_ai_systems(
    sort_by: Optional[str] = Query("created_at", description="Sort field: name, risk_level, compliance_score, created_at"),
    order: Optional[str] = Query("desc", description="Sort direction: asc, desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve a paginated and optionally sorted list of registered AI systems.

    Args:
        sort_by (Optional[str]): Field name to sort the results by.
        order (Optional[str]): Direction of sorting ('asc' or 'desc').
        page (int): Active page number for data chunking.
        limit (int): Total number of records per page.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        PaginatedResponse[AISystemResponse]: Wrapped list of systems with metadata.
    """
    if sort_by not in _SORTABLE_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by '{sort_by}'. Allowed: {', '.join(sorted(_SORTABLE_FIELDS))}",
        )
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order. Use 'asc' or 'desc'.",
        )

    column = _SORTABLE_FIELDS[sort_by]
    direction = asc(column) if order == "asc" else desc(column)

    base_query = db.query(AISystem).filter(AISystem.owner_id == current_user.id)
    total = base_query.count()
    offset = (page - 1) * limit

    systems = (
        base_query
        .order_by(direction)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(items=systems, total=total, page=page, limit=limit)


@router.post("/import", response_model=BulkImportResponse)
def bulk_import_systems(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Import multiple AI systems concurrently from an uploaded CSV spreadsheet file.

    Args:
        file (UploadFile): The raw multi-part form uploaded CSV file.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        BulkImportResponse: Report consisting of creation count and a dictionary array of row validation errors.
    """
    errors = []
    created_count = 0

    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV format: File must have .csv extension"
        )

    try:
        content = file.file.read()
        decoded_content = content.decode("utf-8")

        if not decoded_content.strip():
            return BulkImportResponse(created=0, errors=[])

        f = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(f)

        if not csv_reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV format: No headers found"
            )

        for row_num, row in enumerate(csv_reader, start=2):
            if not any(row.values()):
                continue

            name = row.get("name", "").strip()
            if not name:
                errors.append({"row": row_num, "error": "name is required"})
                continue

            existing = db.query(AISystem).filter(
                AISystem.owner_id == current_user.id,
                AISystem.name == name
            ).first()

            if existing:
                errors.append({"row": row_num, "error": f"duplicate name '{name}'"})
                continue

            try:
                ai_system = AISystem(
                    owner_id=current_user.id,
                    name=name,
                    description=row.get("description", "").strip() or None,
                    version=row.get("version", "").strip() or None,
                    use_case=row.get("use_case", "").strip() or None,
                    sector=row.get("sector", "").strip() or None
                )
                db.add(ai_system)
                created_count += 1
            except Exception as e:
                errors.append({"row": row_num, "error": str(e)})

        db.commit()

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded CSV"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )

    return BulkImportResponse(created=created_count, errors=errors)


@router.get("/export")
def export_ai_systems(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: minimal, limited, high, unacceptable"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Export the authenticated user's AI systems registry as a downloadable CSV document stream.

    Args:
        risk_level (Optional[str]): Optional categorization filter parameter.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        StreamingResponse: Text/csv file download response.
    """
    query = db.query(AISystem).filter(AISystem.owner_id == current_user.id)

    if risk_level is not None:
        allowed = {"minimal", "limited", "high", "unacceptable"}
        if risk_level.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level '{risk_level}'. Allowed: {', '.join(sorted(allowed))}",
            )
        query = query.filter(AISystem.risk_level == risk_level.lower())

    systems = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "description", "version", "use_case", "sector",
        "risk_level", "compliance_status", "compliance_score", "created_at",
    ])
    for s in systems:
        writer.writerow([
            s.id,
            s.name,
            s.description or "",
            s.version or "",
            s.use_case or "",
            s.sector or "",
            s.risk_level.value if s.risk_level else "",
            s.compliance_status.value if s.compliance_status else "",
            s.compliance_score if s.compliance_score is not None else "",
            s.created_at.isoformat() if s.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"ai_systems.csv\""},
    )


@router.get("/{system_id}/history", response_model=PaginatedResponse[AISystemAuditLogResponse])
def get_ai_system_history(
    system_id: UUID,
    order: Optional[str] = Query("desc", description="Sort direction for changed_at: asc, desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get paginated and sorted sequential change history records for an internal audit log trail.

    Args:
        system_id (UUID): The targeted system identifier.
        order (Optional[str]): Operational sorting direction for the timestamp field.
        page (int): Chunk counter identifier.
        limit (int): System ceiling constraint for array returns.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        PaginatedResponse[AISystemAuditLogResponse]: Object wrapper encapsulating raw row structures.
    """
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order parameter. Use 'asc' or 'desc'.",
        )

    system = (
        db.query(AISystem)
        .filter(
            AISystem.id == system_id,
            AISystem.owner_id == current_user.id,
        )
        .first()
    )

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    base_query = (
        db.query(AISystemAuditLog)
        .filter(AISystemAuditLog.ai_system_id == system_id)
    )

    total = base_query.count()
    direction = asc(AISystemAuditLog.changed_at) if order == "asc" else desc(AISystemAuditLog.changed_at)

    logs = (
        base_query
        .order_by(direction)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=logs,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{system_id}", response_model=AISystemResponse)
def get_ai_system(
    system_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the detailed profile of a specific AI system by its ID.

    Args:
        system_id (UUID): The unique identifier of the AI system.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        AISystemResponse: The AI system details if found.
    """
    system = ai_system_service.get_system(db=db, system_id=system_id)
    if not system or system.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI System not found"
        )
    return system


@router.put("/{system_id}", response_model=AISystemResponse)
def update_ai_system(
    system_id: UUID,
    payload: AISystemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update an existing AI system's details or compliance metadata.

    Args:
        system_id (UUID): The unique identifier of the AI system to update.
        payload (AISystemUpdate): The fields to update.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        AISystemResponse: The updated AI system database record.
    """
    system = ai_system_service.get_system(db=db, system_id=system_id)
    if not system or system.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI System not found"
        )
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(system, field, value)
    
    system._changed_by_id = current_user.id
    db.commit()
    db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_system(
    system_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete an AI system from the registry.

    Args:
        system_id (UUID): The unique identifier of the AI system to delete.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        None
    """
    system = ai_system_service.get_system(db=db, system_id=system_id)
    if not system or system.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI System not found"
        )
    ai_system_service.delete_system(db=db, system_id=system_id)


@router.patch("/{system_id}/status", response_model=AISystemResponse)
def update_ai_system_status(
    system_id: UUID,
    payload: ComplianceStatusUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Partially update only the operational compliance status state enumerator of a registered entity.

    Args:
        system_id (UUID): Target system identifier mapping.
        payload (ComplianceStatusUpdateSchema): Pydantic input body containing the targeted field status state.
        db (Session): The database session dependency.
        current_user (User): The currently authenticated user.

    Returns:
        AISystemResponse: The modified data entity row.
    """
    system = ai_system_service.get_system(db=db, system_id=system_id)
    if not system or system.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    system.compliance_status = payload.compliance_status
    system._changed_by_id = current_user.id
    db.commit()
    db.refresh(system)
    return system
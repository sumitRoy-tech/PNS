from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import SessionLocal, ProjectCredential, PublishRFP, VendorBid
from datetime import datetime
import random

router = APIRouter(prefix="/publish", tags=["Publish RFP"])

# ==================== VENDOR LIST ====================
VENDORS = [
    "TCS Ltd",
    "Infosys Tech",
    "Wipro Ltd",
    "HCL Tech",
    "Tech Mahindra",
    "LTIMindtree",
    "Persistent Systems",
    "Coforge",
    "Mphasis",
    "Zensar Technologies"
]

def generate_scores():
    tech = round(random.uniform(40, 70), 1)
    comm = round(random.uniform(20, 50), 1)

    if tech + comm >= 100:
        comm = round(99.9 - tech, 1)

    return tech, comm, round(tech + comm, 1)
# ==================== RANDOM VENDORS API ====================

@router.get("/get_vendors")
def get_random_vendors():
    """Get random vendors with their bid status"""
    selected_vendors = random.sample(VENDORS, random.randint(3, len(VENDORS)))
    vendor_data = []
    complete_count = 0
    incomplete_count = 0
    
    for vendor in selected_vendors:
        technical = random.randint(0, 1)
        commercial = random.randint(0, 1)
        emd = random.randint(0, 1)
        status = "Received" if technical == 1 and commercial == 1 and emd == 1 else "Incomplete"
        
        if status == "Received":
            complete_count += 1
        else:
            incomplete_count += 1
        
        vendor_data.append({
            "vendor_name": vendor,
            "Technical Bid": technical,
            "Commercial Bid": commercial,
            "EMD": emd,
            "status": status
        })
    
    return {
        "total_vendors": len(selected_vendors),
        "total_complete_bids": complete_count,
        "total_incomplete_bids": incomplete_count,
        "vendors": vendor_data
    }


class PublishRFPRequest(BaseModel):
    project_id: str
    bank_website: int 
    cppp: int 
    newspaper_publication: int
    gem_portal: int  
    publication_date: Optional[str] = None  
    pre_bid_meeting: Optional[str] = None  
    query_last_date: Optional[str] = None 
    bid_opening_date: Optional[str] = None  

def parse_date(value: str) -> datetime:
    """
    Parse date from various formats
    """
    if not value or value.strip() == "":
        return None
    
    value = value.strip()
    
 
    formats = ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%m-%d-%Y"]
    
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    
    raise HTTPException(
        status_code=400,
        detail=f"Invalid date format: {value}. Expected format: mm/dd/yyyy"
    )


def validate_radio_value(value: int, field_name: str) -> int:
    """Validate that value is 0 or 1"""
    if value not in [0, 1]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for {field_name}. Must be 0 or 1"
        )
    return value
@router.post("/submit")
def submit_publish_rfp(request: PublishRFPRequest):
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        bank_website = validate_radio_value(request.bank_website, "bank_website")
        cppp = validate_radio_value(request.cppp, "cppp")
        newspaper_publication = validate_radio_value(request.newspaper_publication, "newspaper_publication")
        gem_portal = validate_radio_value(request.gem_portal, "gem_portal")
        
        publication_date = parse_date(request.publication_date) if request.publication_date else None
        pre_bid_meeting = parse_date(request.pre_bid_meeting) if request.pre_bid_meeting else None
        query_last_date = parse_date(request.query_last_date) if request.query_last_date else None
        bid_opening_date = parse_date(request.bid_opening_date) if request.bid_opening_date else None
        
        existing = db.query(PublishRFP).filter(
            PublishRFP.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            existing.bank_website = bank_website
            existing.cppp = cppp
            existing.newspaper_publication = newspaper_publication
            existing.gem_portal = gem_portal
            existing.publication_date = publication_date
            existing.pre_bid_meeting = pre_bid_meeting
            existing.query_last_date = query_last_date
            existing.bid_opening_date = bid_opening_date
            
            db.commit()
            db.refresh(existing)
            
            return {
                "message": "Publish RFP updated successfully",
                "publish_id": existing.id,
                "project_id": project.id,
                "project_title": project.title,
                "data": {
                    "bank_website": existing.bank_website,
                    "cppp": existing.cppp,
                    "newspaper_publication": existing.newspaper_publication,
                    "gem_portal": existing.gem_portal,
                    "publication_date": existing.publication_date.strftime("%Y-%m-%d") if existing.publication_date else None,
                    "pre_bid_meeting": existing.pre_bid_meeting.strftime("%Y-%m-%d") if existing.pre_bid_meeting else None,
                    "query_last_date": existing.query_last_date.strftime("%Y-%m-%d") if existing.query_last_date else None,
                    "bid_opening_date": existing.bid_opening_date.strftime("%Y-%m-%d") if existing.bid_opening_date else None
                },
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
                "updated_at": existing.updated_at.isoformat() if existing.updated_at else None
            }
        
        else:
            # Create new
            publish_rfp = PublishRFP(
                project_pk_id=project.pk_id,
                project_id=project.id,
                bank_website=bank_website,
                cppp=cppp,
                newspaper_publication=newspaper_publication,
                gem_portal=gem_portal,
                publication_date=publication_date,
                pre_bid_meeting=pre_bid_meeting,
                query_last_date=query_last_date,
                bid_opening_date=bid_opening_date
            )
            
            db.add(publish_rfp)
            db.commit()
            db.refresh(publish_rfp)
            
            return {
                "message": "Publish RFP submitted successfully",
                "publish_id": publish_rfp.id,
                "project_id": project.id,
                "project_title": project.title,
                "data": {
                    "bank_website": publish_rfp.bank_website,
                    "cppp": publish_rfp.cppp,
                    "newspaper_publication": publish_rfp.newspaper_publication,
                    "gem_portal": publish_rfp.gem_portal,
                    "publication_date": publish_rfp.publication_date.strftime("%Y-%m-%d") if publish_rfp.publication_date else None,
                    "pre_bid_meeting": publish_rfp.pre_bid_meeting.strftime("%Y-%m-%d") if publish_rfp.pre_bid_meeting else None,
                    "query_last_date": publish_rfp.query_last_date.strftime("%Y-%m-%d") if publish_rfp.query_last_date else None,
                    "bid_opening_date": publish_rfp.bid_opening_date.strftime("%Y-%m-%d") if publish_rfp.bid_opening_date else None
                },
                "created_at": publish_rfp.created_at.isoformat() if publish_rfp.created_at else None
            }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


# ==================== GET APIs ====================

@router.get("/list")
def get_all_publish_rfps():
    """Get all published RFPs"""
    db = SessionLocal()
    
    try:
        records = db.query(PublishRFP).order_by(PublishRFP.created_at.desc()).all()
        
        result = []
        for record in records:
            project = db.query(ProjectCredential).filter(
                ProjectCredential.pk_id == record.project_pk_id
            ).first()
            
            result.append({
                "id": record.id,
                "project_id": record.project_id,
                "project_title": project.title if project else None,
                "bank_website": record.bank_website,
                "cppp": record.cppp,
                "newspaper_publication": record.newspaper_publication,
                "gem_portal": record.gem_portal,
                "publication_date": record.publication_date.strftime("%Y-%m-%d") if record.publication_date else None,
                "pre_bid_meeting": record.pre_bid_meeting.strftime("%Y-%m-%d") if record.pre_bid_meeting else None,
                "query_last_date": record.query_last_date.strftime("%Y-%m-%d") if record.query_last_date else None,
                "bid_opening_date": record.bid_opening_date.strftime("%Y-%m-%d") if record.bid_opening_date else None,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None
            })
        
        return {
            "total_records": len(result),
            "publish_rfps": result
        }
    
    finally:
        db.close()


@router.get("/{project_id}")
def get_publish_rfp_by_project(project_id: str):
    """Get publish RFP data for a specific project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        publish_rfp = db.query(PublishRFP).filter(
            PublishRFP.project_pk_id == project.pk_id
        ).first()
        
        if not publish_rfp:
            raise HTTPException(status_code=404, detail="No publish RFP data found for this project")
        
        return {
            "project_id": project.id,
            "project_title": project.title,
            "publish_rfp": {
                "id": publish_rfp.id,
                "bank_website": publish_rfp.bank_website,
                "cppp": publish_rfp.cppp,
                "newspaper_publication": publish_rfp.newspaper_publication,
                "gem_portal": publish_rfp.gem_portal,
                "publication_date": publish_rfp.publication_date.strftime("%Y-%m-%d") if publish_rfp.publication_date else None,
                "pre_bid_meeting": publish_rfp.pre_bid_meeting.strftime("%Y-%m-%d") if publish_rfp.pre_bid_meeting else None,
                "query_last_date": publish_rfp.query_last_date.strftime("%Y-%m-%d") if publish_rfp.query_last_date else None,
                "bid_opening_date": publish_rfp.bid_opening_date.strftime("%Y-%m-%d") if publish_rfp.bid_opening_date else None,
                "created_at": publish_rfp.created_at.isoformat() if publish_rfp.created_at else None,
                "updated_at": publish_rfp.updated_at.isoformat() if publish_rfp.updated_at else None
            }
        }
    
    finally:
        db.close()


# ==================== VENDOR BIDS APIs ====================

class VendorBidRequest(BaseModel):
    project_id: str
    vendors: List[dict]


@router.post("/vendor-bids/submit")
def submit_vendor_bids(request: VendorBidRequest):
    """Submit vendor bids for a project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not request.vendors or len(request.vendors) == 0:
            raise HTTPException(status_code=400, detail="At least one vendor is required")
        
        # Delete existing vendor bids for this project
        db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).delete()
        
        # Filter only vendors with status "Received"
        received_vendors = [v for v in request.vendors if v.get("status") == "Received"]
        
        if len(received_vendors) == 0:
            raise HTTPException(status_code=400, detail="No vendors with 'Received' status found")
        
        # Generate random bids for each received vendor
        vendor_data = []
        for vendor in received_vendors:
            vendor_name = vendor.get("vendor_name")
            commercial_bid = random.randint(15000000, 95000000)
            technical_score = random.randint(60, 100)
            vendor_data.append({
                "vendor_name": vendor_name,
                "commercial_bid": commercial_bid,
                "technical_score": technical_score
            })
        
        # Sort by commercial bid (lowest first) and assign ranks
        vendor_data.sort(key=lambda x: x["commercial_bid"])
        
        # Create vendor bid records with ranks
        created_bids = []
        for rank, vendor in enumerate(vendor_data, start=1):
            vendor_bid = VendorBid(
                project_pk_id=project.pk_id,
                project_id=project.id,
                vendor_name=vendor["vendor_name"],
                commercial_bid=vendor["commercial_bid"],
                technical_score=vendor["technical_score"],
                rank=rank
            )
            db.add(vendor_bid)
            created_bids.append({
                "vendor_name": vendor["vendor_name"],
                "commercial_bid": vendor["commercial_bid"],
                "technical_score": vendor["technical_score"],
                "rank": rank
            })
        
        db.commit()
        
        return {
            "message": "Vendor bids submitted successfully",
            "project_id": project.id,
            "project_title": project.title,
            "total_vendors_received": len(request.vendors),
            "total_qualified_vendors": len(created_bids),
            "vendor_bids": created_bids
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        db.close()


@router.get("/vendor-bids/{project_id}")
def get_vendor_bids(project_id: str):
    """Get all vendor bids for a project"""
    db = SessionLocal()
    
    try:
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        bids = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).order_by(VendorBid.rank).all()
        
        if not bids:
            raise HTTPException(status_code=404, detail="No vendor bids found for this project")
        
        return {
            "project_id": project.id,
            "project_title": project.title,
            "total_vendors": len(bids),
            "vendor_bids": [
                {
                    "id": bid.id,
                    "vendor_name": bid.vendor_name,
                    "commercial_bid": bid.commercial_bid,
                    "technical_score": bid.technical_score,
                    "rank": bid.rank,
                    "created_at": bid.created_at.isoformat() if bid.created_at else None
                }
                for bid in bids
            ]
        }
    
    finally:
        db.close()


@router.get("/vendor-bids/list/all")
def get_all_vendor_bids():
    """Get all vendor bids across all projects"""
    db = SessionLocal()
    
    try:
        bids = db.query(VendorBid).order_by(VendorBid.project_id, VendorBid.rank).all()
        
        result = []
        for bid in bids:
            project = db.query(ProjectCredential).filter(
                ProjectCredential.pk_id == bid.project_pk_id
            ).first()
            
            result.append({
                "id": bid.id,
                "project_id": bid.project_id,
                "project_title": project.title if project else None,
                "vendor_name": bid.vendor_name,
                "commercial_bid": bid.commercial_bid,
                "technical_score": bid.technical_score,
                "rank": bid.rank,
                "created_at": bid.created_at.isoformat() if bid.created_at else None
            })
        
        return {
            "total_bids": len(result),
            "bids": result
        }
    
    finally:
        db.close()


@router.post("/vendor-evaluation/{project_id}")
def submit_vendor_evaluation(project_id: str):
    db = SessionLocal()

    try:
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")

        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        vendors = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).all()

        if not vendors:
            raise HTTPException(status_code=404, detail="No vendor bids found")

        # Get publication date from PublishRFP table
        publish_rfp = db.query(PublishRFP).filter(
            PublishRFP.project_pk_id == project.pk_id
        ).first()

        publication_date = None
        if publish_rfp and publish_rfp.publication_date:
            publication_date = publish_rfp.publication_date.strftime("%Y-%m-%d")

        evaluated = []

        for vendor in vendors:
            tech, comm, total = generate_scores()

            vendor.tech_score = tech
            vendor.comm_score = comm
            vendor.total_score = total

            evaluated.append(vendor)

        evaluated.sort(key=lambda x: x.total_score, reverse=True)

        for idx, vendor in enumerate(evaluated, start=1):
            vendor.rank = idx

        db.commit()

        final_bids = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).order_by(VendorBid.rank).all()

        # ✅ WINNER (Rank 1) - Now includes publication_date
        winner = {
            "vendor_name": final_bids[0].vendor_name,
            "commercial_bid": final_bids[0].commercial_bid,
            "publication_date": publication_date
        }

        return {
            "message": "Vendor bids submitted successfully",
            "project_id": project.id,
            "project_title": project.title,
            "total_vendors_received": len(final_bids),
            "total_qualified_vendors": len(final_bids),
            "winner": winner,
            "vendor_bids": [
                {
                    "vendor_name": v.vendor_name,
                    "tech_score": v.tech_score,
                    "comm_score": v.comm_score,
                    "total_score": v.total_score,
                    "commercial_bid": v.commercial_bid,
                    "technical_score": v.technical_score,
                    "rank": v.rank
                }
                for v in final_bids
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

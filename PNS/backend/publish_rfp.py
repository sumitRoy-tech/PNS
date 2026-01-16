import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import SessionLocal, ProjectCredential, PublishRFP, VendorBid
from datetime import datetime
import random

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("PUBLISH RFP MODULE INITIALIZATION STARTED")
logger.info("=" * 60)

router = APIRouter(prefix="/publish", tags=["Publish RFP"])
logger.info("Router created with prefix: /publish")
logger.info("Tags: ['Publish RFP']")

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
logger.info(f"Vendor list initialized with {len(VENDORS)} vendors:")
for vendor in VENDORS:
    logger.info(f"  - {vendor}")

logger.info("=" * 60)
logger.info("PUBLISH RFP MODULE INITIALIZED SUCCESSFULLY")
logger.info("=" * 60)


def generate_scores():
    logger.debug("Generating random scores for vendor evaluation...")
    tech = round(random.uniform(40, 70), 1)
    comm = round(random.uniform(20, 50), 1)

    if tech + comm >= 100:
        logger.debug(f"Score adjustment needed: tech={tech}, comm={comm}, total={tech+comm}")
        comm = round(99.9 - tech, 1)

    total = round(tech + comm, 1)
    logger.debug(f"Generated scores: tech={tech}, comm={comm}, total={total}")
    return tech, comm, total


# ==================== RANDOM VENDORS API ====================

@router.get("/get_vendors")
def get_random_vendors():
    """Get random vendors with their bid status"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /publish/get_vendors")
    logger.info("=" * 60)

    logger.info(f"Selecting random vendors from pool of {len(VENDORS)}...")
    selected_vendors = random.sample(VENDORS, random.randint(3, len(VENDORS)))
    logger.info(f"Selected {len(selected_vendors)} vendors")
    
    vendor_data = []
    complete_count = 0
    incomplete_count = 0

    for vendor in selected_vendors:
        technical = random.randint(0, 1)
        commercial = random.randint(0, 1)
        emd = random.randint(0, 1)

        status = (
            "Received"
            if technical == 1 and commercial == 1 and emd == 1
            else "Incomplete"
        )

        if status == "Received":
            complete_count += 1
        else:
            incomplete_count += 1

        logger.debug(f"  Vendor: {vendor} - Technical={technical}, Commercial={commercial}, EMD={emd}, Status={status}")

        vendor_data.append({
            "vendor_name": vendor,
            "Technical Bid": technical,
            "Commercial Bid": commercial,
            "EMD": emd,
            "status": status
        })

    logger.info(f"Complete bids: {complete_count}, Incomplete bids: {incomplete_count}")

    # Edge case: No complete bids
    if complete_count == 0:
        logger.warning("No complete bids found - adding fallback vendor 'Nirvana Tech'")
        fallback_vendor = {
            "vendor_name": "Nirvana Tech",
            "Technical Bid": 1,
            "Commercial Bid": 1,
            "EMD": 1,
            "status": "Received"
        }

        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /publish/get_vendors - SUCCESS (with fallback)")
        logger.info(f"Total vendors: {len(selected_vendors) + 1}")
        logger.info("=" * 60)

        return {
            "total_vendors": len(selected_vendors) + 1,
            "total_complete_bids": 1,
            "total_incomplete_bids": incomplete_count,
            "vendors": vendor_data + [fallback_vendor]
        }

    logger.info("=" * 60)
    logger.info("API RESPONSE: GET /publish/get_vendors - SUCCESS")
    logger.info(f"Total vendors: {len(selected_vendors)}")
    logger.info(f"Complete: {complete_count}, Incomplete: {incomplete_count}")
    logger.info("=" * 60)

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
    logger.debug(f"Parsing date value: '{value}'")
    
    if not value or value.strip() == "":
        logger.debug("Empty date value, returning None")
        return None
    
    value = value.strip()
    
    formats = ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%m-%d-%Y"]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            logger.debug(f"Successfully parsed date with format '{fmt}': {parsed}")
            return parsed
        except ValueError:
            continue
    
    logger.error(f"Failed to parse date: '{value}' - no matching format found")
    raise HTTPException(
        status_code=400,
        detail=f"Invalid date format: {value}. Expected format: mm/dd/yyyy"
    )


def validate_radio_value(value: int, field_name: str) -> int:
    """Validate that value is 0 or 1"""
    logger.debug(f"Validating radio value for {field_name}: {value}")
    if value not in [0, 1]:
        logger.error(f"Invalid radio value for {field_name}: {value} (must be 0 or 1)")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for {field_name}. Must be 0 or 1"
        )
    logger.debug(f"Validation passed for {field_name}: {value}")
    return value


@router.post("/submit")
def submit_publish_rfp(request: PublishRFPRequest):
    logger.info("=" * 60)
    logger.info("API CALLED: POST /publish/submit")
    logger.info("=" * 60)
    logger.info("Request Parameters:")
    logger.info(f"  - project_id: {request.project_id}")
    logger.info(f"  - bank_website: {request.bank_website}")
    logger.info(f"  - cppp: {request.cppp}")
    logger.info(f"  - newspaper_publication: {request.newspaper_publication}")
    logger.info(f"  - gem_portal: {request.gem_portal}")
    logger.info(f"  - publication_date: {request.publication_date}")
    logger.info(f"  - pre_bid_meeting: {request.pre_bid_meeting}")
    logger.info(f"  - query_last_date: {request.query_last_date}")
    logger.info(f"  - bid_opening_date: {request.bid_opening_date}")

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {request.project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {request.project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        logger.info("Validating radio values...")
        bank_website = validate_radio_value(request.bank_website, "bank_website")
        cppp = validate_radio_value(request.cppp, "cppp")
        newspaper_publication = validate_radio_value(request.newspaper_publication, "newspaper_publication")
        gem_portal = validate_radio_value(request.gem_portal, "gem_portal")
        logger.info("All radio values validated successfully")
        
        logger.info("Parsing date values...")
        publication_date = parse_date(request.publication_date) if request.publication_date else None
        pre_bid_meeting = parse_date(request.pre_bid_meeting) if request.pre_bid_meeting else None
        query_last_date = parse_date(request.query_last_date) if request.query_last_date else None
        bid_opening_date = parse_date(request.bid_opening_date) if request.bid_opening_date else None
        logger.info("All dates parsed successfully")
        logger.info(f"  - publication_date: {publication_date}")
        logger.info(f"  - pre_bid_meeting: {pre_bid_meeting}")
        logger.info(f"  - query_last_date: {query_last_date}")
        logger.info(f"  - bid_opening_date: {bid_opening_date}")
        
        logger.info(f"Checking for existing PublishRFP record for project pk_id: {project.pk_id}")
        existing = db.query(PublishRFP).filter(
            PublishRFP.project_pk_id == project.pk_id
        ).first()
        
        if existing:
            logger.info(f"Existing record found with id: {existing.id}")
            logger.info("Updating existing PublishRFP record...")
            
            existing.bank_website = bank_website
            existing.cppp = cppp
            existing.newspaper_publication = newspaper_publication
            existing.gem_portal = gem_portal
            existing.publication_date = publication_date
            existing.pre_bid_meeting = pre_bid_meeting
            existing.query_last_date = query_last_date
            existing.bid_opening_date = bid_opening_date
            
            logger.info("Committing transaction...")
            db.commit()
            logger.info("Transaction committed successfully")
            
            logger.info("Refreshing record...")
            db.refresh(existing)
            
            logger.info("=" * 60)
            logger.info("API RESPONSE: POST /publish/submit - SUCCESS (UPDATE)")
            logger.info(f"Updated publish_id: {existing.id}")
            logger.info("=" * 60)
            
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
            logger.info("No existing record found. Creating new PublishRFP record...")
            
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
            
            logger.info("Adding new record to database session...")
            db.add(publish_rfp)
            
            logger.info("Committing transaction...")
            db.commit()
            logger.info("Transaction committed successfully")
            
            logger.info("Refreshing record...")
            db.refresh(publish_rfp)
            logger.info(f"New record created with id: {publish_rfp.id}")
            
            logger.info("=" * 60)
            logger.info("API RESPONSE: POST /publish/submit - SUCCESS (CREATE)")
            logger.info(f"Created publish_id: {publish_rfp.id}")
            logger.info("=" * 60)
            
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
        logger.error(f"Error in submit_publish_rfp: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


# ==================== GET APIs ====================

@router.get("/list")
def get_all_publish_rfps():
    """Get all published RFPs"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /publish/list")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info("Querying all PublishRFP records ordered by created_at DESC...")
        records = db.query(PublishRFP).order_by(PublishRFP.created_at.desc()).all()
        logger.info(f"Found {len(records)} PublishRFP records")
        
        result = []
        for idx, record in enumerate(records):
            logger.debug(f"Processing record {idx + 1}/{len(records)}: id={record.id}")
            
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
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /publish/list - SUCCESS")
        logger.info(f"Returning {len(result)} records")
        logger.info("=" * 60)
        
        return {
            "total_records": len(result),
            "publish_rfps": result
        }
    
    except Exception as e:
        logger.error(f"Error in get_all_publish_rfps: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/{project_id}")
def get_publish_rfp_by_project(project_id: str):
    """Get publish RFP data for a specific project"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /publish/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        logger.info(f"Querying PublishRFP for project pk_id: {project.pk_id}")
        publish_rfp = db.query(PublishRFP).filter(
            PublishRFP.project_pk_id == project.pk_id
        ).first()
        
        if not publish_rfp:
            logger.warning(f"No PublishRFP data found for project: {project_id}")
            logger.error("Raising HTTPException 404: No publish RFP data found")
            raise HTTPException(status_code=404, detail="No publish RFP data found for this project")
        
        logger.info(f"PublishRFP record found with id: {publish_rfp.id}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /publish/{project_id} - SUCCESS")
        logger.info(f"Returning PublishRFP data for project: {project_id}")
        logger.info("=" * 60)
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_publish_rfp_by_project: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


# ==================== VENDOR BIDS APIs ====================

class VendorBidRequest(BaseModel):
    project_id: str
    vendors: List[dict]


@router.post("/vendor-bids/submit")
def submit_vendor_bids(request: VendorBidRequest):
    """Submit vendor bids for a project"""
    logger.info("=" * 60)
    logger.info("API CALLED: POST /publish/vendor-bids/submit")
    logger.info("=" * 60)
    logger.info("Request Parameters:")
    logger.info(f"  - project_id: {request.project_id}")
    logger.info(f"  - vendors count: {len(request.vendors)}")
    for idx, vendor in enumerate(request.vendors):
        logger.debug(f"  Vendor {idx + 1}: {vendor}")

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {request.project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == request.project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {request.project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        if not request.vendors or len(request.vendors) == 0:
            logger.warning("No vendors provided in request")
            logger.error("Raising HTTPException 400: At least one vendor is required")
            raise HTTPException(status_code=400, detail="At least one vendor is required")
        
        # Delete existing vendor bids for this project
        logger.info(f"Deleting existing vendor bids for project pk_id: {project.pk_id}")
        deleted_count = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).delete()
        logger.info(f"Deleted {deleted_count} existing vendor bids")
        
        # Filter only vendors with status "Received"
        logger.info("Filtering vendors with status 'Received'...")
        received_vendors = [v for v in request.vendors if v.get("status") == "Received"]
        logger.info(f"Found {len(received_vendors)} vendors with 'Received' status")
        
        if len(received_vendors) == 0:
            logger.warning("No vendors with 'Received' status found")
            logger.error("Raising HTTPException 400: No vendors with 'Received' status")
            raise HTTPException(status_code=400, detail="No vendors with 'Received' status found")
        
        # Generate random bids for each received vendor
        logger.info("Generating random bids for received vendors...")
        vendor_data = []
        for vendor in received_vendors:
            vendor_name = vendor.get("vendor_name")
            commercial_bid = random.randint(15000000, 95000000)
            technical_score = random.randint(60, 100)
            logger.debug(f"  {vendor_name}: commercial_bid={commercial_bid}, technical_score={technical_score}")
            vendor_data.append({
                "vendor_name": vendor_name,
                "commercial_bid": commercial_bid,
                "technical_score": technical_score
            })
        
        # Sort by commercial bid (lowest first) and assign ranks
        logger.info("Sorting vendors by commercial bid (lowest first)...")
        vendor_data.sort(key=lambda x: x["commercial_bid"])
        
        # Create vendor bid records with ranks
        logger.info("Creating VendorBid records...")
        created_bids = []
        for rank, vendor in enumerate(vendor_data, start=1):
            logger.debug(f"  Creating bid for {vendor['vendor_name']} with rank {rank}")
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
        
        logger.info(f"Created {len(created_bids)} VendorBid records")
        
        logger.info("Committing transaction...")
        db.commit()
        logger.info("Transaction committed successfully")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /publish/vendor-bids/submit - SUCCESS")
        logger.info(f"Total vendors received: {len(request.vendors)}")
        logger.info(f"Total qualified vendors: {len(created_bids)}")
        logger.info("=" * 60)
        
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
        logger.error(f"Error in submit_vendor_bids: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/vendor-bids/{project_id}")
def get_vendor_bids(project_id: str):
    """Get all vendor bids for a project"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /publish/vendor-bids/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()
        
        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")
        
        logger.info(f"Querying VendorBid records for project pk_id: {project.pk_id}")
        bids = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).order_by(VendorBid.rank).all()
        
        if not bids:
            logger.warning(f"No vendor bids found for project: {project_id}")
            logger.error("Raising HTTPException 404: No vendor bids found")
            raise HTTPException(status_code=404, detail="No vendor bids found for this project")
        
        logger.info(f"Found {len(bids)} vendor bids")
        for bid in bids:
            logger.debug(f"  Rank {bid.rank}: {bid.vendor_name} - Commercial: {bid.commercial_bid}, Technical: {bid.technical_score}")
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /publish/vendor-bids/{project_id} - SUCCESS")
        logger.info(f"Returning {len(bids)} vendor bids")
        logger.info("=" * 60)
        
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
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_vendor_bids: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.get("/vendor-bids/list/all")
def get_all_vendor_bids():
    """Get all vendor bids across all projects"""
    logger.info("=" * 60)
    logger.info("API CALLED: GET /publish/vendor-bids/list/all")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")
    
    try:
        logger.info("Querying all VendorBid records ordered by project_id, rank...")
        bids = db.query(VendorBid).order_by(VendorBid.project_id, VendorBid.rank).all()
        logger.info(f"Found {len(bids)} total vendor bids")
        
        result = []
        for idx, bid in enumerate(bids):
            logger.debug(f"Processing bid {idx + 1}/{len(bids)}: id={bid.id}")
            
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
        
        logger.info("=" * 60)
        logger.info("API RESPONSE: GET /publish/vendor-bids/list/all - SUCCESS")
        logger.info(f"Returning {len(result)} vendor bids")
        logger.info("=" * 60)
        
        return {
            "total_bids": len(result),
            "bids": result
        }
    
    except Exception as e:
        logger.error(f"Error in get_all_vendor_bids: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise
    
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")


@router.post("/vendor-evaluation/{project_id}")
def submit_vendor_evaluation(project_id: str):
    logger.info("=" * 60)
    logger.info("API CALLED: POST /publish/vendor-evaluation/{project_id}")
    logger.info(f"Parameter - project_id: {project_id}")
    logger.info("=" * 60)

    logger.info("Creating database session...")
    db = SessionLocal()
    logger.info("Database session created successfully")

    try:
        if not project_id:
            logger.warning("project_id is empty or None")
            logger.error("Raising HTTPException 400: project_id is required")
            raise HTTPException(status_code=400, detail="project_id is required")

        logger.info(f"Querying project with id: {project_id}")
        project = db.query(ProjectCredential).filter(
            ProjectCredential.id == project_id
        ).first()

        if not project:
            logger.warning(f"Project not found with id: {project_id}")
            logger.error("Raising HTTPException 404: Project not found")
            raise HTTPException(status_code=404, detail="Project not found")

        logger.info(f"Project found: {project.title} (pk_id: {project.pk_id})")

        logger.info(f"Querying VendorBid records for project pk_id: {project.pk_id}")
        vendors = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).all()

        if not vendors:
            logger.warning(f"No vendor bids found for project: {project_id}")
            logger.error("Raising HTTPException 404: No vendor bids found")
            raise HTTPException(status_code=404, detail="No vendor bids found")

        logger.info(f"Found {len(vendors)} vendor bids for evaluation")

        # Get publication date from PublishRFP table
        logger.info(f"Querying PublishRFP for publication date...")
        publish_rfp = db.query(PublishRFP).filter(
            PublishRFP.project_pk_id == project.pk_id
        ).first()

        publication_date = None
        if publish_rfp and publish_rfp.publication_date:
            publication_date = publish_rfp.publication_date.strftime("%Y-%m-%d")
            logger.info(f"Publication date found: {publication_date}")
        else:
            logger.info("No publication date found")

        logger.info("Generating evaluation scores for each vendor...")
        evaluated = []

        for vendor in vendors:
            tech, comm, total = generate_scores()
            logger.debug(f"  {vendor.vendor_name}: tech={tech}, comm={comm}, total={total}")

            vendor.tech_score = tech
            vendor.comm_score = comm
            vendor.total_score = total

            evaluated.append(vendor)

        logger.info("Sorting vendors by total_score (highest first)...")
        evaluated.sort(key=lambda x: x.total_score, reverse=True)

        logger.info("Assigning ranks based on sorted order...")
        for idx, vendor in enumerate(evaluated, start=1):
            vendor.rank = idx
            logger.debug(f"  Rank {idx}: {vendor.vendor_name} (total_score={vendor.total_score})")

        logger.info("Committing transaction...")
        db.commit()
        logger.info("Transaction committed successfully")

        logger.info("Querying final bids with updated ranks...")
        final_bids = db.query(VendorBid).filter(
            VendorBid.project_pk_id == project.pk_id
        ).order_by(VendorBid.rank).all()

        # ✅ WINNER (Rank 1) - Now includes publication_date
        winner = {
            "vendor_name": final_bids[0].vendor_name,
            "commercial_bid": final_bids[0].commercial_bid,
            "publication_date": publication_date
        }
        logger.info(f"Winner determined: {winner['vendor_name']} with commercial_bid={winner['commercial_bid']}")

        logger.info("=" * 60)
        logger.info("API RESPONSE: POST /publish/vendor-evaluation/{project_id} - SUCCESS")
        logger.info(f"Total vendors evaluated: {len(final_bids)}")
        logger.info(f"Winner: {winner['vendor_name']}")
        logger.info("=" * 60)

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
        logger.error(f"Error in submit_vendor_evaluation: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.info("Rolling back transaction...")
        db.rollback()
        logger.info("Transaction rolled back")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        logger.info("Closing database session...")
        db.close()
        logger.info("Database session closed")

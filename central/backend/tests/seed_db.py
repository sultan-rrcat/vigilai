import uuid
from core.db import SessionLocal
from db.models import Camera, Zone

def seed_data():
    # Get a database session
    db = SessionLocal()
    
    # The exact UUID from your edge/.env file
    target_camera_id = uuid.UUID("b6f2b6b0-1234-4d3a-9f1a-000000000001")
    
    try:
        # 1. Check if the camera already exists
        camera = db.query(Camera).filter(Camera.id == target_camera_id).first()
        
        if not camera:
            print("Creating test camera...")
            camera = Camera(
                id=target_camera_id,
                name="Test Camera 1",
                location="Front Gate",
                rtsp_url="test_fullhd.mp4",
                status="online"
            )
            db.add(camera)
            db.commit()
            db.refresh(camera)
            print(f"✅ Created Camera: '{camera.name}' with ID: {camera.id}")
        else:
            print(f"✅ Camera already exists: '{camera.name}'")

        # 2. Check if a zone exists for this camera
        zone = db.query(Zone).filter(Zone.camera_id == camera.id).first()
        
        if not zone:
            print("Creating test zone...")
            zone = Zone(
                camera_id=camera.id,
                name="Restricted Entry",
                # The exact normalized test polygon we used on the edge
                polygon=[[0.2, 0.4], [0.8, 0.4], [0.8, 0.9], [0.2, 0.9]], 
                min_dwell_seconds=2.0
            )
            db.add(zone)
            db.commit()
            print(f"✅ Created Zone: '{zone.name}' linked to Camera: '{camera.name}'")
        else:
            print(f"✅ Zone already exists: '{zone.name}'")
            
        # 3. Test the SQLAlchemy Relationship mapping
        print(f"🔍 ORM Validation: Camera '{camera.name}' currently has {len(camera.zones)} zone(s) linked to it.")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        db.rollback()
    finally:
        # Always close the session
        db.close()

if __name__ == "__main__":
    seed_data()
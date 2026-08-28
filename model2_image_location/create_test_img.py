import os
import logging
import piexif
from PIL import Image
from typing import Tuple, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def to_deg(value: float, loc: List[str]) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], str]:
    """Convert float degrees to EXIF rational format (degrees, minutes, seconds)."""
    if value < 0:
        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
        
    abs_value = abs(value)
    deg = int(abs_value)
    t1 = (abs_value - deg) * 60
    min_val = int(t1)
    sec = round((t1 - min_val) * 60, 5)
    
    return (deg, 1), (min_val, 1), (int(sec * 100), 100), loc_value

def create_test_image_with_gps(filepath: str, lat: float, lon: float) -> None:
    """Creates a simple test image and injects GPS EXIF data."""
    try:
        # Create a simple red image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Convert lat/lon to rationals for EXIF
        lat_tuple = to_deg(lat, ["S", "N"])
        lon_tuple = to_deg(lon, ["W", "E"])

        exif_dict = {"GPS": {}}
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_tuple[3]
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = (lat_tuple[0], lat_tuple[1], lat_tuple[2])
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_tuple[3]
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = (lon_tuple[0], lon_tuple[1], lon_tuple[2])
        
        exif_bytes = piexif.dump(exif_dict)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        img.save(filepath, "jpeg", exif=exif_bytes)
        logger.info(f"Test image successfully saved to {filepath}")
    except Exception as e:
        logger.error(f"Failed to create test image: {e}")

if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "input")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "test_beijing.jpg")
    
    # Beijing coordinates
    create_test_image_with_gps(output_file, 39.9042, 116.4074)

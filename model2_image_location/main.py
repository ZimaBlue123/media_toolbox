import os
import time
import logging
from typing import Optional, Dict, Any, Tuple
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_exif_data(image_path: str) -> Optional[Dict[int, Any]]:
    '''Extract EXIF data from image.'''
    if not os.path.isfile(image_path):
        logger.error(f"Image path does not exist or is not a file: {image_path}")
        return None

    try:
        with Image.open(image_path) as image:
            image.verify()  # verify that it is, in fact, an image
        
        # We need to reopen because verify() closes it
        with Image.open(image_path) as image:
            exif_data = image._getexif()
            return exif_data
    except Exception as e:
        logger.error(f"Error reading {image_path}: {e}")
        return None

def get_gps_info(exif_data: Optional[Dict[int, Any]]) -> Dict[str, Any]:
    '''Extract GPS information from EXIF data.'''
    gps_info: Dict[str, Any] = {}
    if exif_data:
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                if isinstance(value, dict):
                    for t, val in value.items():
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_info[sub_decoded] = val
    return gps_info

def convert_to_degrees(value: Tuple[Any, Any, Any]) -> float:
    '''Convert GPS coordinates to degrees in float.'''
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ValueError, IndexError, ZeroDivisionError) as e:
        logger.warning(f"Error converting coordinates {value}: {e}")
        raise ValueError(f"Invalid coordinate value: {value}")

def get_lat_lon(gps_info: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    '''Get latitude and longitude from GPS info.'''
    lat = None
    lon = None
    
    if gps_info and "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
        try:
            lat = convert_to_degrees(gps_info["GPSLatitude"])
            if gps_info.get("GPSLatitudeRef") != "N":
                lat = 0 - lat
                
            lon = convert_to_degrees(gps_info["GPSLongitude"])
            if gps_info.get("GPSLongitudeRef") != "E":
                lon = 0 - lon
        except ValueError as e:
            logger.warning(f"Failed to parse GPS coordinates: {e}")
            lat, lon = None, None
            
    return lat, lon

def get_address_from_coords(lat: float, lon: float) -> str:
    '''Use geopy to get address from lat/lon.'''
    try:
        geolocator = Nominatim(user_agent="av_media_repair_model2")
        location = geolocator.reverse((lat, lon), language="zh-CN")
        return location.address if location else "未知地址 (Unknown address)"
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        logger.error(f"Geocoding service unavailable or timed out: {e}")
        return f"地址解析服务不可用 (Geocoding service unavailable): {e}"
    except Exception as e:
        logger.error(f"Error during geocoding: {e}")
        return f"地址解析出错 (Error during geocoding): {e}"

def process_images_in_folder(folder_path: str) -> None:
    if not os.path.exists(folder_path):
        logger.error(f"Directory '{folder_path}' does not exist.")
        return
        
    supported_formats = ('.jpg', '.jpeg', '.png', '.tiff', '.webp')
    
    try:
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(supported_formats)]
    except OSError as e:
        logger.error(f"Failed to read directory {folder_path}: {e}")
        return
    
    if not files:
        logger.info(f"No supported image formats found in '{folder_path}'.")
        return
        
    logger.info(f"Found {len(files)} images. Starting processing...")
    print("-" * 50)
    
    for filename in files:
        file_path = os.path.join(folder_path, filename)
        logger.info(f"Processing image: {filename}")
        
        exif = get_exif_data(file_path)
        if not exif:
            logger.info("  Result: No EXIF data found. Image might be compressed or stripped.")
            print("-" * 50)
            continue
            
        gps_info = get_gps_info(exif)
        if not gps_info:
            logger.info("  Result: No GPS geolocation info in EXIF data.")
            print("-" * 50)
            continue
            
        lat, lon = get_lat_lon(gps_info)
        if lat is None or lon is None:
            logger.info("  Result: GPS coordinate data invalid or missing.")
            print("-" * 50)
            continue
            
        logger.info(f"  Coordinates (Lat, Lon): {lat:.6f}, {lon:.6f}")
        address = get_address_from_coords(lat, lon)
        logger.info(f"  Resolved Address: {address}")
        print("-" * 50)
        
        # Request limit to avoid being banned
        try:
            time.sleep(1.1)
        except KeyboardInterrupt:
            logger.info("Process interrupted by user.")
            break

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(current_dir, "input")
    
    print("========================================")
    print(" Model 2: 图片位置识别 (Image Location) ")
    print("========================================")
    
    try:
        process_images_in_folder(input_dir)
    except Exception as e:
        logger.critical(f"Unhandled exception during execution: {e}")
    finally:
        try:
            input('执行完毕，按回车键退出... (Press Enter to exit)')
        except EOFError:
            pass

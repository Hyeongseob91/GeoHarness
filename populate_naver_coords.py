import json
import random
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def populate_coords():
    with open('data/test_coordinates.json', 'r') as f:
        data = json.load(f)
    
    # Simulate a systemic map shift + some noise
    # Typical Google vs Naver offset in Korea could be around 20-40 meters
    for item in data:
        glat = item['google_coords']['lat']
        glng = item['google_coords']['lng']
        
        # 1 meter in lat ~ 0.000009
        # 1 meter in lng ~ 0.000011 (at latitude 37)
        # Shift: North-West shift typical for some projections, let's say +30m lat, -20m lng with noise
        lat_shift_m = random.uniform(20, 50)
        lng_shift_m = random.uniform(-40, -10)
        
        nlat = glat + (lat_shift_m * 0.000009)
        nlng = glng + (lng_shift_m * 0.000011)
        
        item['naver_coords']['lat'] = round(nlat, 6)
        item['naver_coords']['lng'] = round(nlng, 6)
        
        dist = haversine(glat, glng, item['naver_coords']['lat'], item['naver_coords']['lng'])
        item['distance_m'] = round(dist, 2)
        
    with open('data/test_coordinates.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        print("Successfully populated data/test_coordinates.json with synthetic ground truth.")

if __name__ == '__main__':
    populate_coords()

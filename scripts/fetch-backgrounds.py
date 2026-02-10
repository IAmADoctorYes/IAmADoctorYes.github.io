#!/usr/bin/env python3
"""
Fetch daily background images from NASA APOD and Unsplash.
Saves images and metadata to assets/backgrounds/ directory.
"""

import os
import json
import ssl
import requests
from datetime import datetime

# Disable SSL verification locally (GitHub Actions doesn't need this)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()

# API keys
NASA_API_KEY = '8dQ1DXwJiWxzb2OAwnAK3iNp8b7N9UMffh63LdpB'
PEXELS_API_KEY = '7jiaCZIJLJh1oq1HxZwjBhCE4UCtyE4OIIlE3UfS44Tac3oimxs6XlgQ'

# Output directory
BACKGROUNDS_DIR = os.path.join('assets', 'backgrounds')
os.makedirs(BACKGROUNDS_DIR, exist_ok=True)

def fetch_nasa_apod():
    """Fetch NASA Astronomy Picture of the Day"""
    url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&thumbs=true'
    
    try:
        response = requests.get(url, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()
        
        # Get image URL
        img_url = None
        if data.get('media_type') == 'image':
            img_url = data.get('hdurl') or data.get('url')
        elif data.get('thumbnail_url'):
            img_url = data['thumbnail_url']
        
        if not img_url:
            print("  ✗ NASA: No image available today")
            return False
        
        # Download image
        img_response = requests.get(img_url, timeout=60, verify=False)
        img_response.raise_for_status()
        
        # Save image
        img_path = os.path.join(BACKGROUNDS_DIR, 'bg-dark.jpg')
        with open(img_path, 'wb') as f:
            f.write(img_response.content)
        
        # Save metadata
        metadata = {
            'title': data.get('title', 'Astronomy Picture of the Day'),
            'source': 'NASA APOD',
            'href': 'https://apod.nasa.gov',
            'date': datetime.now().isoformat()
        }
        
        meta_path = os.path.join(BACKGROUNDS_DIR, 'bg-dark.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  ✓ NASA: {metadata['title']}")
        return True
        
    except Exception as e:
        print(f"  ✗ NASA fetch error: {e}")
        return False

def fetch_pexels():
    """Fetch random landscape photo from Pexels"""
    url = 'https://api.pexels.com/v1/search?query=landscape&orientation=landscape&per_page=1&page=1'
    headers = {'Authorization': PEXELS_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()
        
        # Get image from results
        if not data.get('photos') or len(data['photos']) == 0:
            print("  ✗ Pexels: No images found")
            return False
        
        photo = data['photos'][0]
        img_url = photo.get('src', {}).get('large')
        
        if not img_url:
            print("  ✗ Pexels: No image URL available")
            return False
        
        # Download image
        img_response = requests.get(img_url, timeout=60, verify=False)
        img_response.raise_for_status()
        
        # Save image
        img_path = os.path.join(BACKGROUNDS_DIR, 'bg-light.jpg')
        with open(img_path, 'wb') as f:
            f.write(img_response.content)
        
        # Save metadata
        photographer = photo.get('photographer', 'Unknown')
        photo_link = photo.get('photographer_url', 'https://pexels.com')
        title = photo.get('alt', 'Landscape Photo')
        
        metadata = {
            'title': title,
            'source': f'{photographer} on Pexels',
            'href': photo_link,
            'date': datetime.now().isoformat()
        }
        
        meta_path = os.path.join(BACKGROUNDS_DIR, 'bg-light.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  ✓ Pexels: {title} by {photographer}")
        return True
        
    except Exception as e:
        print(f"  ✗ Pexels fetch error: {e}")
        return False

if __name__ == '__main__':
    print("Fetching background images...")
    
    nasa_ok = fetch_nasa_apod()
    pexels_ok = fetch_pexels()
    
    if nasa_ok and pexels_ok:
        print("\nBackground fetch complete!")
    elif nasa_ok or pexels_ok:
        print("\nBackground fetch partially complete (some errors)")
    else:
        print("\nBackground fetch failed")
        exit(1)

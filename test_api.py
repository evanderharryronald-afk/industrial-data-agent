import requests

try:
    response = requests.post(
        'http://localhost:8000/api/v1/tools/eda/analyze',
        json={'session_id': 'test', 'dataset_path': 'sample_data.csv'},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Content: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")

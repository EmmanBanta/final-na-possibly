import firebase_admin
from firebase_admin import credentials, db

if not firebase_admin._apps:
    cred = credentials.Certificate('path/to/serviceAccountKey.json')
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://wasteposal-c1fe3afa-default-rtdb.asia-southeast1.firebasedatabase.app'
    })
    
ref = db.reference('/')
print(ref.get())
import os
import sys
from app import app, init_db

if __name__ == '__main__':
    print("=" * 60)
    print(" THE BIGGER FAMILY PORTAL - WEB APPLICATION")
    print("=" * 60)
    print("• Currency: Ghanaian Cedi (GH₵ - GHS)")
    print("• Dues Frequency: Monthly (GH₵ 50.00)")
    print("• Bi-Weekly Assemblies: Every 14 Days")
    print("• Registration Rule: Strictly 16 Years & Above")
    print("• In-App Notification Hub: Enabled")
    print("-" * 60)
    print("Running on http://127.0.0.1:5000")
    print("=" * 60)
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)

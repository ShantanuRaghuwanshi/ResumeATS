# Database configuration and setup
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime
from pathlib import Path


class InMemoryDatabase:
    """Simple in-memory database for development and testing"""

    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {
            "conversations": {},
            "optimization_requests": {},
            "job_analyses": {},
            "resume_versions": {},
            "user_preferences": {},
            "feedback": {},
            "suggestions": {},
            "messages": {},
            "change_impact_analyses": {},
            "performance_metrics": {},
            "user_feedback": {},
            "user_sessions": {},
            "session_data": {},
        }
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.load_data()

    def save_data(self):
        """Save data to disk"""
        try:
            for collection, data in self.data.items():
                file_path = self.data_dir / f"{collection}.json"
                with open(file_path, "w") as f:
                    # Convert datetime objects to strings for JSON serialization
                    serializable_data = self._make_serializable(data)
                    json.dump(serializable_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_data(self):
        """Load data from disk"""
        try:
            for collection in self.data.keys():
                file_path = self.data_dir / f"{collection}.json"
                if file_path.exists():
                    with open(file_path, "r") as f:
                        self.data[collection] = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")

    def _make_serializable(self, obj):
        """Convert objects to JSON serializable format"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def create(self, collection: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record"""
        if collection not in self.data:
            self.data[collection] = {}

        self.data[collection][id] = {
            **data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.save_data()
        return self.data[collection][id]

    def read(self, collection: str, id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID"""
        return self.data.get(collection, {}).get(id)

    def update(
        self, collection: str, id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a record"""
        if collection in self.data and id in self.data[collection]:
            self.data[collection][id].update(
                {**data, "updated_at": datetime.utcnow().isoformat()}
            )
            self.save_data()
            return self.data[collection][id]
        return None

    def delete(self, collection: str, id: str) -> bool:
        """Delete a record"""
        if collection in self.data and id in self.data[collection]:
            del self.data[collection][id]
            self.save_data()
            return True
        return False

    def list(self, collection: str, filter_func=None) -> List[Dict[str, Any]]:
        """List all records in a collection with optional filtering"""
        records = list(self.data.get(collection, {}).values())
        if filter_func:
            records = [r for r in records if filter_func(r)]
        return records

    def find(self, collection: str, **kwargs) -> List[Dict[str, Any]]:
        """Find records matching criteria"""

        def filter_func(record):
            return all(record.get(k) == v for k, v in kwargs.items())

        return self.list(collection, filter_func)


# Global database instance
db = InMemoryDatabase()


def get_database():
    """Get the database instance"""
    return db

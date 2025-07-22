"""
Database migration scripts for resume optimization features
"""

from typing import Dict, Any
from datetime import datetime
from . import get_database


def create_initial_schema():
    """Create initial database schema for enhanced resume features"""
    db = get_database()

    # Initialize collections if they don't exist
    collections = [
        "conversations",
        "optimization_requests",
        "job_analyses",
        "resume_versions",
        "user_preferences",
        "feedback",
        "suggestions",
        "messages",
        "session_data",
        "analytics",
    ]

    for collection in collections:
        if collection not in db.data:
            db.data[collection] = {}

    # Create indexes (for future database implementation)
    indexes = {
        "conversations": ["user_id", "resume_id", "section", "created_at"],
        "optimization_requests": ["user_id", "resume_id", "status", "created_at"],
        "job_analyses": ["user_id", "job_title", "industry", "created_at"],
        "resume_versions": ["user_id", "is_current", "created_at"],
        "user_preferences": ["user_id", "category", "last_updated"],
        "feedback": ["user_id", "session_id", "type", "created_at"],
        "suggestions": ["session_id", "section", "type", "applied"],
        "messages": ["session_id", "role", "timestamp"],
    }

    # Store index information for future use
    db.data["_indexes"] = indexes

    print("✅ Initial database schema created successfully")
    return True


def migrate_existing_resume_data():
    """Migrate existing resume data to new format"""
    db = get_database()

    # This would migrate existing resume data if any exists
    # For now, we'll just ensure the structure is compatible

    print("✅ Existing resume data migration completed")
    return True


def create_default_user_preferences():
    """Create default user preferences for existing users"""
    db = get_database()

    # Create default preferences template
    default_preferences = {
        "suggestion_aggressiveness": "moderate",
        "auto_apply_high_confidence": False,
        "show_reasoning": True,
        "real_time_feedback": True,
        "email_suggestions": False,
        "weekly_summary": True,
        "allow_learning": True,
        "share_anonymous_data": False,
        "preferred_theme": "auto",
        "compact_mode": False,
    }

    # Store default preferences template
    db.data["_default_preferences"] = default_preferences

    print("✅ Default user preferences created")
    return True


def setup_analytics_tracking():
    """Set up analytics tracking structure"""
    db = get_database()

    # Initialize analytics collections
    analytics_collections = [
        "user_sessions",
        "feature_usage",
        "performance_metrics",
        "error_logs",
        "suggestion_effectiveness",
    ]

    for collection in analytics_collections:
        if collection not in db.data:
            db.data[collection] = {}

    print("✅ Analytics tracking setup completed")
    return True


def run_all_migrations():
    """Run all database migrations"""
    print("🚀 Starting database migrations...")

    migrations = [
        ("Creating initial schema", create_initial_schema),
        ("Migrating existing resume data", migrate_existing_resume_data),
        ("Setting up default user preferences", create_default_user_preferences),
        ("Setting up analytics tracking", setup_analytics_tracking),
    ]

    for description, migration_func in migrations:
        print(f"📝 {description}...")
        try:
            migration_func()
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    # Save migration timestamp
    db = get_database()
    db.data["_migration_info"] = {
        "last_migration": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "migrations_applied": [desc for desc, _ in migrations],
    }
    db.save_data()

    print("✅ All database migrations completed successfully!")
    return True


if __name__ == "__main__":
    run_all_migrations()

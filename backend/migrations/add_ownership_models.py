"""
Database Migration: Add Ownership Assignment Models

This migration adds:
- Manual and ManualSection tables for company manual parsing
- OwnershipAssignment table for question ownership tracking
- OwnershipRule table for configurable assignment rules

It also seeds default keyword and CFR rules for initial ownership assignments.
"""

import sys
import os

# Add parent directory to path to import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, get_session, init_db
from models import Base, OwnershipRule
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Default keyword rules (seeded on first run)
DEFAULT_KEYWORD_RULES = [
    {
        "rule_type": "keyword",
        "pattern": r"inspect|inspection|inspected",
        "target_function": "Aircraft Records",
        "weight": 1.5,
        "notes": "Inspection-related activities typically belong to Aircraft Records"
    },
    {
        "rule_type": "keyword",
        "pattern": r"control|dispatch|release",
        "target_function": "MOC",
        "weight": 1.5,
        "notes": "Operational control and dispatch activities"
    },
    {
        "rule_type": "keyword",
        "pattern": r"program|task card|scheduled maintenance",
        "target_function": "Maintenance Planning",
        "weight": 1.5,
        "notes": "Maintenance program and planning activities"
    },
    {
        "rule_type": "keyword",
        "pattern": r"record|logbook|documentation",
        "target_function": "Aircraft Records",
        "weight": 1.2,
        "notes": "Record-keeping and documentation"
    },
    {
        "rule_type": "keyword",
        "pattern": r"training|curriculum|qualification",
        "target_function": "Training",
        "weight": 1.5,
        "notes": "Training and qualification activities"
    },
    {
        "rule_type": "keyword",
        "pattern": r"audit|surveillance|quality assurance",
        "target_function": "Quality",
        "weight": 1.3,
        "notes": "Quality assurance and audit activities"
    },
    {
        "rule_type": "keyword",
        "pattern": r"safety|hazard|risk assessment",
        "target_function": "Safety",
        "weight": 1.3,
        "notes": "Safety management and risk assessment"
    },
    {
        "rule_type": "keyword",
        "pattern": r"director|management approval",
        "target_function": "Director of Maintenance",
        "weight": 1.0,
        "notes": "Management authorization and approval"
    },
    {
        "rule_type": "keyword",
        "pattern": r"preventive|corrective|repair",
        "target_function": "Maintenance Planning",
        "weight": 1.1,
        "notes": "Maintenance action types"
    },
    {
        "rule_type": "keyword",
        "pattern": r"operational control|flight dispatch",
        "target_function": "MOC",
        "weight": 1.4,
        "notes": "Flight operations and dispatch control"
    },
]

# Default CFR rules (seeded on first run)
DEFAULT_CFR_RULES = [
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 121.369",
        "target_function": "Maintenance Planning",
        "weight": 1.5,
        "notes": "Manual requirements - maintenance program"
    },
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 121.373",
        "target_function": "Maintenance Planning",
        "weight": 1.5,
        "notes": "Continuing analysis and surveillance"
    },
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 121.379",
        "target_function": "MOC",
        "weight": 1.5,
        "notes": "Authority to perform and approve maintenance"
    },
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 121.380",
        "target_function": "Aircraft Records",
        "weight": 1.5,
        "notes": "Maintenance recording requirements"
    },
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 135.427",
        "target_function": "Director of Maintenance",
        "weight": 1.5,
        "notes": "Manual requirements - Part 135"
    },
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 121.135",
        "target_function": "Training",
        "weight": 1.4,
        "notes": "Training program requirements"
    },
    {
        "rule_type": "cfr",
        "pattern": "14 CFR 121.375",
        "target_function": "Quality",
        "weight": 1.3,
        "notes": "Continuing analysis and surveillance system"
    },
]


def create_tables():
    """Create all database tables including new ownership models."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def seed_default_rules():
    """Seed default keyword and CFR rules into the database."""
    with get_session() as session:
        # Check if rules already exist
        existing_rules_count = session.query(OwnershipRule).count()

        if existing_rules_count > 0:
            logger.info(f"Rules already exist ({existing_rules_count} rules found). Skipping seed.")
            return

        logger.info("Seeding default keyword rules...")
        for rule_data in DEFAULT_KEYWORD_RULES:
            rule = OwnershipRule(**rule_data)
            session.add(rule)

        logger.info("Seeding default CFR rules...")
        for rule_data in DEFAULT_CFR_RULES:
            rule = OwnershipRule(**rule_data)
            session.add(rule)

        session.commit()

        total_rules = session.query(OwnershipRule).count()
        keyword_rules = session.query(OwnershipRule).filter_by(rule_type='keyword').count()
        cfr_rules = session.query(OwnershipRule).filter_by(rule_type='cfr').count()

        logger.info(f"Seeded {total_rules} rules successfully:")
        logger.info(f"  - {keyword_rules} keyword rules")
        logger.info(f"  - {cfr_rules} CFR rules")


def run_migration():
    """Execute the migration."""
    logger.info("=" * 60)
    logger.info("Running Migration: Add Ownership Assignment Models")
    logger.info("=" * 60)

    try:
        # Create tables
        create_tables()

        # Seed default rules
        seed_default_rules()

        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNew tables added:")
        logger.info("  - manuals")
        logger.info("  - manual_sections")
        logger.info("  - ownership_assignments")
        logger.info("  - ownership_rules")
        logger.info("\nRelationships updated:")
        logger.info("  - questions.ownership_assignment (one-to-one)")
        logger.info("\nDefault rules seeded:")
        logger.info("  - 10 keyword matching rules")
        logger.info("  - 7 CFR mapping rules")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_migration()

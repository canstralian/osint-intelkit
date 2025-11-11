"""Prefect deployment registration for scheduled OSINT flows.

This module creates and registers Prefect deployments with automatic scheduling.
The deployment will run the OSINT collection and enrichment flow at regular intervals.

Configuration:
- Interval-based scheduling (every N hours)
- Cron-based scheduling (specific times)
- Configurable via environment variables
"""

import logging
import os
import time
from datetime import timedelta

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule, IntervalSchedule

# Import the flow to deploy
from app.flows.vt_flow import scheduled_vt_osint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
SCHEDULE_INTERVAL_HOURS = int(os.getenv("OSINT_SCHEDULE_INTERVAL_HOURS", "4"))
SCHEDULE_TYPE = os.getenv("OSINT_SCHEDULE_TYPE", "interval")  # "interval" or "cron"
SCHEDULE_CRON = os.getenv("OSINT_SCHEDULE_CRON", "0 2 * * *")  # Default: 2 AM UTC daily
SCHEDULE_TIMEZONE = os.getenv("OSINT_SCHEDULE_TIMEZONE", "UTC")


def create_deployment():
    """Create and register a Prefect deployment for the OSINT flow.

    This deployment will automatically run the flow according to the schedule.

    Returns:
        Deployment object
    """
    logger.info("Creating Prefect deployment for OSINT pipeline")

    # Choose schedule type
    if SCHEDULE_TYPE == "cron":
        schedule = CronSchedule(cron=SCHEDULE_CRON, timezone=SCHEDULE_TIMEZONE)
        logger.info(f"Using cron schedule: {SCHEDULE_CRON} ({SCHEDULE_TIMEZONE})")
    else:
        schedule = IntervalSchedule(interval=timedelta(hours=SCHEDULE_INTERVAL_HOURS))
        logger.info(f"Using interval schedule: every {SCHEDULE_INTERVAL_HOURS} hours")

    # Build deployment
    deployment = Deployment.build_from_flow(
        flow=scheduled_vt_osint,
        name="osint-automated-collection",
        description="Automated OSINT collection and VirusTotal enrichment",
        version="1.0.0",
        work_queue_name="default",
        schedule=schedule,
        tags=["osint", "virustotal", "scheduled", "automated"],
        parameters={},  # Add default parameters if needed
        work_pool_name=None,  # Use default work pool
    )

    logger.info("Deployment configuration:")
    logger.info(f"  Name: {deployment.name}")
    logger.info(f"  Flow: {deployment.flow_name}")
    logger.info(f"  Schedule: {schedule}")
    logger.info(f"  Work Queue: {deployment.work_queue_name}")
    logger.info(f"  Tags: {deployment.tags}")

    return deployment


def deploy():
    """Deploy the OSINT flow to Prefect server.

    This function:
    1. Creates the deployment configuration
    2. Registers it with the Prefect server
    3. Enables automatic scheduling

    The deployment will start running according to the schedule immediately.
    """
    logger.info("=" * 60)
    logger.info("OSINT IntelKit - Prefect Deployment Registration")
    logger.info("=" * 60)

    try:
        # Wait for Prefect server to be ready
        logger.info("Waiting for Prefect server to be ready...")
        time.sleep(5)  # Give server time to start

        # Create deployment
        deployment = create_deployment()

        # Apply deployment to Prefect server
        logger.info("Registering deployment with Prefect server...")
        deployment_id = deployment.apply()

        logger.info("=" * 60)
        logger.info("✅ Deployment successful!")
        logger.info(f"Deployment ID: {deployment_id}")
        logger.info("=" * 60)
        logger.info("\nThe OSINT pipeline will now run automatically according to schedule:")

        if SCHEDULE_TYPE == "cron":
            logger.info(f"  Schedule: {SCHEDULE_CRON} ({SCHEDULE_TIMEZONE})")
        else:
            logger.info(f"  Schedule: Every {SCHEDULE_INTERVAL_HOURS} hours")

        logger.info("\nAccess Prefect UI at: http://localhost:4200")
        logger.info("View deployments: http://localhost:4200/deployments")
        logger.info("View flow runs: http://localhost:4200/flow-runs")
        logger.info("\nTo trigger a manual run:")
        logger.info(
            "  docker exec -it prefect_agent prefect deployment run 'vt-osint-flow/osint-automated-collection'"
        )
        logger.info("=" * 60)

        return deployment_id

    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        logger.error("Check that Prefect server is running and accessible")
        raise


def create_additional_deployments():
    """Create additional deployments for different schedules or configurations.

    Examples:
    - Hourly quick scans
    - Daily comprehensive scans
    - Weekly deep analysis
    """
    logger.info("Creating additional deployments...")

    # Example: Hourly quick scan (disabled by default)
    if os.getenv("ENABLE_HOURLY_SCAN", "false").lower() == "true":
        hourly_deployment = Deployment.build_from_flow(
            flow=scheduled_vt_osint,
            name="osint-hourly-quick-scan",
            description="Hourly quick OSINT scan for high-priority targets",
            work_queue_name="default",
            schedule=IntervalSchedule(interval=timedelta(hours=1)),
            tags=["osint", "hourly", "quick-scan"],
        )
        hourly_deployment.apply()
        logger.info("✅ Hourly quick scan deployment created")

    # Example: Daily comprehensive scan
    if os.getenv("ENABLE_DAILY_SCAN", "false").lower() == "true":
        daily_deployment = Deployment.build_from_flow(
            flow=scheduled_vt_osint,
            name="osint-daily-comprehensive",
            description="Daily comprehensive OSINT collection and analysis",
            work_queue_name="default",
            schedule=CronSchedule(cron="0 2 * * *", timezone="UTC"),
            tags=["osint", "daily", "comprehensive"],
        )
        daily_deployment.apply()
        logger.info("✅ Daily comprehensive scan deployment created")


if __name__ == "__main__":
    # Deploy main OSINT flow
    deploy()

    # Optionally create additional deployments
    create_additional_deployments()

    logger.info("\n🚀 OSINT IntelKit is now running with automated scheduling!")
    logger.info("The deployment service will now exit (deployment is registered).\n")
